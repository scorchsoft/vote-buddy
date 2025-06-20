from flask import Blueprint, render_template, abort, jsonify, request, current_app
from .extensions import db, limiter
from .models import (
    Meeting,
    Amendment,
    Motion,
    Vote,
    Member,
    VoteToken,
    Runoff,
    AppSetting,
)
from .services.email import send_vote_invite, send_stage2_invite, send_runoff_invite
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


@bp.route('/public/meetings')
def public_meetings():
    """List meetings for public view."""
    meetings = Meeting.query.order_by(Meeting.title).all()
    member_counts = {
        m.id: Member.query.filter_by(meeting_id=m.id).count() for m in meetings
    }
    return render_template(
        'public_meetings.html', meetings=meetings, member_counts=member_counts
    )


@bp.route('/public/meetings/<int:meeting_id>')
def public_meeting_detail(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    member_count = Member.query.filter_by(meeting_id=meeting.id).count()
    contact_url = AppSetting.get(
        'contact_url', 'https://www.britishpowerlifting.org/contactus'
    )
    return render_template(
        'public_meeting.html',
        meeting=meeting,
        member_count=member_count,
        contact_url=contact_url,
    )


@bp.post('/public/meetings/<int:meeting_id>/resend')
@limiter.limit('5 per hour')
def resend_meeting_link_public(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    email = request.form.get('email', '').strip().lower()
    member_number = request.form.get('member_number', '').strip()
    member = Member.query.filter_by(
        meeting_id=meeting.id, member_number=member_number, email=email
    ).first()
    if member:
        stage = 2 if meeting.status in {'Stage 2', 'Pending Stage 2'} else 1
        token_obj, plain = VoteToken.create(
            member_id=member.id, stage=stage, salt=current_app.config['TOKEN_SALT']
        )
        db.session.commit()
        if stage == 2:
            send_stage2_invite(member, plain, meeting)
        else:
            if Runoff.query.filter_by(meeting_id=meeting.id).count() > 0:
                send_runoff_invite(member, plain, meeting)
            else:
                send_vote_invite(member, plain, meeting)
        message = 'A new voting link has been sent to your email.'
        success = True
    else:
        message = 'We could not find a member with those details.'
        success = False
    contact_url = AppSetting.get(
        'contact_url', 'https://www.britishpowerlifting.org/contactus'
    )
    return render_template(
        'resend_modal_content.html',
        message=message,
        success=success,
        contact_url=contact_url,
    )


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
