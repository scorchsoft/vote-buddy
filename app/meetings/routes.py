from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file
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
from ..services.email import send_vote_invite, send_stage2_invite
from ..permissions import permission_required
from .forms import MeetingForm, MemberImportForm, AmendmentForm, MotionForm
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
            token = VoteToken(token=str(uuid7()), member_id=member.id, stage=1)
            db.session.add(token)
            tokens_to_send.append((member, token.token))

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
    if form.validate_on_submit():
        order = Amendment.query.filter_by(motion_id=motion.id).count() + 1
        amendment = Amendment(meeting_id=motion.meeting_id, motion_id=motion.id, text_md=form.text_md.data, order=order)
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


@bp.route('/<int:meeting_id>/close-stage1', methods=['POST'])
@login_required
@permission_required('manage_meetings')
def close_stage1(meeting_id: int):
    """Close Stage 1 and issue Stage 2 tokens."""
    meeting = Meeting.query.get_or_404(meeting_id)
    members = Member.query.filter_by(meeting_id=meeting.id).all()
    tokens_to_send: list[tuple[Member, str]] = []
    for member in members:
        token = VoteToken(token=str(uuid7()), member_id=member.id, stage=2)
        db.session.add(token)
        tokens_to_send.append((member, token.token))
    meeting.status = 'Stage 2'
    db.session.commit()
    for m, t in tokens_to_send:
        send_stage2_invite(m, t, meeting)
    flash('Stage 1 closed and Stage 2 voting links sent', 'success')
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
