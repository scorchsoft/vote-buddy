from flask import Blueprint, render_template, abort
from .extensions import db
from .models import Meeting, Amendment, Motion, Vote
from sqlalchemy import func

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/results')
def results_index():
    """List meetings with public results."""
    meetings = (
        Meeting.query.filter_by(public_results=True)
        .order_by(Meeting.title)
        .all()
    )
    return render_template('results_index.html', meetings=meetings)


def _vote_counts(query):
    counts = {'for': 0, 'against': 0, 'abstain': 0}
    rows = (
        db.session.query(Vote.choice, func.count(Vote.id))
        .filter(query)
        .group_by(Vote.choice)
        .all()
    )
    for choice, count in rows:
        counts[choice] = count
    return counts


@bp.route('/results/<int:meeting_id>')
def public_results(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    if not meeting.public_results:
        abort(404)

    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id)
        .order_by(Amendment.order)
        .all()
    )
    stage1 = []
    for amend in amendments:
        stage1.append((amend, _vote_counts(Vote.amendment_id == amend.id)))

    motions = (
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
    )
    stage2 = []
    for motion in motions:
        stage2.append((motion, _vote_counts(Vote.motion_id == motion.id)))

    return render_template(
        'public_results.html', meeting=meeting, stage1=stage1, stage2=stage2
    )
