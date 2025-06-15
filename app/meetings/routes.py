from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file, current_app
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
    Motion,
    MotionOption,
    Vote,
)
from ..services.email import (
    send_vote_invite,
    send_stage2_invite,
    send_runoff_invite,
)
from ..services import runoff
from ..permissions import permission_required
from .forms import MeetingForm, MemberImportForm, AmendmentForm, MotionForm
from ..voting.routes import compile_motion_text
import csv
import io
from uuid6 import uuid7
from sqlalchemy import func
from docx import Document

bp = Blueprint('meetings', __name__, url_prefix='/meetings')

@bp.route('/')
@login_required
@permission_required('manage_meetings')
def list_meetings():
    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'title')
    direction = request.args.get('direction', 'asc')

    query = Meeting.query
    if q:
        search = f"%{q}%"
        query = query.filter(Meeting.title.ilike(search))

    if sort == 'type':
        order_attr = Meeting.type
    elif sort == 'status':
        order_attr = Meeting.status
    else:
        order_attr = Meeting.title

    query = query.order_by(
        order_attr.asc() if direction == 'asc' else order_attr.desc()
    )

    meetings = query.all()

    template = (
        'meetings/_meeting_rows.html'
        if request.headers.get('HX-Request')
        else 'meetings_list.html'
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


@bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('manage_meetings')
def create_meeting():
    form = MeetingForm()
    if form.validate_on_submit():
        _save_meeting(form)
        return redirect(url_for('meetings.list_meetings'))
    return render_template('meetings/meetings_form.html', form=form)


@bp.route('/<int:meeting_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_meetings')
def edit_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    form = MeetingForm(obj=meeting)
    if form.validate_on_submit():
        _save_meeting(form, meeting)
        return redirect(url_for('meetings.list_meetings'))
    return render_template('meetings/meetings_form.html', form=form, meeting=meeting)


@bp.route('/<int:meeting_id>/import-members', methods=['GET', 'POST'])
@login_required
@permission_required('manage_meetings')
def import_members(meeting_id):
    """Upload a CSV of members and generate vote tokens."""

    meeting = Meeting.query.get_or_404(meeting_id)
    form = MemberImportForm()
    if form.validate_on_submit():
        file_data = form.csv_file.data
        csv_text = file_data.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(csv_text))
        expected = ['member_id', 'name', 'email', 'vote_weight', 'proxy_for']
        if reader.fieldnames != expected:
            flash('CSV headers must be: ' + ', '.join(expected), 'error')
            return render_template('meetings/import_members.html', form=form, meeting=meeting)

        seen_emails: set[str] = set()
        tokens_to_send: list[tuple[Member, str]] = []
        for row in reader:
            email = row['email'].strip().lower()
            if email in seen_emails:
                flash(f'Duplicate email: {email}', 'error')
                return render_template('meetings/import_members.html', form=form, meeting=meeting)
            seen_emails.add(email)

            member = Member(
                meeting_id=meeting.id,
                name=row['name'].strip(),
                email=email,
                proxy_for=(row.get('proxy_for') or '').strip() or None,
                weight=int(row.get('vote_weight') or 1),
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
        flash('Members imported successfully', 'success')
        return redirect(url_for('meetings.list_meetings'))

    return render_template('meetings/import_members.html', form=form, meeting=meeting)


@bp.route('/<int:meeting_id>/motions')
def list_motions(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    motions = Motion.query.filter_by(meeting_id=meeting.id).order_by(Motion.ordering).all()
    return render_template('meetings/motions_list.html', meeting=meeting, motions=motions)


@bp.route('/<int:meeting_id>/motions/create', methods=['GET', 'POST'])
@login_required
@permission_required('manage_meetings')
def create_motion(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    form = MotionForm()
    if form.validate_on_submit():
        ordering = Motion.query.filter_by(meeting_id=meeting.id).count() + 1
        motion = Motion(
            meeting_id=meeting.id,
            title=form.title.data,
            text_md=form.text_md.data,
            category=form.category.data,
            threshold=form.threshold.data,
            ordering=ordering,
        )
        db.session.add(motion)
        db.session.flush()
        if form.category.data == 'multiple_choice' and form.options.data:
            for line in form.options.data.splitlines():
                text = line.strip()
                if text:
                    db.session.add(MotionOption(motion_id=motion.id, text=text))
        db.session.commit()
        return redirect(url_for('meetings.list_motions', meeting_id=meeting.id))
    return render_template('meetings/motion_form.html', form=form, motion=None)


@bp.route('/motions/<int:motion_id>')
def view_motion(motion_id):
    motion = Motion.query.get_or_404(motion_id)
    amendments = Amendment.query.filter_by(motion_id=motion.id).order_by(Amendment.order).all()
    return render_template('meetings/view_motion.html', motion=motion, amendments=amendments)


@bp.route('/motions/<int:motion_id>/amendments/add', methods=['GET', 'POST'])
@login_required
@permission_required('manage_meetings')
def add_amendment(motion_id):
    motion = Motion.query.get_or_404(motion_id)
    form = AmendmentForm()
    members = (
        Member.query.filter_by(meeting_id=motion.meeting_id)
        .order_by(Member.name)
        .all()
    )
    choices = [(m.id, m.name) for m in members]
    form.proposer_id.choices = choices
    form.seconder_id.choices = choices
    if form.validate_on_submit():
        meeting = Meeting.query.get(motion.meeting_id)
        if meeting.opens_at_stage1:
            deadline = meeting.opens_at_stage1 - timedelta(days=21)
            if datetime.utcnow() > deadline:
                flash('Amendment deadline has passed.', 'error')
                return render_template('meetings/amendment_form.html', form=form, motion=motion)

        if form.proposer_id.data == form.seconder_id.data:
            flash('Proposer cannot second their own amendment.', 'error')
            return render_template('meetings/amendment_form.html', form=form, motion=motion)

        count = Amendment.query.filter_by(
            motion_id=motion.id,
            proposer_id=form.proposer_id.data,
        ).count()
        if count >= 3:
            flash('A member may propose at most three amendments per motion.', 'error')
            return render_template('meetings/amendment_form.html', form=form, motion=motion)

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
        db.session.commit()
        return redirect(url_for('meetings.view_motion', motion_id=motion.id))
    return render_template('meetings/amendment_form.html', form=form, motion=motion)


def _amendment_results(meeting: Meeting) -> list[tuple[Amendment, dict]]:
    """Return vote counts for each amendment."""
    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id)
        .order_by(Amendment.order)
        .all()
    )
    results = []
    for amend in amendments:
        counts = {
            'for': 0,
            'against': 0,
            'abstain': 0,
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
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
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
        fields[f'motion_{motion.id}'] = TextAreaField(
            'Final Motion Text', validators=[DataRequired()]
        )
    fields['submit'] = SubmitField('Save and Send Stage 2 Links')
    return type('MergeForm', (FlaskForm,), fields)()


@bp.route('/<int:meeting_id>/close-stage1', methods=['POST'])
@login_required
@permission_required('manage_meetings')
def close_stage1(meeting_id: int):
    """Close Stage 1 and handle run-offs or open Stage 2."""
    meeting = Meeting.query.get_or_404(meeting_id)

    # finalize Stage 1 results and create run-off ballots if required
    runoffs, tokens_to_send = runoff.close_stage1(meeting)

    if runoffs:
        for member, token in tokens_to_send:
            send_runoff_invite(member, token, meeting)
        flash('Run-off ballot issued; Stage 2 start delayed', 'success')
    else:
        meeting.status = 'Pending Stage 2'
        db.session.commit()
        flash('Stage 1 closed. Prepare final motion text before opening Stage 2', 'success')
    return redirect(url_for('meetings.results_summary', meeting_id=meeting.id))


@bp.route('/<int:meeting_id>/results')
@login_required
@permission_required('manage_meetings')
def results_summary(meeting_id: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    results = _amendment_results(meeting)
    return render_template(
        'meetings/results_summary.html', meeting=meeting, results=results
    )


@bp.route('/<int:meeting_id>/results.docx')
@login_required
@permission_required('manage_meetings')
def results_docx(meeting_id: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    results = _amendment_results(meeting)
    doc = Document()
    doc.add_heading(f'{meeting.title} - Stage 1 Results', level=1)
    for amend, counts in results:
        doc.add_heading(f'Amendment {amend.order}', level=2)
        doc.add_paragraph(amend.text_md or '')
        doc.add_paragraph(f"For: {counts['for']}")
        doc.add_paragraph(f"Against: {counts['against']}")
        doc.add_paragraph(f"Abstain: {counts['abstain']}")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype=(
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ),
        as_attachment=True,
        download_name='results.docx',
    )


@bp.route('/<int:meeting_id>/prepare-stage2', methods=['GET', 'POST'])
@login_required
@permission_required('manage_meetings')
def prepare_stage2(meeting_id: int):
    """Allow a human to merge amendments into final motion text."""
    meeting = Meeting.query.get_or_404(meeting_id)
    motions = (
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
    )
    form = _merge_form(motions)
    if form.validate_on_submit():
        for motion in motions:
            data = form[f'motion_{motion.id}'].data
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
        meeting.status = 'Stage 2'
        db.session.commit()
        for m, t in tokens_to_send:
            send_stage2_invite(m, t, meeting)
        flash('Stage 2 voting links sent', 'success')
        return redirect(url_for('meetings.results_summary', meeting_id=meeting.id))

    for motion in motions:
        field = form[f'motion_{motion.id}']
        field.data = motion.final_text_md or compile_motion_text(motion)

    return render_template(
        'meetings/prepare_stage2.html',
        meeting=meeting,
        motions=motions,
        form=form,
        compile_motion_text=compile_motion_text,
    )


@bp.route('/<int:meeting_id>/results-stage2.docx')
@login_required
@permission_required('manage_meetings')
def results_stage2_docx(meeting_id: int):
    """Download DOCX summarising carried amendments and final motion results."""
    meeting = Meeting.query.get_or_404(meeting_id)
    amend_results = _amendment_results(meeting)
    motion_results = _motion_results(meeting)

    doc = Document()
    doc.add_heading(f"{meeting.title} - Final Results", level=1)

    doc.add_heading("Carried Amendments", level=2)
    carried = [a for a, c in amend_results if c.get("for", 0) > c.get("against", 0)]
    if carried:
        for amend in carried:
            doc.add_paragraph(amend.text_md or "")
    else:
        doc.add_paragraph("No amendments carried.")

    doc.add_heading("Motion Outcomes", level=2)
    for motion, counts in motion_results:
        doc.add_heading(motion.title or "Motion", level=3)
        doc.add_paragraph(motion.text_md or "")
        doc.add_paragraph(f"For: {counts['for']}")
        doc.add_paragraph(f"Against: {counts['against']}")
        doc.add_paragraph(f"Abstain: {counts['abstain']}")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        as_attachment=True,
        download_name='final_results.docx',
    )
