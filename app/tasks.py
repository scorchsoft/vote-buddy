from datetime import datetime, timedelta
from flask import current_app
from .utils import config_or_setting

from .extensions import scheduler, db
from .models import (
    Meeting,
    Member,
    VoteToken,
    AppSetting,
    AmendmentObjection,
    Amendment,
)
import math
from .services.email import (
    send_stage1_reminder,
    send_stage2_reminder,
    send_board_notice,
    send_amendment_reinstated,
    send_submission_invite,
    auto_send_enabled,
)


def register_jobs():
    scheduler.add_job('stage1_reminders', send_stage1_reminders, trigger='interval', hours=1)
    scheduler.add_job('stage2_reminders', send_stage2_reminders, trigger='interval', hours=1)
    scheduler.add_job('token_cleanup', cleanup_vote_tokens, trigger='cron', hour=0)
    scheduler.add_job('objection_check', check_objection_deadlines, trigger='cron', hour='*')
    scheduler.add_job('submission_invites', send_submission_invites, trigger='cron', hour='*')


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
        if not auto_send_enabled(meeting, 'stage1_reminder'):
            continue
        members = (
            Member.query.join(
                VoteToken,
                db.and_(
                    VoteToken.member_id == Member.id,
                    VoteToken.stage == 1,
                    VoteToken.used_at.is_(None),
                ),
            )
            .filter(Member.meeting_id == meeting.id)
            .distinct()
            .all()
        )
        for member in members:
            _, plain = VoteToken.create(
                member_id=member.id,
                stage=1,
                salt=current_app.config["TOKEN_SALT"],
            )
            send_stage1_reminder(member, plain, meeting)
        if members:
            meeting.stage1_reminder_sent_at = now
            db.session.commit()


def send_stage2_reminders():
    """Check meetings nearing Stage 2 close and email reminders."""
    if AppSetting.get("manual_email_mode") == "1":
        return
    now = datetime.utcnow()
    soon = now + timedelta(
        hours=config_or_setting('STAGE2_REMINDER_HOURS_BEFORE_CLOSE', 6, parser=int)
    )
    meetings = Meeting.query.filter(
        Meeting.closes_at_stage2.isnot(None),
        Meeting.closes_at_stage2 <= soon,
        Meeting.closes_at_stage2 >= now,
    ).all()
    for meeting in meetings:
        last = getattr(meeting, 'stage2_reminder_sent_at', None)
        cooldown = timedelta(
            hours=config_or_setting('STAGE2_REMINDER_COOLDOWN_HOURS', 24, parser=int)
        )
        if last and now - last < cooldown:
            continue
        if not auto_send_enabled(meeting, 'stage2_reminder'):
            continue
        members = (
            Member.query.join(
                VoteToken,
                db.and_(
                    VoteToken.member_id == Member.id,
                    VoteToken.stage == 2,
                    VoteToken.used_at.is_(None),
                ),
            )
            .filter(Member.meeting_id == meeting.id)
            .distinct()
            .all()
        )
        for member in members:
            _, plain = VoteToken.create(
                member_id=member.id,
                stage=2,
                salt=current_app.config["TOKEN_SALT"],
            )
            send_stage2_reminder(member, plain, meeting)
        if members:
            meeting.stage2_reminder_sent_at = now
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


def check_objection_deadlines() -> None:
    now = datetime.utcnow()
    objs_first = AmendmentObjection.query.filter(
        AmendmentObjection.deadline_first.isnot(None),
        AmendmentObjection.deadline_first <= now,
        AmendmentObjection.deadline_final.is_(None),
    ).all()
    for obj in objs_first:
        count = (
            AmendmentObjection.query.filter_by(amendment_id=obj.amendment_id)
            .filter(AmendmentObjection.confirmed_at.isnot(None))
            .count()
        )
        if count >= 10:
            amendment = db.session.get(Amendment, obj.amendment_id)
            meeting = db.session.get(Meeting, amendment.meeting_id)
            send_board_notice(amendment, meeting)
            deadline = obj.deadline_first + timedelta(days=5)
            AmendmentObjection.query.filter_by(amendment_id=obj.amendment_id).update(
                {"deadline_final": deadline}, synchronize_session=False
            )
            db.session.commit()

    objs_final = AmendmentObjection.query.filter(
        AmendmentObjection.deadline_final.isnot(None),
        AmendmentObjection.deadline_final <= now,
    ).all()
    for obj in objs_final:
        amendment = db.session.get(Amendment, obj.amendment_id)
        meeting = db.session.get(Meeting, amendment.meeting_id)
        count = (
            AmendmentObjection.query.filter_by(amendment_id=obj.amendment_id)
            .filter(AmendmentObjection.confirmed_at.isnot(None))
            .count()
        )
        total = Member.query.filter_by(meeting_id=meeting.id).count()
        threshold = max(25, math.ceil(total * 0.05))
        if count >= threshold:
            amendment.status = None
            send_amendment_reinstated(amendment, meeting)
        AmendmentObjection.query.filter_by(amendment_id=obj.amendment_id).update(
            {"deadline_final": None}, synchronize_session=False
        )
        db.session.commit()


def send_submission_invites() -> None:
    """Send motion submission invites when the window opens."""
    if AppSetting.get("manual_email_mode") == "1":
        return
    now = datetime.utcnow()
    meetings = Meeting.query.filter(
        Meeting.motions_opens_at.isnot(None),
        Meeting.motions_opens_at <= now,
        Meeting.submission_invites_sent_at.is_(None),
    ).all()
    for meeting in meetings:
        if not auto_send_enabled(meeting, "submission_invite"):
            continue
        members = Member.query.filter_by(meeting_id=meeting.id).all()
        for member in members:
            send_submission_invite(member, meeting)
        meeting.submission_invites_sent_at = now
        db.session.commit()
