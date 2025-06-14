from flask import Blueprint, render_template, redirect, url_for
from ..extensions import db
from ..models import Meeting
from .forms import MeetingForm

bp = Blueprint('meetings', __name__, url_prefix='/meetings')

@bp.route('/')
def list_meetings():
    return render_template('meetings/list.html')


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
