from datetime import datetime, timedelta
from flask import current_app
from .utils import config_or_setting

from .extensions import scheduler, db
from .models import Meeting, Member, VoteToken
from .services.email import send_stage1_reminder


def register_jobs():
    scheduler.add_job('stage1_reminders', send_stage1_reminders, trigger='interval', hours=1)


def send_stage1_reminders():
    """Check meetings nearing Stage 1 close and email reminders."""
    now = datetime.utcnow()
    soon = now + timedelta(
        hours=config_or_setting('REMINDER_HOURS_BEFORE_CLOSE', 6, parser=int)
    )
    meetings = Meeting.query.filter(
        Meeting.closes_at_stage1 != None,
        Meeting.closes_at_stage1 <= soon,
        Meeting.closes_at_stage1 >= now,
    ).all()
    for meeting in meetings:
        if meeting.stage1_votes_count() >= meeting.quorum:
            continue
        last = getattr(meeting, 'stage1_reminder_sent_at', None)
        cooldown = timedelta(
            hours=config_or_setting('REMINDER_COOLDOWN_HOURS', 24, parser=int)
        )
        if last and now - last < cooldown:
            continue
        members = Member.query.filter_by(meeting_id=meeting.id).all()
        for member in members:
            _, plain = VoteToken.create(
                member_id=member.id,
                stage=1,
                salt=current_app.config["TOKEN_SALT"],
            )
            send_stage1_reminder(member, plain, meeting)
        meeting.stage1_reminder_sent_at = now
        db.session.commit()
