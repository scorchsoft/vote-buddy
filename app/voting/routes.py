from datetime import datetime
from flask import Blueprint, render_template, current_app, abort, url_for, request, flash
from flask_login import current_user

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
    Comment,
    AppSetting,
)
from flask_wtf import FlaskForm
from wtforms import RadioField, SubmitField, StringField
from wtforms.validators import DataRequired
from app.services.email import send_vote_receipt
from ..utils import carried_amendment_summary
from ..extensions import limiter

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


def amendment_snippet(amendment: Amendment, char_limit: int = 40) -> str:
    """Return the first ``char_limit`` characters of an amendment."""
    text = (amendment.text_md or "").strip()
    if len(text) > char_limit:
        return text[:char_limit].rstrip() + "..."
    return text


@bp.route("/<token>", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def ballot_token(token: str):
    """Verify token and display the correct ballot stage."""
    if token == "preview":
        if not current_user.is_authenticated or not current_user.has_permission("manage_meetings"):
            abort(403)
        meeting_id = request.args.get("meeting_id", type=int)
        stage = request.args.get("stage", type=int, default=1)
        meeting = db.session.get(Meeting, meeting_id) if meeting_id else None
        if meeting is None:
            meeting = Meeting.query.order_by(Meeting.id).first()
        if meeting is None:
            abort(404)
        from ..meetings.routes import preview_voting
        return preview_voting(meeting.id, stage)

    vote_token = VoteToken.verify(token, current_app.config["TOKEN_SALT"])
    if not vote_token:
        return render_template("voting/token_error.html", message="Invalid voting link."), 404
    member = db.session.get(Member, vote_token.member_id)
    if member is None:
        abort(404)
    acting_member = (
        db.session.get(Member, vote_token.proxy_holder_id)
        if vote_token.proxy_holder_id
        else member
    )
    meeting = db.session.get(Meeting, member.meeting_id)
    if meeting is None:
        abort(404)

    proxy_for = member if vote_token.proxy_holder_id else None

    # verify current time falls within the configured window
    now = datetime.utcnow()
    if vote_token.stage == 1:
        opens = meeting.opens_at_stage1
        closes = meeting.closes_at_stage1
    else:
        opens = meeting.opens_at_stage2
        closes = meeting.closes_at_stage2
    if opens and now < opens:
        return (
            render_template(
                "voting/token_not_open.html",
                start=opens,
                end=closes,
            ),
            400,
        )
    if closes and now > closes:
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

    used_any = (
        VoteToken.query.filter_by(member_id=member.id, stage=vote_token.stage)
        .filter(VoteToken.used_at.isnot(None))
        .first()
    )
    if used_any and not meeting.revoting_allowed:
        return (
            render_template(
                "voting/token_error.html",
                message="This voting link has already been used.",
            ),
            400,
        )

    revote = bool(used_any and meeting.revoting_allowed)

    if meeting.ballot_mode == "combined":
        motions = (
            Motion.query.filter_by(meeting_id=meeting.id, is_published=True)
            .order_by(Motion.ordering)
            .all()
        )
        amendments = (
            Amendment.query.filter(
                Amendment.motion_id.in_([m.id for m in motions]),
                Amendment.is_published.is_(True),
            )
            .order_by(Amendment.order)
            .all()
        )
        form = _combined_form(motions, amendments)
        if form.validate_on_submit():
            hashes = []
            if revote:
                for amend in amendments:
                    Vote.query.filter_by(member_id=member.id, amendment_id=amend.id).delete()
                for motion in motions:
                    Vote.query.filter_by(member_id=member.id, motion_id=motion.id).delete()
                db.session.commit()
            for amend in amendments:
                choice = form[f"amend_{amend.id}"].data
                vote = Vote.record(
                    member_id=member.id,
                    amendment_id=amend.id,
                    choice=choice,
                    salt=current_app.config["VOTE_SALT"],
                    stage=vote_token.stage,
                )
                hashes.append(vote.hash)
            for motion in motions:
                choice = form[f"motion_{motion.id}"].data
                vote = Vote.record(
                    member_id=member.id,
                    motion_id=motion.id,
                    choice=choice,
                    salt=current_app.config["VOTE_SALT"],
                    stage=vote_token.stage,
                )
                hashes.append(vote.hash)
            now = datetime.utcnow()
            VoteToken.query.filter_by(member_id=member.id, stage=vote_token.stage).update({"used_at": now})
            db.session.commit()
            send_vote_receipt(acting_member, meeting, hashes)
            return render_template(
                "voting/confirmation.html",
                choice="recorded",
                meeting=meeting,
                token=token,
                stage=vote_token.stage,
                final_message_default=current_app.config.get("FINAL_STAGE_MESSAGE"),
            )

        motion_counts = {
            m.id: Comment.query.filter_by(motion_id=m.id, hidden=False).count()
            for m in motions
        }
        amend_counts = {
            a.id: Comment.query.filter_by(amendment_id=a.id, hidden=False).count()
            for a in amendments
        }
        motions_grouped = []
        for motion in motions:
            ams = [a for a in amendments if a.motion_id == motion.id]
            motions_grouped.append((motion, ams))
        return render_template(
            "voting/combined_ballot.html",
            form=form,
            motions=motions_grouped,
            meeting=meeting,
            proxy_for=proxy_for,
            token=token,
            motion_counts=motion_counts,
            amend_counts=amend_counts,
            revote=revote,
        )

    if vote_token.stage == 1:
        motions = (
            Motion.query.filter_by(meeting_id=meeting.id, is_published=True)
            .order_by(Motion.ordering)
            .all()
        )
        amendments = (
            Amendment.query.filter(
                Amendment.motion_id.in_([m.id for m in motions]),
                Amendment.is_published.is_(True),
            )
            .order_by(Amendment.order)
            .all()
        )
        form = _amendment_form(amendments)
        if form.validate_on_submit():
            hashes = []
            if revote:
                for amend in amendments:
                    Vote.query.filter_by(member_id=member.id, amendment_id=amend.id).delete()
                db.session.commit()
            for amend in amendments:
                choice = form[f"amend_{amend.id}"].data
                vote = Vote.record(
                    member_id=member.id,
                    amendment_id=amend.id,
                    choice=choice,
                    salt=current_app.config["VOTE_SALT"],
                    stage=vote_token.stage,
                )
                hashes.append(vote.hash)
            now = datetime.utcnow()
            VoteToken.query.filter_by(member_id=member.id, stage=vote_token.stage).update({"used_at": now})
            db.session.commit()
            send_vote_receipt(acting_member, meeting, hashes)
            return render_template(
                "voting/confirmation.html",
                choice="recorded",
                meeting=meeting,
                token=token,
                stage=vote_token.stage,
                final_message_default=current_app.config.get("FINAL_STAGE_MESSAGE"),
            )

        motion_counts = {
            m.id: Comment.query.filter_by(motion_id=m.id, hidden=False).count()
            for m in motions
        }
        amend_counts = {
            a.id: Comment.query.filter_by(amendment_id=a.id, hidden=False).count()
            for a in amendments
        }
        motions_grouped = []
        for motion in motions:
            ams = [a for a in amendments if a.motion_id == motion.id]
            motions_grouped.append((motion, ams))
        return render_template(
            "voting/stage1_ballot.html",
            form=form,
            motions=motions_grouped,
            meeting=meeting,
            proxy_for=proxy_for,
            token=token,
            motion_counts=motion_counts,
            amend_counts=amend_counts,
            revote=revote,
        )

    else:
        motions = (
            Motion.query.filter_by(meeting_id=meeting.id, is_published=True)
            .order_by(Motion.ordering)
            .all()
        )
        form = _motion_form(motions)
        if form.validate_on_submit():
            hashes = []
            if revote:
                for motion in motions:
                    Vote.query.filter_by(member_id=member.id, motion_id=motion.id).delete()
                db.session.commit()
            for motion in motions:
                choice = form[f"motion_{motion.id}"].data
                vote = Vote.record(
                    member_id=member.id,
                    motion_id=motion.id,
                    choice=choice,
                    salt=current_app.config["VOTE_SALT"],
                    stage=vote_token.stage,
                )
                hashes.append(vote.hash)
            now = datetime.utcnow()
            VoteToken.query.filter_by(member_id=member.id, stage=vote_token.stage).update({"used_at": now})
            db.session.commit()
            send_vote_receipt(acting_member, meeting, hashes)
            return render_template(
                "voting/confirmation.html",
                choice="recorded",
                meeting=meeting,
                token=token,
                stage=vote_token.stage,
                final_message_default=current_app.config.get("FINAL_STAGE_MESSAGE"),
            )

        compiled = [
            (m, m.final_text_md or compile_motion_text(m)) for m in motions
        ]
        motion_counts = {
            m.id: Comment.query.filter_by(motion_id=m.id, hidden=False).count()
            for m in motions
        }
        carried_summary = carried_amendment_summary(meeting)
        results_link = None if carried_summary else url_for('main.public_results', meeting_id=meeting.id)
        return render_template(
            "voting/stage2_ballot.html",
            form=form,
            motions=compiled,
            meeting=meeting,
            proxy_for=proxy_for,
            token=token,
            motion_counts=motion_counts,
            revote=revote,
            carried_summary=carried_summary,
            results_link=results_link,
        )


@bp.route("/runoff/<token>", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def runoff_ballot(token: str):
    """Display a run-off ballot for conflicting amendments."""
    if token == "preview":
        if not current_user.is_authenticated or not current_user.has_permission("manage_meetings"):
            abort(403)
        meeting_id = request.args.get("meeting_id", type=int)
        meeting = db.session.get(Meeting, meeting_id) if meeting_id else None
        if meeting is None:
            meeting = Meeting.query.order_by(Meeting.id).first()
        if meeting is None:
            abort(404)
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
            flash("Preview submission complete – votes were not saved", "info")
            return render_template(
                "voting/confirmation.html",
                preview=True,
                stage=1,
                final_message_default=current_app.config.get("FINAL_STAGE_MESSAGE"),
            )
        pairs = [
            (r, db.session.get(Amendment, r.amendment_a_id), db.session.get(Amendment, r.amendment_b_id))
            for r in runoffs
        ]
        return render_template(
            "voting/runoff_ballot.html",
            form=form,
            runoffs=pairs,
            meeting=meeting,
            proxy_for=None,
            snippet=amendment_snippet,
        )

    vote_token = VoteToken.verify(token, current_app.config["TOKEN_SALT"])
    if not vote_token or vote_token.stage != 1:
        return render_template("voting/token_error.html", message="Invalid voting link."), 404
    member = db.session.get(Member, vote_token.member_id)
    if member is None:
        abort(404)
    meeting = db.session.get(Meeting, member.meeting_id)
    if meeting is None:
        abort(404)

    acting_member = (
        db.session.get(Member, vote_token.proxy_holder_id)
        if vote_token.proxy_holder_id
        else member
    )
    proxy_for = member if vote_token.proxy_holder_id else None

    used_any = (
        VoteToken.query.filter_by(member_id=member.id, stage=vote_token.stage)
        .filter(VoteToken.used_at.isnot(None))
        .first()
    )
    if used_any and not meeting.revoting_allowed:
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

    now = datetime.utcnow()
    if (meeting.runoff_opens_at and now < meeting.runoff_opens_at) or (
        meeting.runoff_closes_at and now > meeting.runoff_closes_at
    ):
        return (
            render_template(
                "voting/token_error.html",
                message="Run-off voting is not currently open.",
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
                v1 = Vote.record(member_id=member.id, amendment_id=a_id, choice="for", salt=current_app.config["VOTE_SALT"], stage=vote_token.stage)
                v2 = Vote.record(member_id=member.id, amendment_id=b_id, choice="against", salt=current_app.config["VOTE_SALT"], stage=vote_token.stage)
                hashes.extend([v1.hash, v2.hash])
            elif choice == "b":
                v1 = Vote.record(member_id=member.id, amendment_id=a_id, choice="against", salt=current_app.config["VOTE_SALT"], stage=vote_token.stage)
                v2 = Vote.record(member_id=member.id, amendment_id=b_id, choice="for", salt=current_app.config["VOTE_SALT"], stage=vote_token.stage)
                hashes.extend([v1.hash, v2.hash])
            else:
                v1 = Vote.record(member_id=member.id, amendment_id=a_id, choice="abstain", salt=current_app.config["VOTE_SALT"], stage=vote_token.stage)
                v2 = Vote.record(member_id=member.id, amendment_id=b_id, choice="abstain", salt=current_app.config["VOTE_SALT"], stage=vote_token.stage)
                hashes.extend([v1.hash, v2.hash])
        now = datetime.utcnow()
        VoteToken.query.filter_by(member_id=member.id, stage=vote_token.stage).update({"used_at": now})
        db.session.commit()
        send_vote_receipt(acting_member, meeting, hashes)
        return render_template(
            "voting/confirmation.html",
            choice="recorded",
            stage=vote_token.stage,
            final_message_default=current_app.config.get("FINAL_STAGE_MESSAGE"),
        )

    pairs = [
        (
            r,
            db.session.get(Amendment, r.amendment_a_id),
            db.session.get(Amendment, r.amendment_b_id),
        )
        for r in runoffs
    ]
    return render_template(
        "voting/runoff_ballot.html",
        form=form,
        runoffs=pairs,
        meeting=meeting,
        proxy_for=proxy_for,
        snippet=amendment_snippet,
    )


class ReceiptLookupForm(FlaskForm):
    hash = StringField("Receipt Hash", validators=[DataRequired()])
    submit = SubmitField("Verify")


@bp.route("/verify-receipt", methods=["GET", "POST"])
@limiter.limit("20 per hour")
def verify_receipt():
    """Allow members to check a vote receipt hash."""
    form = ReceiptLookupForm()
    votes = None
    message = None
    if form.validate_on_submit():
        h = form.hash.data.strip()
        raw = Vote.query.filter_by(hash=h).all()
        if len(raw) == 1:
            votes = [
                {
                    "choice": raw[0].choice,
                    "motion": db.session.get(Motion, raw[0].motion_id) if raw[0].motion_id else None,
                    "amendment": db.session.get(Amendment, raw[0].amendment_id) if raw[0].amendment_id else None,
                }
            ]
        elif len(raw) > 1:
            message = "Multiple votes share this hash. Check your email receipt or contact support."
        else:
            message = "No vote found for that hash."
    contact_url = AppSetting.get(
        "contact_url", "https://www.britishpowerlifting.org/contactus"
    )
    return render_template(
        "voting/verify_receipt.html",
        form=form,
        votes=votes,
        message=message,
        contact_url=contact_url,
    )
