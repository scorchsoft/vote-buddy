from datetime import datetime
from flask import Blueprint, render_template, abort, request, current_app

from ..extensions import db
from ..models import VoteToken, Member, Amendment, Meeting, Vote
from .forms import VoteForm

bp = Blueprint('voting', __name__, url_prefix='/vote')


@bp.route('/')
def ballot_home():
    return render_template('voting/home.html')


@bp.route('/<token>', methods=['GET', 'POST'])
def ballot_token(token: str):
    """Verify token, display amendment and record vote."""
    vote_token = VoteToken.query.filter_by(token=token).first_or_404()
    member = Member.query.get_or_404(vote_token.member_id)
    meeting = Meeting.query.get_or_404(member.meeting_id)

    if vote_token.used_at and not meeting.revoting_allowed:
        return render_template(
            'voting/token_error.html',
            message='This voting link has already been used.',
        ), 400

    amendment = (
        Amendment.query.filter_by(meeting_id=meeting.id)
        .order_by(Amendment.order)
        .first()
    )

    form = VoteForm()
    if form.validate_on_submit():
        Vote.record(
            member_id=member.id,
            amendment_id=amendment.id if amendment else None,
            choice=form.choice.data,
            salt=current_app.config['VOTE_SALT'],
            motion=False,
        )
        vote_token.used_at = datetime.utcnow()
        db.session.commit()
        return render_template('voting/confirmation.html', choice=form.choice.data)

    return render_template(
        'voting/ballot.html',
        form=form,
        amendment=amendment,
        meeting=meeting,
    )
