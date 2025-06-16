from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    send_file,
    current_app,
)
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime, timedelta
from flask_login import login_required
from ..extensions import db
from ..models import (
    Meeting,
    Member,
    VoteToken,
    Amendment,
    AmendmentMerge,
    AmendmentConflict,
    Motion,
    MotionOption,
    Vote,
    Runoff,
)
from ..services.email import (
    send_vote_invite,
    send_stage2_invite,
    send_runoff_invite,
)
from ..services import runoff
from ..permissions import permission_required
from .forms import (
    MeetingForm,
    MemberImportForm,
    AmendmentForm,
    MotionForm,
    ConflictForm,
)
from ..voting.routes import compile_motion_text
import csv
import io
from uuid6 import uuid7
from sqlalchemy import func
from docx import Document
from docx.shared import RGBColor, Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from ..utils import config_or_setting
import os

bp = Blueprint("meetings", __name__, url_prefix="/meetings")


def _shade_cell(cell, color_hex: str) -> None:
    """Apply background colour to a table cell."""
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _styled_doc(title: str, include_logo: bool) -> Document:
    """Return a Document with BP branding styles."""
    doc = Document()
    normal = doc.styles["Normal"].font
    normal.name = "Gotham"
    normal.size = Pt(11)

    for level in ["Heading 2", "Heading 3"]:
        h = doc.styles[level].font
        h.name = "Gotham"
        h.color.rgb = RGBColor(0xDC, 0x07, 0x14)

    # header bar
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    para = cell.paragraphs[0]
    run = para.add_run(title)
    run.bold = True
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _shade_cell(cell, "002D59")

    if include_logo:
        logo_path = os.path.join(current_app.root_path, "..", "assets", "logo (1).png")
        footer = doc.sections[0].footer
        fp = footer.add_paragraph()
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        fp_run = fp.add_run()
        try:
            fp_run.add_picture(logo_path, width=Inches(1))
        except Exception:
            pass

    return doc


@bp.route("/")
@login_required
@permission_required("manage_meetings")
def list_meetings():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "title")
    direction = request.args.get("direction", "asc")

    query = Meeting.query
    if q:
        search = f"%{q}%"
        query = query.filter(Meeting.title.ilike(search))

    if sort == "type":
        order_attr = Meeting.type
    elif sort == "status":
        order_attr = Meeting.status
    else:
        order_attr = Meeting.title

    query = query.order_by(
        order_attr.asc() if direction == "asc" else order_attr.desc()
    )

    meetings = query.all()

    template = (
        "meetings/_meeting_rows.html"
        if request.headers.get("HX-Request")
        else "meetings_list.html"
    )
    return render_template(
        template,
        meetings=meetings,
        q=q,
        sort=sort,
        direction=direction,
    )


def _save_meeting(form: MeetingForm, meeting: Meeting | None = None) -> Meeting:
    """Populate Meeting from form and save."""
    if meeting is None:
        meeting = Meeting()

    form.populate_obj(meeting)
    db.session.add(meeting)
    db.session.commit()
    return meeting


@bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def create_meeting():
    form = MeetingForm()
    if form.validate_on_submit():
        _save_meeting(form)
        return redirect(url_for("meetings.list_meetings"))
    return render_template("meetings/meetings_form.html", form=form)


@bp.route("/<int:meeting_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def edit_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    form = MeetingForm(obj=meeting)
    if form.validate_on_submit():
        _save_meeting(form, meeting)
        return redirect(url_for("meetings.list_meetings"))
    return render_template("meetings/meetings_form.html", form=form, meeting=meeting)


@bp.route("/<int:meeting_id>/import-members", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def import_members(meeting_id):
    """Upload a CSV of members and generate vote tokens."""

    meeting = Meeting.query.get_or_404(meeting_id)
    form = MemberImportForm()
    if form.validate_on_submit():
        file_data = form.csv_file.data
        csv_text = file_data.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(csv_text))
        expected = ["member_id", "name", "email", "vote_weight", "proxy_for"]
        if reader.fieldnames != expected:
            flash("CSV headers must be: " + ", ".join(expected), "error")
            return render_template(
                "meetings/import_members.html", form=form, meeting=meeting
            )

        seen_emails: set[str] = set()
        tokens_to_send: list[tuple[Member, str]] = []
        for row in reader:
            email = row["email"].strip().lower()
            if email in seen_emails:
                flash(f"Duplicate email: {email}", "error")
                return render_template(
                    "meetings/import_members.html", form=form, meeting=meeting
                )
            seen_emails.add(email)

            member = Member(
                meeting_id=meeting.id,
                name=row["name"].strip(),
                email=email,
                proxy_for=(row.get("proxy_for") or "").strip() or None,
                weight=int(row.get("vote_weight") or 1),
            )
            db.session.add(member)
            db.session.flush()
            token_obj, plain = VoteToken.create(
                member_id=member.id,
                stage=1,
                salt=current_app.config["TOKEN_SALT"],
            )
            tokens_to_send.append((member, plain))

        db.session.commit()
        for m, t in tokens_to_send:
            send_vote_invite(m, t, meeting)
        flash("Members imported successfully", "success")
        return redirect(url_for("meetings.list_meetings"))

    return render_template("meetings/import_members.html", form=form, meeting=meeting)


@bp.route("/<int:meeting_id>/motions")
@login_required
@permission_required("manage_meetings")
def list_motions(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    motions = (
        Motion.query.filter_by(meeting_id=meeting.id).order_by(Motion.ordering).all()
    )
    return render_template(
        "meetings/motions_list.html", meeting=meeting, motions=motions
    )


@bp.route("/<int:meeting_id>/motions/create", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def create_motion(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    form = MotionForm()
    clerical_text = config_or_setting("CLERICAL_TEXT", "")
    move_text = config_or_setting("MOVE_TEXT", "")
    if form.validate_on_submit():
        ordering = Motion.query.filter_by(meeting_id=meeting.id).count() + 1
        text_md = form.text_md.data
        if form.allow_clerical.data and clerical_text:
            text_md += f"\n\n{clerical_text}"
        if form.allow_move.data and move_text:
            text_md += f"\n\n{move_text}"
        motion = Motion(
            meeting_id=meeting.id,
            title=form.title.data,
            text_md=text_md,
            category=form.category.data,
            threshold=form.threshold.data,
            ordering=ordering,
        )
        db.session.add(motion)
        db.session.flush()
        if form.category.data == "multiple_choice" and form.options.data:
            for line in form.options.data.splitlines():
                text = line.strip()
                if text:
                    db.session.add(MotionOption(motion_id=motion.id, text=text))
        db.session.commit()
        return redirect(url_for("meetings.list_motions", meeting_id=meeting.id))
    return render_template(
        "meetings/motion_form.html",
        form=form,
        motion=None,
        clerical_text=clerical_text,
        move_text=move_text,
    )


@bp.route("/motions/<int:motion_id>")
def view_motion(motion_id):
    motion = Motion.query.get_or_404(motion_id)
    amendments = (
        Amendment.query.filter_by(motion_id=motion.id).order_by(Amendment.order).all()
    )
    conflicts = (
        AmendmentConflict.query.join(
            Amendment, Amendment.id == AmendmentConflict.amendment_a_id
        )
        .filter(Amendment.motion_id == motion.id)
        .all()
    )
    return render_template(
        "meetings/view_motion.html",
        motion=motion,
        amendments=amendments,
        conflicts=conflicts,
    )


@bp.route("/motions/<int:motion_id>/amendments/add", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def add_amendment(motion_id):
    motion = Motion.query.get_or_404(motion_id)
    form = AmendmentForm()
    members = (
        Member.query.filter_by(meeting_id=motion.meeting_id).order_by(Member.name).all()
    )
    choices = [(m.id, m.name) for m in members]
    form.proposer_id.choices = choices
    form.seconder_id.choices = choices
    if form.validate_on_submit():
        meeting = Meeting.query.get(motion.meeting_id)
        if meeting.opens_at_stage1:
            deadline = meeting.opens_at_stage1 - timedelta(days=21)
            if datetime.utcnow() > deadline:
                flash("Amendment deadline has passed.", "error")
                return render_template(
                    "meetings/amendment_form.html", form=form, motion=motion
                )

        if form.proposer_id.data == form.seconder_id.data:
            flash("Proposer cannot second their own amendment.", "error")
            return render_template(
                "meetings/amendment_form.html", form=form, motion=motion
            )

        count = Amendment.query.filter_by(
            motion_id=motion.id,
            proposer_id=form.proposer_id.data,
        ).count()
        if count >= 3:
            flash("A member may propose at most three amendments per motion.", "error")
            return render_template(
                "meetings/amendment_form.html", form=form, motion=motion
            )

        order = Amendment.query.filter_by(motion_id=motion.id).count() + 1
        amendment = Amendment(
            meeting_id=motion.meeting_id,
            motion_id=motion.id,
            text_md=form.text_md.data,
            order=order,
            proposer_id=form.proposer_id.data,
            seconder_id=form.seconder_id.data,
        )
        db.session.add(amendment)
        db.session.flush()

        combine_param = request.args.get("combine")
        if combine_param:
            ids = [int(i) for i in combine_param.split(",") if i.isdigit()]
            for src_id in ids:
                db.session.add(
                    AmendmentMerge(combined_id=amendment.id, source_id=src_id)
                )

        db.session.commit()
        return redirect(url_for("meetings.view_motion", motion_id=motion.id))
    return render_template("meetings/amendment_form.html", form=form, motion=motion)


@bp.route("/motions/<int:motion_id>/conflicts", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def manage_conflicts(motion_id: int):
    motion = Motion.query.get_or_404(motion_id)
    amendments = (
        Amendment.query.filter_by(motion_id=motion.id).order_by(Amendment.order).all()
    )
    form = ConflictForm()
    choices = [(a.id, f"A{a.order}") for a in amendments]
    form.amendment_a_id.choices = choices
    form.amendment_b_id.choices = choices

    if form.validate_on_submit():
        a_id = form.amendment_a_id.data
        b_id = form.amendment_b_id.data
        if a_id != b_id:
            exists = (
                AmendmentConflict.query.filter_by(meeting_id=motion.meeting_id)
                .filter(
                    (
                        (AmendmentConflict.amendment_a_id == a_id)
                        & (AmendmentConflict.amendment_b_id == b_id)
                    )
                    | (
                        (AmendmentConflict.amendment_a_id == b_id)
                        & (AmendmentConflict.amendment_b_id == a_id)
                    )
                )
                .first()
            )
            if not exists:
                db.session.add(
                    AmendmentConflict(
                        meeting_id=motion.meeting_id,
                        amendment_a_id=a_id,
                        amendment_b_id=b_id,
                    )
                )
                db.session.commit()
                flash("Conflict recorded", "success")
            return redirect(url_for("meetings.manage_conflicts", motion_id=motion.id))
        flash("Select two different amendments", "error")

    conflicts = (
        AmendmentConflict.query.join(
            Amendment, Amendment.id == AmendmentConflict.amendment_a_id
        )
        .filter(Amendment.motion_id == motion.id)
        .all()
    )
    return render_template(
        "meetings/manage_conflicts.html",
        motion=motion,
        amendments=amendments,
        conflicts=conflicts,
        form=form,
    )


@bp.route("/conflicts/<int:conflict_id>/delete", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def delete_conflict(conflict_id: int):
    conflict = AmendmentConflict.query.get_or_404(conflict_id)
    motion_id = Amendment.query.get(conflict.amendment_a_id).motion_id
    db.session.delete(conflict)
    db.session.commit()
    flash("Conflict removed", "success")
    return redirect(url_for("meetings.manage_conflicts", motion_id=motion_id))


def _amendment_results(meeting: Meeting) -> list[tuple[Amendment, dict]]:
    """Return vote counts for each amendment."""
    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id).order_by(Amendment.order).all()
    )
    results = []
    for amend in amendments:
        counts = {
            "for": 0,
            "against": 0,
            "abstain": 0,
        }
        rows = (
            db.session.query(Vote.choice, func.count(Vote.id))
            .filter_by(amendment_id=amend.id)
            .group_by(Vote.choice)
            .all()
        )
        for choice, count in rows:
            counts[choice] = count
        results.append((amend, counts))
    return results


def _motion_results(meeting: Meeting) -> list[tuple[Motion, dict]]:
    """Return vote counts for each motion."""
    motions = (
        Motion.query.filter_by(meeting_id=meeting.id).order_by(Motion.ordering).all()
    )
    results: list[tuple[Motion, dict]] = []
    for motion in motions:
        counts = {
            "for": 0,
            "against": 0,
            "abstain": 0,
        }
        rows = (
            db.session.query(Vote.choice, func.count(Vote.id))
            .filter_by(motion_id=motion.id)
            .group_by(Vote.choice)
            .all()
        )
        for choice, count in rows:
            counts[choice] = count
        results.append((motion, counts))
    return results


def _merge_form(motions: list[Motion]) -> FlaskForm:
    fields = {}
    for motion in motions:
        fields[f"motion_{motion.id}"] = TextAreaField(
            "Final Motion Text", validators=[DataRequired()]
        )
    fields["submit"] = SubmitField("Save and Send Stage 2 Links")
    return type("MergeForm", (FlaskForm,), fields)()


@bp.route("/<int:meeting_id>/close-stage1", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def close_stage1(meeting_id: int):
    """Close Stage 1 and handle run-offs or open Stage 2."""
    meeting = Meeting.query.get_or_404(meeting_id)

    # check whether Stage 1 reached quorum
    if meeting.stage1_votes_count() < meeting.quorum:
        meeting.status = "Quorum not met"
        db.session.commit()
        flash(
            "Stage 1 quorum not met – vote void under Articles 112(d)–(f).",
            "error",
        )
        return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))

    # finalize Stage 1 results and create run-off ballots if required
    runoffs, tokens_to_send = runoff.close_stage1(meeting)

    if runoffs:
        for member, token in tokens_to_send:
            send_runoff_invite(member, token, meeting)
        flash("Run-off ballot issued; Stage 2 start delayed", "success")
    else:
        meeting.status = "Pending Stage 2"
        db.session.commit()
        flash(
            "Stage 1 closed. Prepare final motion text before opening Stage 2",
            "success",
        )
    return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))


@bp.route("/<int:meeting_id>/results")
@login_required
@permission_required("manage_meetings")
def results_summary(meeting_id: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    results = _amendment_results(meeting)
    return render_template(
        "meetings/results_summary.html", meeting=meeting, results=results
    )


@bp.route("/<int:meeting_id>/results.docx")
@login_required
@permission_required("manage_meetings")
def results_docx(meeting_id: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    results = _amendment_results(meeting)
    include_logo = request.args.get("logo") == "1"
    doc = _styled_doc(f"{meeting.title} - Stage 1 Results", include_logo)

    table = doc.add_table(rows=1, cols=4)
    hdr = table.rows[0].cells
    hdr[0].text = "Amendment"
    hdr[1].text = "For"
    hdr[2].text = "Against"
    hdr[3].text = "Abstain"
    for cell in hdr:
        for run in cell.paragraphs[0].runs:
            run.bold = True

    for idx, (amend, counts) in enumerate(results, start=1):
        row = table.add_row().cells
        row[0].text = amend.text_md or ""
        row[1].text = str(counts["for"])
        row[2].text = str(counts["against"])
        row[3].text = str(counts["abstain"])
        if idx % 2 == 0:
            for c in row:
                _shade_cell(c, "F7F7F9")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        as_attachment=True,
        download_name="results.docx",
    )


@bp.route("/<int:meeting_id>/prepare-stage2", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def prepare_stage2(meeting_id: int):
    """Allow a human to merge amendments into final motion text."""
    meeting = Meeting.query.get_or_404(meeting_id)
    motions = (
        Motion.query.filter_by(meeting_id=meeting.id).order_by(Motion.ordering).all()
    )
    form = _merge_form(motions)
    if form.validate_on_submit():
        for motion in motions:
            data = form[f"motion_{motion.id}"].data
            motion.final_text_md = data
        members = Member.query.filter_by(meeting_id=meeting.id).all()
        tokens_to_send: list[tuple[Member, str]] = []
        for member in members:
            token_obj, plain = VoteToken.create(
                member_id=member.id,
                stage=2,
                salt=current_app.config["TOKEN_SALT"],
            )
            tokens_to_send.append((member, plain))
        meeting.status = "Stage 2"
        db.session.commit()
        for m, t in tokens_to_send:
            send_stage2_invite(m, t, meeting)
        flash("Stage 2 voting links sent", "success")
        return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))

    for motion in motions:
        field = form[f"motion_{motion.id}"]
        field.data = motion.final_text_md or compile_motion_text(motion)

    return render_template(
        "meetings/prepare_stage2.html",
        meeting=meeting,
        motions=motions,
        form=form,
        compile_motion_text=compile_motion_text,
    )


@bp.route("/<int:meeting_id>/results-stage2.docx")
@login_required
@permission_required("manage_meetings")
def results_stage2_docx(meeting_id: int):
    """Download DOCX summarising carried amendments and final motion results."""
    meeting = Meeting.query.get_or_404(meeting_id)
    amend_results = _amendment_results(meeting)
    motion_results = _motion_results(meeting)

    include_logo = request.args.get("logo") == "1"
    doc = _styled_doc(f"{meeting.title} - Final Results", include_logo)

    doc.add_heading("Carried Amendments", level=2)
    carried = [a for a, c in amend_results if c.get("for", 0) > c.get("against", 0)]
    table_ca = doc.add_table(rows=1, cols=1)
    if carried:
        for idx, amend in enumerate(carried, start=1):
            row = table_ca.add_row().cells
            row[0].text = amend.text_md or ""
            if idx % 2 == 0:
                _shade_cell(row[0], "F7F7F9")
    else:
        table_ca.rows[0].cells[0].text = "No amendments carried."

    doc.add_heading("Motion Outcomes", level=2)
    table = doc.add_table(rows=1, cols=5)
    hdr = table.rows[0].cells
    hdr[0].text = "Motion"
    hdr[1].text = "For"
    hdr[2].text = "Against"
    hdr[3].text = "Abstain"
    hdr[4].text = "Outcome"
    for cell in hdr:
        for run in cell.paragraphs[0].runs:
            run.bold = True

    for idx, (motion, counts) in enumerate(motion_results, start=1):
        row = table.add_row().cells
        row[0].text = motion.title or "Motion"
        row[1].text = str(counts["for"])
        row[2].text = str(counts["against"])
        row[3].text = str(counts["abstain"])
        row[4].text = (motion.status or "?").capitalize()
        if idx % 2 == 0:
            for c in row:
                _shade_cell(c, "F7F7F9")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name="final_results.docx",
    )


@bp.route("/<int:meeting_id>/close-stage2", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def close_stage2(meeting_id: int):
    """Finalize Stage 2 results and record motion outcomes."""
    meeting = Meeting.query.get_or_404(meeting_id)
    motion_results = _motion_results(meeting)

    for motion, counts in motion_results:
        total = counts["for"] + counts["against"] + counts["abstain"]
        if total == 0:
            motion.status = "failed"
            continue
        ratio = counts["for"] / total
        if motion.threshold == "special":
            carried = ratio >= 0.75
        else:
            carried = counts["for"] > counts["against"]
        motion.status = "carried" if carried else "failed"
    db.session.commit()
    flash('Stage 2 closed and motions tallied', 'success')
    return redirect(url_for('meetings.results_summary', meeting_id=meeting.id))


@bp.route('/<int:meeting_id>/members/<int:member_id>/resend', methods=['POST'])
@login_required
@permission_required('manage_meetings')
def resend_member_link(meeting_id: int, member_id: int):
    """Generate a new voting token for the current stage and email it."""
    meeting = Meeting.query.get_or_404(meeting_id)
    member = (
        Member.query.filter_by(id=member_id, meeting_id=meeting.id).first_or_404()
    )

    stage = 2 if meeting.status in {'Stage 2', 'Pending Stage 2'} else 1

    token_obj, plain = VoteToken.create(
        member_id=member.id, stage=stage, salt=current_app.config["TOKEN_SALT"]
    )
    db.session.commit()

    if stage == 2:
        send_stage2_invite(member, plain, meeting)
    else:
        if Runoff.query.filter_by(meeting_id=meeting.id).count() > 0:
            send_runoff_invite(member, plain, meeting)
        else:
            send_vote_invite(member, plain, meeting)

    flash('Voting link resent', 'success')
    return redirect(url_for('meetings.results_summary', meeting_id=meeting.id))
