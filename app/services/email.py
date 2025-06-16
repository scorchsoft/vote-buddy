from flask import render_template, url_for
from flask_mail import Message
from ..utils import config_or_setting, generate_stage_ics

from ..extensions import mail, db
from ..models import Member, Meeting, UnsubscribeToken, AppSetting
from flask import current_app
from uuid6 import uuid7


def _unsubscribe_url(member: Member) -> str:
    token = UnsubscribeToken.query.filter_by(member_id=member.id).first()
    if not token:
        token = UnsubscribeToken(token=str(uuid7()), member_id=member.id)
        db.session.add(token)
        db.session.commit()
    return url_for('notifications.unsubscribe', token=token.token, _external=True)


def _sender() -> str | None:
    return AppSetting.get('from_email', current_app.config.get('MAIL_DEFAULT_SENDER'))


def send_vote_invite(member: Member, token: str, meeting: Meeting) -> None:
    """Send voting link to a member using Flask-Mail."""
    if member.email_opt_out:
        return
    link = url_for('voting.ballot_token', token=token, _external=True)
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=f"Your voting link for {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template('email/invite.txt', member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe)
    msg.html = render_template('email/invite.html', member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe)
    ics = generate_stage_ics(meeting, 1)
    msg.attach('stage1.ics', 'text/calendar', ics)
    mail.send(msg)


def send_stage2_invite(member: Member, token: str, meeting: Meeting) -> None:
    """Email Stage 2 voting link to a member."""
    if member.email_opt_out:
        return
    link = url_for('voting.ballot_token', token=token, _external=True)
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=f"Stage 2 voting open for {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template(
        'email/stage2_invite.txt', member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe
    )
    msg.html = render_template(
        'email/stage2_invite.html',
        member=member,
        meeting=meeting,
        link=link,
        unsubscribe_url=unsubscribe,
    )
    ics = generate_stage_ics(meeting, 2)
    msg.attach('stage2.ics', 'text/calendar', ics)
    mail.send(msg)

def send_runoff_invite(member: Member, token: str, meeting: Meeting) -> None:
    """Email run-off voting link after Stage 1."""
    if member.email_opt_out:
        return
    link = url_for('voting.runoff_ballot', token=token, _external=True)
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=f"Run-off vote for {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template(
        'email/runoff_invite.txt', member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe
    )
    msg.html = render_template(
        'email/runoff_invite.html',
        member=member,
        meeting=meeting,
        link=link,
        unsubscribe_url=unsubscribe,
    )
    mail.send(msg)


def send_stage1_reminder(member: Member, token: str, meeting: Meeting) -> None:
    """Email reminder to cast Stage 1 vote."""
    if member.email_opt_out:
        return
    link = url_for('voting.ballot_token', token=token, _external=True)
    template_base = config_or_setting('REMINDER_TEMPLATE', 'email/reminder')
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=f"Reminder: vote in {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template(f"{template_base}.txt", member=member, meeting=meeting, link=link, unsubscribe_url=unsubscribe)
    msg.html = render_template(
        f"{template_base}.html",
        member=member,
        meeting=meeting,
        link=link,
        unsubscribe_url=unsubscribe,
    )
    mail.send(msg)


def send_vote_receipt(member: Member, meeting: Meeting, hashes: list[str]) -> None:
    """Email a receipt containing vote hashes."""
    unsubscribe = _unsubscribe_url(member)
    msg = Message(
        subject=f"Your vote receipt for {meeting.title}",
        recipients=[member.email],
        sender=_sender(),
    )
    msg.body = render_template(
        "email/receipt.txt",
        member=member,
        meeting=meeting,
        hashes=hashes,
        unsubscribe_url=unsubscribe,
    )
    msg.html = render_template(
        "email/receipt.html",
        member=member,
        meeting=meeting,
        hashes=hashes,
        unsubscribe_url=unsubscribe,
    )
    mail.send(msg)
