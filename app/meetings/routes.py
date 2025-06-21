from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    abort,
    send_file,
    current_app,
    send_from_directory,
)
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from ..extensions import db
from ..models import (
    Meeting,
    Member,
    VoteToken,
    Amendment,
    AmendmentMerge,
    AmendmentConflict,
    AmendmentObjection,
    Motion,
    MotionOption,
    Vote,
    Runoff,
    AppSetting,
)
from ..services.email import (
    send_vote_invite,
    send_stage2_invite,
    send_runoff_invite,
    send_quorum_failure,
    send_final_results,
    send_objection_confirmation,
    send_proxy_invite,
)
from ..services import runoff
from ..permissions import permission_required
from .forms import (
    MeetingForm,
    MemberImportForm,
    AmendmentForm,
    MotionForm,
    ConflictForm,
    ObjectionForm,
    ManualEmailForm,
    ExtendStageForm,
    MotionChangeRequestForm,
)
from ..voting.routes import (
    compile_motion_text,
    _amendment_form,
    _motion_form,
    _combined_form,
)
from ..utils import generate_stage_ics
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
        logo_path = os.path.join(current_app.root_path, "..", "assets", "logo.png")
        footer = doc.sections[0].footer
        fp = footer.add_paragraph()
        fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        fp_run = fp.add_run()
        try:
            fp_run.add_picture(logo_path, width=Inches(1))
        except Exception:
            pass

    return doc


def _calculate_default_times(agm_date: datetime) -> dict:
    """Return default timeline values relative to the AGM date."""
    cfg = current_app.config
    opens_at_stage2 = agm_date - timedelta(days=cfg.get("STAGE2_LENGTH_DAYS", 5))
    closes_at_stage1 = opens_at_stage2 - timedelta(days=cfg.get("STAGE_GAP_DAYS", 1))
    opens_at_stage1 = closes_at_stage1 - timedelta(days=cfg.get("STAGE1_LENGTH_DAYS", 7))
    notice_date = opens_at_stage1 - timedelta(days=cfg.get("NOTICE_PERIOD_DAYS", 14))
    return {
        "notice_date": notice_date,
        "opens_at_stage1": opens_at_stage1,
        "closes_at_stage1": closes_at_stage1,
        "opens_at_stage2": opens_at_stage2,
        "closes_at_stage2": agm_date,
    }


def _prefill_form_defaults(form: MeetingForm) -> None:
    """Set form defaults based on AGM date if fields are empty."""
    if form.closes_at_stage2.data:
        defaults = _calculate_default_times(form.closes_at_stage2.data)
        for field, value in defaults.items():
            if getattr(form, field).data is None:
                getattr(form, field).data = value


@bp.route("/")
@login_required
@permission_required("manage_meetings")
def list_meetings():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "title")
    direction = request.args.get("direction", "asc")

    page = request.args.get("page", 1, type=int)
    per_page = current_app.config.get("MEETINGS_PER_PAGE", 20)

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

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    meetings = pagination.items

    # Only return partial template for specific HTMX requests (search/sort/pagination)
    # Not for general page navigation via hx-boost
    if request.headers.get("HX-Request") and request.headers.get("HX-Target") == "meeting-table-body":
        template = "meetings/_meeting_rows.html"
    else:
        template = "meetings_list.html"
    
    return render_template(
        template,
        meetings=meetings,
        pagination=pagination,
        q=q,
        sort=sort,
        direction=direction,
    )


def _save_meeting(form: MeetingForm, meeting: Meeting | None = None) -> Meeting:
    """Populate Meeting from form and save."""
    if meeting is None:
        meeting = Meeting()
    _prefill_form_defaults(form)
    form.populate_obj(meeting)
    db.session.add(meeting)
    db.session.commit()
    if (
        not meeting.opens_at_stage1
        and Amendment.query.filter_by(meeting_id=meeting.id).count() == 0
    ):
        meeting.status = "Pending Stage 2"
        db.session.commit()
    return meeting


@bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def create_meeting():
    form = MeetingForm()
    notice_days = current_app.config.get("NOTICE_PERIOD_DAYS", 14)
    form.notice_date.description = (
        f"Must be at least {notice_days} days before Stage 1 opens."
    )
    form.opens_at_stage1.description = (
        f"At least {notice_days} days after notice date."
    )
    form.closes_at_stage1.description = "Must remain open for at least 7 days."
    form.opens_at_stage2.description = "At least 1 day after Stage 1 closes."
    form.closes_at_stage2.description = (
        "Final voting deadline; at least 5 days after Stage 2 opens."
    )
    if request.method == "GET":
        _prefill_form_defaults(form)
    if form.validate_on_submit():
        _save_meeting(form)
        return redirect(url_for("meetings.list_meetings"))
    return render_template("meetings/meetings_form.html", form=form)


@bp.route("/<int:meeting_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def edit_meeting(meeting_id):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    form = MeetingForm(obj=meeting)
    notice_days = current_app.config.get("NOTICE_PERIOD_DAYS", 14)
    form.notice_date.description = (
        f"Must be at least {notice_days} days before Stage 1 opens."
    )
    form.opens_at_stage1.description = (
        f"At least {notice_days} days after notice date."
    )
    form.closes_at_stage1.description = "Must remain open for at least 7 days."
    form.opens_at_stage2.description = "At least 1 day after Stage 1 closes."
    form.closes_at_stage2.description = (
        "Final voting deadline; at least 5 days after Stage 2 opens."
    )
    if request.method == "GET":
        _prefill_form_defaults(form)
    if form.validate_on_submit():
        _save_meeting(form, meeting)
        return redirect(url_for("meetings.list_meetings"))
    return render_template("meetings/meetings_form.html", form=form, meeting=meeting)


@bp.route("/<int:meeting_id>/clone")
@login_required
@permission_required("manage_meetings")
def clone_meeting(meeting_id: int):
    """Duplicate a meeting along with its motions and amendments."""
    src = db.session.get(Meeting, meeting_id)
    if src is None:
        abort(404)
    new_meeting = Meeting()
    for field in [
        "title",
        "type",
        "ballot_mode",
        "revoting_allowed",
        "status",
        "chair_notes_md",
        "quorum",
        "public_results",
        "early_public_results",
        "comments_enabled",
        "extension_reason",
        "results_doc_published",
        "results_doc_intro_md",
    ]:
        setattr(new_meeting, field, getattr(src, field))
    db.session.add(new_meeting)
    db.session.flush()

    motion_map: dict[int, int] = {}
    for motion in Motion.query.filter_by(meeting_id=src.id).all():
        new_motion = Motion(
            meeting_id=new_meeting.id,
            title=motion.title,
            text_md=motion.text_md,
            final_text_md=motion.final_text_md,
            category=motion.category,
            threshold=motion.threshold,
            ordering=motion.ordering,
            status=motion.status,
            withdrawn=motion.withdrawn,
        )
        db.session.add(new_motion)
        db.session.flush()
        for opt in motion.options:
            db.session.add(MotionOption(motion_id=new_motion.id, text=opt.text))
        motion_map[motion.id] = new_motion.id

    for amend in Amendment.query.filter_by(meeting_id=src.id).all():
        new_amend = Amendment(
            meeting_id=new_meeting.id,
            motion_id=motion_map.get(amend.motion_id),
            text_md=amend.text_md,
            order=amend.order,
            status=amend.status,
            reason=amend.reason,
            board_seconded=amend.board_seconded,
            tie_break_method=amend.tie_break_method,
        )
        db.session.add(new_amend)

    db.session.commit()
    return redirect(url_for("meetings.edit_meeting", meeting_id=new_meeting.id))


@bp.route("/<int:meeting_id>/import-members", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def import_members(meeting_id):
    """Upload a CSV of members and generate vote tokens."""

    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    form = MemberImportForm()
    if form.validate_on_submit():
        file_data = form.csv_file.data
        csv_text = file_data.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(csv_text))
        expected = ["member_id", "name", "email", "proxy_for"]
        if reader.fieldnames != expected:
            flash("CSV headers must be: " + ", ".join(expected), "error")
            return render_template(
                "meetings/import_members.html", form=form, meeting=meeting
            )

        seen_emails: set[str] = set()
        tokens_to_send: list[tuple[Member, str]] = []
        proxy_tokens: list[tuple[Member, Member, str]] = []
        for idx, row in enumerate(reader, start=2):
            name = row["name"].strip()
            email = row["email"].strip().lower()

            if not name:
                flash(f"Row {idx}: name is required", "error")
                return render_template(
                    "meetings/import_members.html", form=form, meeting=meeting
                )
            if not email or "@" not in email:
                flash(f"Row {idx}: invalid email: {email}", "error")
                return render_template(
                    "meetings/import_members.html", form=form, meeting=meeting
                )
            if email in seen_emails or Member.query.filter_by(meeting_id=meeting.id, email=email).first():
                flash(f"Duplicate email: {email}", "error")
                return render_template(
                    "meetings/import_members.html", form=form, meeting=meeting
                )
            seen_emails.add(email)


            member = Member(
                meeting_id=meeting.id,
                member_number=row.get("member_id"),
                name=name,
                email=email,
                proxy_for=(row.get("proxy_for") or "").strip() or None,
            )
            db.session.add(member)
            db.session.flush()
            if meeting.ballot_mode != "in-person":
                token_obj, plain = VoteToken.create(
                    member_id=member.id,
                    stage=1,
                    salt=current_app.config["TOKEN_SALT"],
                )
                tokens_to_send.append((member, plain))

        db.session.commit()
        # create proxy tokens after all members exist
        members = Member.query.filter_by(meeting_id=meeting.id).all()
        for proxy in members:
            if proxy.proxy_for:
                try:
                    target = db.session.get(Member, int(proxy.proxy_for))
                except (ValueError, TypeError):
                    target = None
                if target and meeting.ballot_mode != "in-person":
                    token_obj, plain = VoteToken.create(
                        member_id=target.id,
                        stage=1,
                        salt=current_app.config["TOKEN_SALT"],
                        proxy_holder_id=proxy.id,
                    )
                    proxy_tokens.append((proxy, target, plain))
        db.session.commit()

        if AppSetting.get("manual_email_mode") != "1":
            for m, t in tokens_to_send:
                send_vote_invite(m, t, meeting)
            for p, target, tok in proxy_tokens:
                send_proxy_invite(p, target, tok, meeting)
        else:
            flash("Automatic emails disabled - use manual send", "warning")
        flash("Members imported successfully", "success")
        return redirect(url_for("meetings.list_meetings"))

    return render_template("meetings/import_members.html", form=form, meeting=meeting)


@bp.route("/sample-members.csv")
@login_required
@permission_required("manage_meetings")
def download_sample_csv():
    """Serve a template CSV for member uploads."""
    path = os.path.join(current_app.root_path, "static", "sample_members.csv")
    return send_file(path, mimetype="text/csv", as_attachment=True, download_name="sample_members.csv")


@bp.route("/<int:meeting_id>/motions")
@login_required
@permission_required("manage_meetings")
def list_motions(meeting_id):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
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
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
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
    motion = db.session.get(Motion, motion_id)
    if motion is None:
        abort(404)
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


@bp.route("/motions/<int:motion_id>/request-change", methods=["GET", "POST"])
@login_required
def request_motion_change(motion_id: int):
    """Allow a user to request withdrawal or major edit of a motion."""
    motion = db.session.get(Motion, motion_id)
    if motion is None:
        abort(404)
    meeting = db.session.get(Meeting, motion.meeting_id)
    if meeting is None:
        abort(404)
    if meeting.opens_at_stage1 and datetime.utcnow() > meeting.opens_at_stage1 - timedelta(days=7):
        flash("Change requests must be made at least 7 days before Stage 1 opens.", "error")
        return redirect(url_for("meetings.view_motion", motion_id=motion.id))
    form = MotionChangeRequestForm()
    if request.method == "GET":
        form.text_md.data = motion.text_md
    if form.validate_on_submit():
        if form.text_md.data and form.text_md.data != motion.text_md:
            motion.text_md = form.text_md.data
            motion.modified_at = datetime.utcnow()
            motion.withdrawal_requested_at = datetime.utcnow()
        if form.withdraw.data:
            motion.withdrawal_requested_at = datetime.utcnow()
        db.session.commit()
        flash("Request submitted", "success")
        return redirect(url_for("meetings.view_motion", motion_id=motion.id))
    return render_template("meetings/motion_change_form.html", form=form, motion=motion)


@bp.route("/motions/<int:motion_id>/approve-change/<actor>", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def approve_motion_change(motion_id: int, actor: str):
    """Approve a withdrawal/edit request as chair or board."""
    motion = db.session.get(Motion, motion_id)
    if motion is None:
        abort(404)
    now = datetime.utcnow()
    if actor == "chair":
        motion.chair_approved_at = now
    elif actor == "board":
        motion.board_approved_at = now
    else:
        abort(404)
    if motion.chair_approved_at and motion.board_approved_at:
        if motion.withdrawal_requested_at:
            motion.withdrawn = True
    db.session.commit()
    flash("Request approved", "success")
    return redirect(url_for("meetings.view_motion", motion_id=motion.id))


@bp.route("/motions/<int:motion_id>/reject-change", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def reject_motion_change(motion_id: int):
    """Reject a withdrawal/edit request."""
    motion = db.session.get(Motion, motion_id)
    if motion is None:
        abort(404)
    motion.withdrawal_requested_at = None
    motion.chair_approved_at = None
    motion.board_approved_at = None
    db.session.commit()
    flash("Request rejected", "success")
    return redirect(url_for("meetings.view_motion", motion_id=motion.id))


@bp.route("/motions/<int:motion_id>/amendments/add", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def add_amendment(motion_id):
    motion = db.session.get(Motion, motion_id)
    if motion is None:
        abort(404)
    form = AmendmentForm()
    members = (
        Member.query.filter_by(meeting_id=motion.meeting_id).order_by(Member.name).all()
    )
    choices = [(m.id, m.name) for m in members]
    form.proposer_id.choices = choices
    form.seconder_id.choices = [(0, "")] + choices
    if form.validate_on_submit():
        meeting = db.session.get(Meeting, motion.meeting_id)
        deadline = None
        if meeting.opens_at_stage1:
            deadline = meeting.opens_at_stage1 - timedelta(days=21)
        elif meeting.notice_date:
            notice_days = current_app.config.get("NOTICE_PERIOD_DAYS", 14)
            deadline = meeting.notice_date + timedelta(days=notice_days)

        if deadline and datetime.utcnow() > deadline:
            flash("Amendment deadline has passed.", "error")
            return render_template(
                "meetings/amendment_form.html", form=form, motion=motion
            )

        if not form.seconder_id.data and not form.board_seconded.data:
            flash("Select a seconder or confirm board approval.", "error")
            return render_template(
                "meetings/amendment_form.html", form=form, motion=motion
            )
        if form.seconder_id.data and form.proposer_id.data == form.seconder_id.data:
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
            seconder_id=(
                (form.seconder_id.data or None)
                if not form.board_seconded.data
                else None
            ),
            board_seconded=form.board_seconded.data,
            seconded_method=form.seconded_method.data or None,
            seconded_at=datetime.utcnow() if form.seconded_method.data else None,
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
                src = db.session.get(Amendment, src_id)
                if src:
                    src.status = "merged"

        db.session.commit()
        return redirect(url_for("meetings.view_motion", motion_id=motion.id))
    return render_template("meetings/amendment_form.html", form=form, motion=motion)


@bp.route("/amendments/<int:amendment_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def edit_amendment(amendment_id: int):
    """Edit an existing amendment."""
    amendment = db.session.get(Amendment, amendment_id)
    if amendment is None:
        abort(404)
    motion = db.session.get(Motion, amendment.motion_id)
    if motion is None:
        abort(404)
    meeting = db.session.get(Meeting, amendment.meeting_id)

    form = AmendmentForm(obj=amendment)
    members = Member.query.filter_by(meeting_id=meeting.id).order_by(Member.name).all()
    choices = [(m.id, m.name) for m in members]
    form.proposer_id.choices = choices
    form.seconder_id.choices = [(0, "")] + choices

    if form.validate_on_submit():
        if meeting.opens_at_stage1:
            deadline = meeting.opens_at_stage1 - timedelta(days=21)
            if datetime.utcnow() > deadline:
                flash("Amendment deadline has passed.", "error")
                return render_template(
                    "meetings/amendment_form.html",
                    form=form,
                    motion=motion,
                    amendment=amendment,
                )

        if not form.seconder_id.data and not form.board_seconded.data:
            flash("Select a seconder or confirm board approval.", "error")
            return render_template(
                "meetings/amendment_form.html",
                form=form,
                motion=motion,
                amendment=amendment,
            )
        if form.seconder_id.data and form.proposer_id.data == form.seconder_id.data:
            flash("Proposer cannot second their own amendment.", "error")
            return render_template(
                "meetings/amendment_form.html",
                form=form,
                motion=motion,
                amendment=amendment,
            )

        amendment.text_md = form.text_md.data
        amendment.proposer_id = form.proposer_id.data
        amendment.seconder_id = (
            form.seconder_id.data or None if not form.board_seconded.data else None
        )
        amendment.board_seconded = form.board_seconded.data
        amendment.seconded_method = form.seconded_method.data or None
        amendment.seconded_at = (
            datetime.utcnow() if form.seconded_method.data else None
        )
        db.session.commit()
        flash("Amendment updated", "success")
        return redirect(url_for("meetings.view_motion", motion_id=motion.id))

    return render_template(
        "meetings/amendment_form.html",
        form=form,
        motion=motion,
        amendment=amendment,
    )


@bp.route("/amendments/<int:amendment_id>/delete", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def delete_amendment(amendment_id: int):
    """Delete an amendment."""
    amendment = db.session.get(Amendment, amendment_id)
    if amendment is None:
        abort(404)
    meeting = db.session.get(Meeting, amendment.meeting_id)
    motion_id = amendment.motion_id

    if meeting.opens_at_stage1:
        deadline = meeting.opens_at_stage1 - timedelta(days=21)
        if datetime.utcnow() > deadline:
            flash("Amendment deadline has passed.", "error")
            return redirect(url_for("meetings.view_motion", motion_id=motion_id))

    db.session.delete(amendment)
    db.session.commit()
    flash("Amendment deleted", "success")
    return redirect(url_for("meetings.view_motion", motion_id=motion_id))


@bp.route("/amendments/<int:amendment_id>/reject", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def reject_amendment(amendment_id: int):
    """Mark an amendment as rejected."""
    amendment = db.session.get(Amendment, amendment_id)
    if amendment is None:
        abort(404)
    amendment.status = "rejected"
    amendment.reason = request.form.get("reason")
    db.session.commit()
    flash("Amendment marked as rejected", "success")
    return redirect(url_for("meetings.view_motion", motion_id=amendment.motion_id))


@bp.route("/amendments/<int:amendment_id>/mark-merged", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def mark_amendment_merged(amendment_id: int):
    """Mark an amendment as merged into another."""
    amendment = db.session.get(Amendment, amendment_id)
    if amendment is None:
        abort(404)
    amendment.status = "merged"
    amendment.reason = request.form.get("reason")
    db.session.commit()
    flash("Amendment marked as merged", "success")
    return redirect(url_for("meetings.view_motion", motion_id=amendment.motion_id))


@bp.route("/<int:meeting_id>/member-search")
def member_search(meeting_id: int):
    """Return member options filtered by query."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    q = request.args.get("q", "").strip()
    query = Member.query.filter_by(meeting_id=meeting.id)
    if q:
        query = query.filter(Member.name.ilike(f"%{q}%"))
    members = query.order_by(Member.name).limit(20).all()
    return render_template("meetings/_member_options.html", members=members)


@bp.route("/amendments/<int:amendment_id>/object", methods=["GET", "POST"])
def submit_objection(amendment_id: int):
    """Allow a member to submit an objection."""
    amendment = db.session.get(Amendment, amendment_id)
    if amendment is None:
        abort(404)
    meeting = db.session.get(Meeting, amendment.meeting_id)
    if meeting is None:
        abort(404)
    form = ObjectionForm()
    if form.validate_on_submit():
        try:
            member_id = int(form.member_id.data)
        except (TypeError, ValueError):
            flash("Invalid member", "error")
            return render_template(
                "meetings/objection_form.html", form=form, amendment=amendment
            )

        member = Member.query.filter_by(id=member_id, meeting_id=meeting.id).first()
        if not member:
            flash("Member not found", "error")
            return render_template(
                "meetings/objection_form.html", form=form, amendment=amendment
            )

        obj = AmendmentObjection(
            amendment_id=amendment.id,
            member_id=member.id,
            email=form.email.data.strip().lower(),
            token=str(uuid7()),
        )
        db.session.add(obj)
        db.session.commit()
        send_objection_confirmation(obj, amendment, meeting)
        flash("Check your email to confirm the objection", "success")
        return redirect(url_for("meetings.view_motion", motion_id=amendment.motion_id))
    return render_template(
        "meetings/objection_form.html", form=form, amendment=amendment
    )


@bp.get("/objection/confirm/<token>")
def confirm_objection(token: str):
    obj = AmendmentObjection.query.filter_by(token=token).first_or_404()
    if not obj.confirmed_at:
        obj.confirmed_at = datetime.utcnow()
        obj.deadline_first = obj.created_at + timedelta(days=5)
        db.session.commit()
    return render_template("meetings/objection_confirmed.html", objection=obj)


@bp.route("/motions/<int:motion_id>/conflicts", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def manage_conflicts(motion_id: int):
    motion = db.session.get(Motion, motion_id)
    if motion is None:
        abort(404)
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
    conflict = db.session.get(AmendmentConflict, conflict_id)
    if conflict is None:
        abort(404)
    motion_id = db.session.get(Amendment, conflict.amendment_a_id).motion_id
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
            .filter(Vote.is_test.is_(False))
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
            .filter(Vote.is_test.is_(False))
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
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None or meeting.ballot_mode == "in-person":
        abort(404)

    meeting.stage1_closed_at = datetime.utcnow()

    # check whether Stage 1 reached quorum
    if meeting.stage1_votes_count() < meeting.quorum:
        meeting.status = "Quorum not met"
        db.session.commit()
        if meeting.opens_at_stage2 and meeting.stage1_closed_at:
            if meeting.opens_at_stage2 - meeting.stage1_closed_at < timedelta(hours=24):
                flash(
                    "Stage 2 opens less than 24 hours after Stage 1 closed",
                    "warning",
                )
        members = Member.query.filter_by(meeting_id=meeting.id).all()
        if AppSetting.get("manual_email_mode") != "1":
            for member in members:
                send_quorum_failure(member, meeting)
        else:
            flash("Automatic emails disabled - use manual send", "warning")
        flash(
            "Stage 1 quorum not met – vote void under Articles 112(d)–(f).",
            "error",
        )
        return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))

    # if no amendments were proposed, skip Stage 1 entirely
    if Amendment.query.filter_by(meeting_id=meeting.id).count() == 0:
        members = Member.query.filter_by(meeting_id=meeting.id).all()
        if meeting.ballot_mode != "in-person":
            for member in members:
                VoteToken.create(
                    member_id=member.id,
                    stage=2,
                    salt=current_app.config["TOKEN_SALT"],
                )
        meeting.status = "Pending Stage 2"
        db.session.commit()
        if meeting.opens_at_stage2 and meeting.stage1_closed_at:
            if meeting.opens_at_stage2 - meeting.stage1_closed_at < timedelta(hours=24):
                flash(
                    "Stage 2 opens less than 24 hours after Stage 1 closed",
                    "warning",
                )
        flash(
            "No amendments submitted – Stage 1 skipped and Stage 2 tokens generated",
            "success",
        )
        return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))

    # finalize Stage 1 results and create run-off ballots if required
    runoffs, tokens_to_send = runoff.close_stage1(meeting)

    if runoffs:
        if AppSetting.get("manual_email_mode") != "1":
            for recipient, target, token in tokens_to_send:
                if target:
                    send_proxy_invite(recipient, target, token, meeting)
                else:
                    send_runoff_invite(recipient, token, meeting)
        else:
            flash("Automatic emails disabled - use manual send", "warning")
        flash("Run-off ballot issued; Stage 2 start delayed", "success")
    else:
        meeting.status = "Pending Stage 2"
        db.session.commit()
        if meeting.opens_at_stage2 and meeting.stage1_closed_at:
            if meeting.opens_at_stage2 - meeting.stage1_closed_at < timedelta(hours=24):
                flash(
                    "Stage 2 opens less than 24 hours after Stage 1 closed",
                    "warning",
                )
        flash(
            "Stage 1 closed. Prepare final motion text before opening Stage 2",
            "success",
        )
    return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))


@bp.route("/<int:meeting_id>/results")
@login_required
@permission_required("manage_meetings")
def results_summary(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    results = _amendment_results(meeting)
    return render_template(
        "meetings/results_summary.html", meeting=meeting, results=results
    )


@bp.route("/<int:meeting_id>/send-emails", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def manual_send_emails(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None or meeting.ballot_mode == "in-person":
        abort(404)
    form = ManualEmailForm()
    members = Member.query.filter_by(meeting_id=meeting.id, is_test=False).order_by(Member.name).all()
    form.member_ids.choices = [(m.id, m.name) for m in members]
    if form.validate_on_submit():
        recipients = []
        if form.test_mode.data:
            current_user_member = Member.query.filter_by(meeting_id=meeting.id, email=current_user.email).first()
            if not current_user_member:
                current_user_member = Member(
                    meeting_id=meeting.id,
                    name=current_user.email,
                    email=current_user.email,
                    is_test=True,
                )
                db.session.add(current_user_member)
                db.session.commit()
            recipients = [current_user_member]
        elif form.send_to_all.data:
            recipients = members
        else:
            recipients = [m for m in members if m.id in form.member_ids.data]

        for member in recipients:
            stage = 1
            if form.email_type.data == "stage2_invite":
                stage = 2
            token_obj, plain = VoteToken.create(
                member_id=member.id,
                stage=stage,
                salt=current_app.config["TOKEN_SALT"],
            )
            token_obj.is_test = form.test_mode.data
            db.session.commit()

            if form.email_type.data == "stage1_invite":
                send_vote_invite(member, plain, meeting, test_mode=form.test_mode.data)
            elif form.email_type.data == "stage1_reminder":
                send_stage1_reminder(member, plain, meeting, test_mode=form.test_mode.data)
            elif form.email_type.data == "runoff_invite":
                send_runoff_invite(member, plain, meeting, test_mode=form.test_mode.data)
            elif form.email_type.data == "stage2_invite":
                send_stage2_invite(member, plain, meeting, test_mode=form.test_mode.data)

        flash("Emails sent", "success")
        return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))

    return render_template("meetings/manual_email.html", meeting=meeting, form=form)


@bp.route("/<int:meeting_id>/extend/<int:stage>", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def extend_stage(meeting_id: int, stage: int):
    """Allow admin to extend Stage 1 or 2 voting window."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None or stage not in (1, 2):
        abort(404)
    form = ExtendStageForm()
    if request.method == "GET":
        if stage == 1:
            form.opens_at.data = meeting.opens_at_stage1
            form.closes_at.data = meeting.closes_at_stage1
        else:
            form.opens_at.data = meeting.opens_at_stage2
            form.closes_at.data = meeting.closes_at_stage2
    if form.validate_on_submit():
        if stage == 1:
            meeting.opens_at_stage1 = form.opens_at.data
            meeting.closes_at_stage1 = form.closes_at.data
        else:
            meeting.opens_at_stage2 = form.opens_at.data
            meeting.closes_at_stage2 = form.closes_at.data
        meeting.extension_reason = form.reason.data
        db.session.commit()
        flash("Stage dates updated", "success")
        return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))
    return render_template(
        "meetings/extend_stage.html",
        form=form,
        meeting=meeting,
        stage=stage,
    )


@bp.route("/<int:meeting_id>/stage1-tally", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def stage1_tally(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None or meeting.ballot_mode != "in-person":
        abort(404)
    form = Stage1TallyForm()
    if request.method == "GET":
        form.votes_cast.data = meeting.stage1_manual_votes
    if form.validate_on_submit():
        meeting.stage1_manual_votes = form.votes_cast.data or 0
        meeting.status = "Pending Stage 2"
        db.session.commit()
        flash("Stage 1 tally saved", "success")
        return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))
    return render_template(
        "meetings/stage1_tally_form.html",
        form=form,
        meeting=meeting,
    )


@bp.route("/<int:meeting_id>/stage2-tally", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def stage2_tally(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None or meeting.ballot_mode != "in-person":
        abort(404)
    form = Stage2TallyForm()
    if request.method == "GET":
        form.for_votes.data = meeting.stage2_manual_for
        form.against_votes.data = meeting.stage2_manual_against
        form.abstain_votes.data = meeting.stage2_manual_abstain
    if form.validate_on_submit():
        meeting.stage2_manual_for = form.for_votes.data or 0
        meeting.stage2_manual_against = form.against_votes.data or 0
        meeting.stage2_manual_abstain = form.abstain_votes.data or 0
        meeting.status = "Completed"
        db.session.commit()
        flash("Stage 2 tally saved", "success")
        return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))
    return render_template(
        "meetings/stage2_tally_form.html",
        form=form,
        meeting=meeting,
    )


@bp.route("/<int:meeting_id>/preview/<int:stage>", methods=["GET", "POST"])
@login_required
@permission_required("manage_meetings")
def preview_voting(meeting_id: int, stage: int):
    """Display a preview of the voting screens without recording votes."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)

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
            flash("Preview submission complete – votes were not saved", "info")
            return render_template("voting/confirmation.html", preview=True)
        motions_grouped = []
        for motion in motions:
            ams = [a for a in amendments if a.motion_id == motion.id]
            motions_grouped.append((motion, ams))
        return render_template(
            "voting/combined_ballot.html",
            form=form,
            motions=motions_grouped,
            meeting=meeting,
            proxy_for=None,
            token="preview",
            preview=True,
        )

    if stage == 1:
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
            flash("Preview submission complete – votes were not saved", "info")
            return render_template("voting/confirmation.html", preview=True)
        motions_grouped = []
        for motion in motions:
            ams = [a for a in amendments if a.motion_id == motion.id]
            motions_grouped.append((motion, ams))
        return render_template(
            "voting/stage1_ballot.html",
            form=form,
            motions=motions_grouped,
            meeting=meeting,
            proxy_for=None,
            token="preview",
            preview=True,
        )

    motions = (
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
    )
    form = _motion_form(motions)
    if form.validate_on_submit():
        flash("Preview submission complete – votes were not saved", "info")
        return render_template("voting/confirmation.html", preview=True)
    compiled = [
        (m, m.final_text_md or compile_motion_text(m)) for m in motions
    ]
    return render_template(
        "voting/stage2_ballot.html",
        form=form,
        motions=compiled,
        meeting=meeting,
        proxy_for=None,
        token="preview",
        preview=True,
    )


@bp.route("/<int:meeting_id>/results.docx")
@login_required
@permission_required("manage_meetings")
def results_docx(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
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
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None or meeting.ballot_mode == "in-person":
        abort(404)
    if meeting.opens_at_stage2 and meeting.stage1_closed_at:
        if meeting.opens_at_stage2 - meeting.stage1_closed_at < timedelta(hours=24):
            flash(
                "Stage 2 opens less than 24 hours after Stage 1 closed",
                "warning",
            )
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
        proxy_tokens: list[tuple[Member, Member, str]] = []
        for member in members:
            token_obj, plain = VoteToken.create(
                member_id=member.id,
                stage=2,
                salt=current_app.config["TOKEN_SALT"],
            )
            tokens_to_send.append((member, plain))
        for proxy in members:
            if proxy.proxy_for:
                try:
                    target = db.session.get(Member, int(proxy.proxy_for))
                except (ValueError, TypeError):
                    target = None
                if target:
                    token_obj, plain = VoteToken.create(
                        member_id=target.id,
                        stage=2,
                        salt=current_app.config["TOKEN_SALT"],
                        proxy_holder_id=proxy.id,
                    )
                    proxy_tokens.append((proxy, target, plain))
        meeting.status = "Stage 2"
        db.session.commit()
        if AppSetting.get("manual_email_mode") != "1":
            for m, t in tokens_to_send:
                send_stage2_invite(m, t, meeting)
            for p, target, tok in proxy_tokens:
                send_proxy_invite(p, target, tok, meeting)
        else:
            flash("Automatic emails disabled - use manual send", "warning")
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
def results_stage2_docx(meeting_id: int):
    """Download DOCX summarising carried amendments and final motion results."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    if not meeting.public_results or not meeting.results_doc_published:
        abort(404)
    amend_results = _amendment_results(meeting)
    motion_results = _motion_results(meeting)

    include_logo = request.args.get("logo") == "1"
    doc = _styled_doc(f"{meeting.title} - Final Results", include_logo)
    para = doc.add_paragraph(
        "This document is a draft summary. The organisation reserves the right to issue a final official version." )
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if meeting.results_doc_intro_md:
        doc.add_paragraph(meeting.results_doc_intro_md)

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


@bp.route("/<int:meeting_id>/stage1.ics")
@login_required
@permission_required("manage_meetings")
def stage1_ics(meeting_id: int):
    """Download Stage 1 calendar file."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    try:
        ics = generate_stage_ics(meeting, 1)
    except ValueError:
        flash("Stage 1 timestamps not set", "error")
        return redirect(request.referrer or url_for("meetings.list_meetings"))
    return send_file(
        io.BytesIO(ics),
        mimetype="text/calendar",
        as_attachment=True,
        download_name="stage1.ics",
    )


@bp.route("/<int:meeting_id>/stage2.ics")
@login_required
@permission_required("manage_meetings")
def stage2_ics(meeting_id: int):
    """Download Stage 2 calendar file."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    try:
        ics = generate_stage_ics(meeting, 2)
    except ValueError:
        flash("Stage 2 timestamps not set", "error")
        return redirect(request.referrer or url_for("meetings.list_meetings"))
    return send_file(
        io.BytesIO(ics),
        mimetype="text/calendar",
        as_attachment=True,
        download_name="stage2.ics",
    )


@bp.route("/<int:meeting_id>/close-runoff", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def close_runoff(meeting_id: int):
    """Finalize run-off results and move meeting to Pending Stage 2."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    runoff.close_runoff_stage(meeting)
    meeting.status = "Pending Stage 2"
    db.session.commit()
    flash("Run-off votes tallied", "success")
    return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))


@bp.route("/<int:meeting_id>/close-stage2", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def close_stage2(meeting_id: int):
    """Finalize Stage 2 results and record motion outcomes."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None or meeting.ballot_mode == "in-person":
        abort(404)
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

    meeting.status = "Completed"
    db.session.commit()

    members = Member.query.filter_by(meeting_id=meeting.id).all()
    if AppSetting.get("manual_email_mode") != "1":
        for member in members:
            send_final_results(member, meeting)
    else:
        flash("Automatic emails disabled - use manual send", "warning")

    flash("Stage 2 closed and motions tallied", "success")
    return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))


@bp.route("/<int:meeting_id>/members/<int:member_id>/resend", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def resend_member_link(meeting_id: int, member_id: int):
    """Generate a new voting token for the current stage and email it."""
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None or meeting.ballot_mode == "in-person":
        abort(404)
    member = Member.query.filter_by(id=member_id, meeting_id=meeting.id).first_or_404()

    stage = 2 if meeting.status in {"Stage 2", "Pending Stage 2"} else 1

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

    flash("Voting link resent", "success")
    return redirect(url_for("meetings.results_summary", meeting_id=meeting.id))
