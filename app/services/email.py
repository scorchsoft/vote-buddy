from flask import render_template, url_for, current_app
from flask_mail import Message
from ..utils import config_or_setting, generate_stage_ics, carried_amendment_summary

from ..extensions import mail, db
from ..models import Member, Meeting, UnsubscribeToken, AppSetting, EmailLog
from uuid6 import uuid7


def _log_email(member: Member, meeting: Meeting, kind: str, test_mode: bool) -> None:
    entry = EmailLog(
        meeting_id=meeting.id if meeting else None,
        member_id=member.id if member else None,
        type=kind,
        is_test=test_mode,
    )
    db.session.add(entry)
    db.session.commit()


def _unsubscribe_url(member: Member) -> str:
    token = UnsubscribeToken.query.filter_by(member_id=member.id).first()
    if not token:
        token = UnsubscribeToken(token=str(uuid7()), member_id=member.id)
        db.session.add(token)
        db.session.commit()
    return url_for('notifications.unsubscribe', token=token.token, _external=True)


def _sender() -> str | None:
    return AppSetting.get('from_email', current_app.config.get('MAIL_DEFAULT_SENDER'))


def send_vote_invite(member: Member, token: str, meeting: Meeting, *, test_mode: bool = False) -> None:
    """Send voting link to a member using Flask-Mail."""
    if member.email_opt_out:
        return
    link = url_for('voting.ballot_token', token=token, _external=True)
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=("[TEST] " if test_mode else "") + f"Your voting link for {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template('email/invite.txt', member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe, test_mode=test_mode)
    msg.html = render_template('email/invite.html', member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe, test_mode=test_mode)
    try:
        ics = generate_stage_ics(meeting, 1)
    except Exception:
        ics = None
    if ics:
        msg.attach('stage1.ics', 'text/calendar', ics)
    mail.send(msg)
    _log_email(member, meeting, 'stage1_invite', test_mode)


def send_stage2_invite(member: Member, token: str, meeting: Meeting, *, test_mode: bool = False) -> None:
    """Email Stage 2 voting link to a member."""
    if member.email_opt_out:
        return
    link = url_for('voting.ballot_token', token=token, _external=True)
    unsubscribe = _unsubscribe_url(member)
    summary = carried_amendment_summary(meeting)
    results_link = None if summary else url_for('main.public_results', meeting_id=meeting.id, _external=True)
    msg = Message(
        subject=("[TEST] " if test_mode else "") + f"Stage 2 voting open for {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template(
        'email/stage2_invite.txt',
        member=member,
        meeting=meeting,
        link=link,
        unsubscribe_url=unsubscribe,
        summary=summary,
        results_link=results_link,
        test_mode=test_mode,
    )
    msg.html = render_template(
        'email/stage2_invite.html',
        member=member,
        meeting=meeting,
        link=link,
        unsubscribe_url=unsubscribe,
        summary=summary,
        results_link=results_link,
        test_mode=test_mode,
    )
    try:
        ics = generate_stage_ics(meeting, 2)
    except Exception:
        ics = None
    if ics:
        msg.attach('stage2.ics', 'text/calendar', ics)
    mail.send(msg)
    _log_email(member, meeting, 'stage2_invite', test_mode)

def send_runoff_invite(member: Member, token: str, meeting: Meeting, *, test_mode: bool = False) -> None:
    """Email run-off voting link after Stage 1."""
    if member.email_opt_out:
        return
    link = url_for('voting.runoff_ballot', token=token, _external=True)
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=("[TEST] " if test_mode else "") + f"Run-off vote for {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template('email/runoff_invite.txt', member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe, test_mode=test_mode)
    msg.html = render_template('email/runoff_invite.html', member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe, test_mode=test_mode)
    mail.send(msg)
    _log_email(member, meeting, 'runoff_invite', test_mode)


def send_stage1_reminder(member: Member, token: str, meeting: Meeting, *, test_mode: bool = False) -> None:
    """Email reminder to cast Stage 1 vote."""
    if member.email_opt_out:
        return
    link = url_for('voting.ballot_token', token=token, _external=True)
    template_base = config_or_setting('REMINDER_TEMPLATE', 'email/reminder')
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=("[TEST] " if test_mode else "") + f"Reminder: vote in {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template(f"{template_base}.txt", member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe, test_mode=test_mode)
    msg.html = render_template(
        f"{template_base}.html",
        member=member,
        meeting=meeting,
        link=link,
        unsubscribe_url=unsubscribe,
        test_mode=test_mode,
    )
    mail.send(msg)
    _log_email(member, meeting, 'stage1_reminder', test_mode)


def send_vote_receipt(member: Member, meeting: Meeting, hashes: list[str], *, test_mode: bool = False) -> None:
    """Email a receipt containing vote hashes."""
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=("[TEST] " if test_mode else "") + f"Your vote receipt for {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template(
        "email/receipt.txt",
        member=member,
        meeting=meeting,
        hashes=hashes,
        unsubscribe_url=unsubscribe,
        test_mode=test_mode,
    )
    msg.html = render_template(
        "email/receipt.html",
        member=member,
        meeting=meeting,
        hashes=hashes,
        unsubscribe_url=unsubscribe,
        test_mode=test_mode,
    )
    mail.send(msg)
    _log_email(member, meeting, 'receipt', test_mode)

def send_quorum_failure(member: Member, meeting: Meeting, *, test_mode: bool = False) -> None:
    """Notify a member that Stage 1 failed to reach quorum."""
    if member.email_opt_out:
        return
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=("[TEST] " if test_mode else "") + f"Stage 1 vote void for {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template(
        "email/quorum_failure.txt",
        member=member,
        meeting=meeting,
        unsubscribe_url=unsubscribe,
        test_mode=test_mode,
    )
    msg.html = render_template(
        "email/quorum_failure.html",
        member=member,
        meeting=meeting,
        unsubscribe_url=unsubscribe,
        test_mode=test_mode,
    )
    mail.send(msg)
    _log_email(member, meeting, 'quorum_failure', test_mode)

