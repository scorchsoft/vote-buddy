from flask import Blueprint, render_template, abort, jsonify
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


@bp.route('/results/<int:meeting_id>/charts')
def public_results_charts(meeting_id: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    if not meeting.public_results:
        abort(404)
    return render_template('results_chart.html', meeting=meeting)


@bp.route('/results/<int:meeting_id>/tallies.json')
def public_results_json(meeting_id: int):
    """Return tallies for amendments and motions as JSON."""
    meeting = Meeting.query.get_or_404(meeting_id)
    if not meeting.public_results:
        abort(404)

    tallies: list[dict[str, int | str]] = []
    amendments = (
        Amendment.query.filter_by(meeting_id=meeting.id)
        .order_by(Amendment.order)
        .all()
    )
    for amend in amendments:
        counts = _vote_counts(Vote.amendment_id == amend.id)
        tallies.append(
            {
                "type": "amendment",
                "id": amend.id,
                "text": amend.text_md[:40],
                **counts,
            }
        )

    motions = (
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
    )
    for motion in motions:
        counts = _vote_counts(Vote.motion_id == motion.id)
        tallies.append(
            {
                "type": "motion",
                "id": motion.id,
                "text": motion.title,
                **counts,
            }
        )

    return jsonify({"meeting_id": meeting.id, "tallies": tallies})
