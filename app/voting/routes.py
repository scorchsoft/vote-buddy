from datetime import datetime
from flask import Blueprint, render_template, current_app

from ..extensions import db
from ..models import (
    VoteToken,
    Member,
    Amendment,
    Meeting,
    Vote,
    Motion,
    MotionOption,
    Runoff,
)
from .forms import VoteForm
from flask_wtf import FlaskForm
from wtforms import RadioField, SubmitField
from wtforms.validators import DataRequired
from app.services.email import send_vote_receipt

bp = Blueprint("voting", __name__, url_prefix="/vote")


@bp.route("/")
def ballot_home():
    return render_template("voting/home.html")


def _amendment_form(amendments):
    fields = {}
    for amend in amendments:
        fields[f"amend_{amend.id}"] = RadioField(
            "Your vote",
            choices=[("for", "For"), ("against", "Against"), ("abstain", "Abstain")],
            validators=[DataRequired()],
        )
    fields["submit"] = SubmitField("Submit votes")
    return type("DynamicForm", (FlaskForm,), fields)()


def _motion_form(motions):
    fields = {}
    for motion in motions:
        if motion.category == "multiple_choice":
            opts = [(o.text, o.text) for o in motion.options]
            opts.append(("abstain", "Abstain"))
        else:
            opts = [("for", "For"), ("against", "Against"), ("abstain", "Abstain")]
        fields[f"motion_{motion.id}"] = RadioField(
            "Your vote", choices=opts, validators=[DataRequired()]
        )
    fields["submit"] = SubmitField("Submit votes")
    return type("MotionForm", (FlaskForm,), fields)()


def _combined_form(motions, amendments):
    """Build a form with both amendment and motion fields."""
    fields = {}
    for amend in amendments:
        fields[f"amend_{amend.id}"] = RadioField(
            "Your vote",
            choices=[("for", "For"), ("against", "Against"), ("abstain", "Abstain")],
            validators=[DataRequired()],
        )
    for motion in motions:
        if motion.category == "multiple_choice":
            opts = [(o.text, o.text) for o in motion.options]
            opts.append(("abstain", "Abstain"))
        else:
            opts = [("for", "For"), ("against", "Against"), ("abstain", "Abstain")]
        fields[f"motion_{motion.id}"] = RadioField(
            "Your vote", choices=opts, validators=[DataRequired()]
        )
    fields["submit"] = SubmitField("Submit votes")
    return type("CombinedForm", (FlaskForm,), fields)()


def compile_motion_text(motion: Motion) -> str:
    """Return the motion text with carried amendments inserted in order."""
    amendments = (
        Amendment.query.filter_by(motion_id=motion.id, status="carried")
        .order_by(Amendment.order)
        .all()
    )
    if not amendments:
        return motion.text_md
    parts = [motion.text_md]
    parts.extend(a.text_md for a in amendments)
    return "\n\n".join(parts)


@bp.route("/<token>", methods=["GET", "POST"])
def ballot_token(token: str):
    """Verify token and display the correct ballot stage."""
    vote_token = VoteToken.verify(token, current_app.config["TOKEN_SALT"])
    if not vote_token:
        return render_template("voting/token_error.html", message="Invalid voting link."), 404
    member = Member.query.get_or_404(vote_token.member_id)
    meeting = Meeting.query.get_or_404(member.meeting_id)

    proxy_member = None
    if member.proxy_for:
        try:
            proxy_member = Member.query.get(int(member.proxy_for))
        except (ValueError, TypeError):
            proxy_member = None

    # verify current time falls within the configured window
    now = datetime.utcnow()
    if vote_token.stage == 1:
        opens = meeting.opens_at_stage1
        closes = meeting.closes_at_stage1
    else:
        opens = meeting.opens_at_stage2
        closes = meeting.closes_at_stage2
    if (opens and now < opens) or (closes and now > closes):
        return (
            render_template(
                "voting/token_error.html",
                message="Voting for this stage is not currently open.",
            ),
            400,
        )

    # reject tokens if the RO has locked this stage
    if (vote_token.stage == 1 and meeting.stage1_locked) or (
        vote_token.stage == 2 and meeting.stage2_locked
    ):
        return (
            render_template(
                "voting/token_error.html",
                message="Voting for this stage has been locked by the Returning Officer.",
            ),
            400,
        )

    if vote_token.used_at and not meeting.revoting_allowed:
        return (
            render_template(
                "voting/token_error.html",
                message="This voting link has already been used.",
            ),
            400,
        )

    if meeting.ballot_mode == "combined":
        motions = (
            Motion.query.filter_by(meeting_id=meeting.id)
            .order_by(Motion.ordering)
            .all()
        )
        amendments = (
            Amendment.query.filter(Amendment.motion_id.in_([m.id for m in motions]))
            .order_by(Amendment.order)
            .all()
        )
        form = _combined_form(motions, amendments)
        if form.validate_on_submit():
            hashes = []
            for amend in amendments:
                choice = form[f"amend_{amend.id}"].data
                vote = Vote.record(
                    member_id=member.id,
                    amendment_id=amend.id,
                    choice=choice,
                    salt=current_app.config["VOTE_SALT"],
                )
                hashes.append(vote.hash)
                if proxy_member:
                    Vote.record(
                        member_id=proxy_member.id,
                        amendment_id=amend.id,
                        choice=choice,
                        salt=current_app.config["VOTE_SALT"],
                    )
            for motion in motions:
                choice = form[f"motion_{motion.id}"].data
                vote = Vote.record(
                    member_id=member.id,
                    motion_id=motion.id,
                    choice=choice,
                    salt=current_app.config["VOTE_SALT"],
                )
                hashes.append(vote.hash)
                if proxy_member:
                    Vote.record(
                        member_id=proxy_member.id,
                        motion_id=motion.id,
                        choice=choice,
                        salt=current_app.config["VOTE_SALT"],
                    )
            vote_token.used_at = datetime.utcnow()
            db.session.commit()
            send_vote_receipt(member, meeting, hashes)
            return render_template("voting/confirmation.html", choice="recorded")

        motions_grouped = []
        for motion in motions:
            ams = [a for a in amendments if a.motion_id == motion.id]
            motions_grouped.append((motion, ams))
        return render_template(
            "voting/combined_ballot.html",
            form=form,
            motions=motions_grouped,
            meeting=meeting,
            proxy_for=proxy_member,
        )

    if vote_token.stage == 1:
        motions = (
            Motion.query.filter_by(meeting_id=meeting.id)
            .order_by(Motion.ordering)
            .all()
        )
        amendments = (
            Amendment.query.filter(Amendment.motion_id.in_([m.id for m in motions]))
            .order_by(Amendment.order)
            .all()
        )
        form = _amendment_form(amendments)
        if form.validate_on_submit():
            hashes = []
            for amend in amendments:
                choice = form[f"amend_{amend.id}"].data
                vote = Vote.record(
                    member_id=member.id,
                    amendment_id=amend.id,
                    choice=choice,
                    salt=current_app.config["VOTE_SALT"],
                )
                hashes.append(vote.hash)
                if proxy_member:
                    Vote.record(
                        member_id=proxy_member.id,
                        amendment_id=amend.id,
                        choice=choice,
                        salt=current_app.config["VOTE_SALT"],
                    )
            vote_token.used_at = datetime.utcnow()
            db.session.commit()
            send_vote_receipt(member, meeting, hashes)
            return render_template("voting/confirmation.html", choice="recorded")

        motions_grouped = []
        for motion in motions:
            ams = [a for a in amendments if a.motion_id == motion.id]
            motions_grouped.append((motion, ams))
        return render_template(
            "voting/stage1_ballot.html",
            form=form,
            motions=motions_grouped,
            meeting=meeting,
            proxy_for=proxy_member,
        )

    else:
        motions = (
            Motion.query.filter_by(meeting_id=meeting.id)
            .order_by(Motion.ordering)
            .all()
        )
        form = _motion_form(motions)
        if form.validate_on_submit():
            hashes = []
            for motion in motions:
                choice = form[f"motion_{motion.id}"].data
                vote = Vote.record(
                    member_id=member.id,
                    motion_id=motion.id,
                    choice=choice,
                    salt=current_app.config["VOTE_SALT"],
                )
                hashes.append(vote.hash)
                if proxy_member:
                    Vote.record(
                        member_id=proxy_member.id,
                        motion_id=motion.id,
                        choice=choice,
                        salt=current_app.config["VOTE_SALT"],
                    )
            vote_token.used_at = datetime.utcnow()
            db.session.commit()
            send_vote_receipt(member, meeting, hashes)
            return render_template("voting/confirmation.html", choice="recorded")

        compiled = [
            (m, m.final_text_md or compile_motion_text(m)) for m in motions
        ]
        return render_template(
            "voting/stage2_ballot.html",
            form=form,
            motions=compiled,
            meeting=meeting,
            proxy_for=proxy_member,
        )


@bp.route("/runoff/<token>", methods=["GET", "POST"])
def runoff_ballot(token: str):
    """Display a run-off ballot for conflicting amendments."""
    vote_token = VoteToken.verify(token, current_app.config["TOKEN_SALT"])
    if not vote_token or vote_token.stage != 1:
        return render_template("voting/token_error.html", message="Invalid voting link."), 404
    member = Member.query.get_or_404(vote_token.member_id)
    meeting = Meeting.query.get_or_404(member.meeting_id)

    proxy_member = None
    if member.proxy_for:
        try:
            proxy_member = Member.query.get(int(member.proxy_for))
        except (ValueError, TypeError):
            proxy_member = None

    if vote_token.used_at and not meeting.revoting_allowed:
        return (
            render_template(
                "voting/token_error.html",
                message="This voting link has already been used.",
            ),
            400,
        )

    runoffs = Runoff.query.filter_by(meeting_id=meeting.id).all()
    if not runoffs:
        return (
            render_template(
                "voting/token_error.html",
                message="No run-off ballot is required for this meeting.",
            ),
            400,
        )

    fields = {}
    for r in runoffs:
        fields[f"runoff_{r.id}"] = RadioField(
            "Your choice",
            choices=[("a", "Amendment 1"), ("b", "Amendment 2"), ("abstain", "Abstain")],
            validators=[DataRequired()],
        )
    fields["submit"] = SubmitField("Submit vote")
    form = type("RunoffForm", (FlaskForm,), fields)()

    if form.validate_on_submit():
        hashes = []
        for r in runoffs:
            choice = form[f"runoff_{r.id}"].data
            a_id = r.amendment_a_id
            b_id = r.amendment_b_id
            if choice == "a":
                v1 = Vote.record(member_id=member.id, amendment_id=a_id, choice="for", salt=current_app.config["VOTE_SALT"])
                v2 = Vote.record(member_id=member.id, amendment_id=b_id, choice="against", salt=current_app.config["VOTE_SALT"])
                hashes.extend([v1.hash, v2.hash])
                if proxy_member:
                    Vote.record(member_id=proxy_member.id, amendment_id=a_id, choice="for", salt=current_app.config["VOTE_SALT"])
                    Vote.record(member_id=proxy_member.id, amendment_id=b_id, choice="against", salt=current_app.config["VOTE_SALT"])
            elif choice == "b":
                v1 = Vote.record(member_id=member.id, amendment_id=a_id, choice="against", salt=current_app.config["VOTE_SALT"])
                v2 = Vote.record(member_id=member.id, amendment_id=b_id, choice="for", salt=current_app.config["VOTE_SALT"])
                hashes.extend([v1.hash, v2.hash])
                if proxy_member:
                    Vote.record(member_id=proxy_member.id, amendment_id=a_id, choice="against", salt=current_app.config["VOTE_SALT"])
                    Vote.record(member_id=proxy_member.id, amendment_id=b_id, choice="for", salt=current_app.config["VOTE_SALT"])
            else:
                v1 = Vote.record(member_id=member.id, amendment_id=a_id, choice="abstain", salt=current_app.config["VOTE_SALT"])
                v2 = Vote.record(member_id=member.id, amendment_id=b_id, choice="abstain", salt=current_app.config["VOTE_SALT"])
                hashes.extend([v1.hash, v2.hash])
                if proxy_member:
                    Vote.record(member_id=proxy_member.id, amendment_id=a_id, choice="abstain", salt=current_app.config["VOTE_SALT"])
                    Vote.record(member_id=proxy_member.id, amendment_id=b_id, choice="abstain", salt=current_app.config["VOTE_SALT"])
        vote_token.used_at = datetime.utcnow()
        db.session.commit()
        send_vote_receipt(member, meeting, hashes)
        return render_template("voting/confirmation.html", choice="recorded")

    pairs = [
        (r, Amendment.query.get(r.amendment_a_id), Amendment.query.get(r.amendment_b_id))
        for r in runoffs
    ]
    return render_template(
        "voting/runoff_ballot.html",
        form=form,
        runoffs=pairs,
        meeting=meeting,
        proxy_for=proxy_member,
    )
