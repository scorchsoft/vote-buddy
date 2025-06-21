from datetime import datetime, timedelta
from flask import current_app
from .utils import config_or_setting

from .extensions import scheduler, db
from .models import Meeting, Member, VoteToken, AppSetting
from .services.email import send_stage1_reminder


def register_jobs():
    scheduler.add_job('stage1_reminders', send_stage1_reminders, trigger='interval', hours=1)
    scheduler.add_job('token_cleanup', cleanup_vote_tokens, trigger='cron', hour=0)


def send_stage1_reminders():
    """Check meetings nearing Stage 1 close and email reminders."""
    if AppSetting.get("manual_email_mode") == "1":
        return
    now = datetime.utcnow()
    soon = now + timedelta(
        hours=config_or_setting('REMINDER_HOURS_BEFORE_CLOSE', 6, parser=int)
    )
    meetings = Meeting.query.filter(
        Meeting.closes_at_stage1.isnot(None),
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


def cleanup_vote_tokens() -> None:
    """Delete used or expired vote tokens."""
    now = datetime.utcnow()
    tokens = (
        VoteToken.query.join(Member, VoteToken.member_id == Member.id)
        .join(Meeting, Member.meeting_id == Meeting.id)
        .filter(
            db.or_(
                VoteToken.used_at.isnot(None),
                db.and_(
                    VoteToken.stage == 1,
                    db.or_(
                        db.and_(
                            Meeting.runoff_closes_at.isnot(None),
                            Meeting.runoff_closes_at < now,
                        ),
                        db.and_(
                            Meeting.runoff_closes_at.is_(None),
                            Meeting.closes_at_stage1.isnot(None),
                            Meeting.closes_at_stage1 < now,
                        ),
                    ),
                ),
                db.and_(
                    VoteToken.stage == 2,
                    Meeting.closes_at_stage2.isnot(None),
                    Meeting.closes_at_stage2 < now,
                ),
            )
        )
        .all()
    )
    for token in tokens:
        db.session.delete(token)
    db.session.commit()
