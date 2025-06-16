from __future__ import annotations

from io import StringIO
import csv
from flask import Blueprint, render_template, redirect, url_for, Response, jsonify
from flask_login import login_required

from ..extensions import db
from ..models import Meeting, Amendment, Motion, Vote, VoteToken, Member
from ..permissions import permission_required

bp = Blueprint('ro', __name__, url_prefix='/ro')


def _stage1_vote_count(meeting: Meeting) -> int:
    return (
        VoteToken.query.join(Member, VoteToken.member_id == Member.id)
        .filter(
            VoteToken.stage == 1,
            VoteToken.used_at != None,
            Member.meeting_id == meeting.id,
        )
        .count()
    )


@bp.route('/')
@login_required
@permission_required('manage_meetings')
def dashboard():
    data: list[tuple[Meeting, int]] = []
    for m in Meeting.query.all():
        data.append((m, _stage1_vote_count(m)))
    return render_template('ro/dashboard.html', meetings=data)


@bp.route('/<int:meeting_id>/lock/<int:stage>', methods=['POST'])
@login_required
@permission_required('manage_meetings')
def lock_stage(meeting_id: int, stage: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    if stage == 1:
        meeting.stage1_locked = True
    else:
        meeting.stage2_locked = True
    db.session.commit()
    return redirect(url_for('ro.dashboard'))


@bp.route('/<int:meeting_id>/unlock/<int:stage>', methods=['POST'])
@login_required
@permission_required('manage_meetings')
def unlock_stage(meeting_id: int, stage: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    if stage == 1:
        meeting.stage1_locked = False
    else:
        meeting.stage2_locked = False
    db.session.commit()
    return redirect(url_for('ro.dashboard'))


@bp.route('/<int:meeting_id>/tallies.csv')
@login_required
@permission_required('manage_meetings')
def download_tallies(meeting_id: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['type', 'id', 'text', 'for', 'against', 'abstain'])
    for amend in Amendment.query.filter_by(meeting_id=meeting.id).all():
        writer.writerow([
            'amendment',
            amend.id,
            amend.text_md[:40],
            Vote.query.filter_by(amendment_id=amend.id, choice='for').count(),
            Vote.query.filter_by(amendment_id=amend.id, choice='against').count(),
            Vote.query.filter_by(amendment_id=amend.id, choice='abstain').count(),
        ])
    for motion in Motion.query.filter_by(meeting_id=meeting.id).all():
        writer.writerow([
            'motion',
            motion.id,
            motion.title,
            Vote.query.filter_by(motion_id=motion.id, choice='for').count(),
            Vote.query.filter_by(motion_id=motion.id, choice='against').count(),
            Vote.query.filter_by(motion_id=motion.id, choice='abstain').count(),
        ])
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = (
        f'attachment; filename=tallies_meeting_{meeting.id}.csv'
    )
    return response


@bp.route('/<int:meeting_id>/tallies.json')
@login_required
@permission_required('manage_meetings')
def download_tallies_json(meeting_id: int):
    """Return tallies for amendments and motions as JSON."""
    meeting = Meeting.query.get_or_404(meeting_id)
    rows: list[dict[str, int | str]] = []
    for amend in Amendment.query.filter_by(meeting_id=meeting.id).all():
        rows.append(
            {
                'type': 'amendment',
                'id': amend.id,
                'text': amend.text_md[:40],
                'for': Vote.query.filter_by(amendment_id=amend.id, choice='for').count(),
                'against': Vote.query.filter_by(amendment_id=amend.id, choice='against').count(),
                'abstain': Vote.query.filter_by(amendment_id=amend.id, choice='abstain').count(),
            }
        )
    for motion in Motion.query.filter_by(meeting_id=meeting.id).all():
        rows.append(
            {
                'type': 'motion',
                'id': motion.id,
                'text': motion.title,
                'for': Vote.query.filter_by(motion_id=motion.id, choice='for').count(),
                'against': Vote.query.filter_by(motion_id=motion.id, choice='against').count(),
                'abstain': Vote.query.filter_by(motion_id=motion.id, choice='abstain').count(),
            }
        )
    return jsonify({'meeting_id': meeting.id, 'tallies': rows})


@bp.route('/<int:meeting_id>/stage2_tallies.csv')
@login_required
@permission_required('manage_meetings')
def download_stage2_tallies(meeting_id: int):
    """Return a CSV of Stage 2 motion tallies including outcome."""
    meeting = Meeting.query.get_or_404(meeting_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'title', 'for', 'against', 'abstain', 'outcome'])
    motions = (
        Motion.query.filter_by(meeting_id=meeting.id)
        .order_by(Motion.ordering)
        .all()
    )
    for motion in motions:
        writer.writerow([
            motion.id,
            motion.title,
            Vote.query.filter_by(motion_id=motion.id, choice='for').count(),
            Vote.query.filter_by(motion_id=motion.id, choice='against').count(),
            Vote.query.filter_by(motion_id=motion.id, choice='abstain').count(),
            (motion.status or '').capitalize(),
        ])
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = (
        f'attachment; filename=stage2_tallies_meeting_{meeting.id}.csv'
    )
    return response


@bp.route('/<int:meeting_id>/audit_log.csv')
@login_required
@permission_required('manage_meetings')
def download_audit_log(meeting_id: int):
    """Return a CSV audit log of all votes for a meeting."""
    meeting = Meeting.query.get_or_404(meeting_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['member_id', 'amendment_id', 'motion_id', 'choice', 'hash'])
    votes = (
        Vote.query.join(Member, Vote.member_id == Member.id)
        .filter(Member.meeting_id == meeting.id)
        .all()
    )
    for v in votes:
        writer.writerow([v.member_id, v.amendment_id, v.motion_id, v.choice, v.hash])
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = (
        f'attachment; filename=audit_log_meeting_{meeting.id}.csv'
    )
    return response
