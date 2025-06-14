from flask import Blueprint, render_template, redirect, url_for, request, flash
from ..extensions import db
from ..models import Meeting, Member, VoteToken
from .forms import MeetingForm, MemberImportForm
import csv
import io
from uuid6 import uuid7

bp = Blueprint('meetings', __name__, url_prefix='/meetings')

@bp.route('/')
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
def create_meeting():
    form = MeetingForm()
    if form.validate_on_submit():
        _save_meeting(form)
        return redirect(url_for('meetings.list_meetings'))
    return render_template('meetings/meetings_form.html', form=form)


@bp.route('/<int:meeting_id>/edit', methods=['GET', 'POST'])
def edit_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    form = MeetingForm(obj=meeting)
    if form.validate_on_submit():
        _save_meeting(form, meeting)
        return redirect(url_for('meetings.list_meetings'))
    return render_template('meetings/meetings_form.html', form=form, meeting=meeting)


@bp.route('/<int:meeting_id>/import-members', methods=['GET', 'POST'])
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

        db.session.commit()
        flash('Members imported successfully', 'success')
        return redirect(url_for('meetings.list_meetings'))

    return render_template('meetings/import_members.html', form=form, meeting=meeting)
