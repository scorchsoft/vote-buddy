from flask import render_template, url_for
from flask_mail import Message

from ..extensions import mail
from ..models import Member, Meeting
from flask import current_app


def send_vote_invite(member: Member, token: str, meeting: Meeting) -> None:
    """Send voting link to a member using Flask-Mail."""
    link = url_for('voting.ballot_token', token=token, _external=True)
    msg = Message(
        subject=f"Your voting link for {meeting.title}",
        recipients=[member.email],
    )
    msg.body = render_template('email/invite.txt', member=member, meeting=meeting, link=link)
    msg.html = render_template('email/invite.html', member=member, meeting=meeting, link=link, unsubscribe_url='#')
    mail.send(msg)


def send_stage2_invite(member: Member, token: str, meeting: Meeting) -> None:
    """Email Stage 2 voting link to a member."""
    link = url_for('voting.ballot_token', token=token, _external=True)
    msg = Message(
        subject=f"Stage 2 voting open for {meeting.title}",
        recipients=[member.email],
    )
    msg.body = render_template(
        'email/stage2_invite.txt', member=member, meeting=meeting, link=link
    )
    msg.html = render_template(
        'email/stage2_invite.html',
        member=member,
        meeting=meeting,
        link=link,
        unsubscribe_url='#',
    )
    mail.send(msg)

def send_runoff_invite(member: Member, token: str, meeting: Meeting) -> None:
    """Email run-off voting link after Stage 1."""
    link = url_for('voting.ballot_token', token=token, _external=True)
    msg = Message(
        subject=f"Run-off vote for {meeting.title}",
        recipients=[member.email],
    )
    msg.body = render_template(
        'email/runoff_invite.txt', member=member, meeting=meeting, link=link
    )
    msg.html = render_template(
        'email/runoff_invite.html',
        member=member,
        meeting=meeting,
        link=link,
        unsubscribe_url='#',
    )
    mail.send(msg)


def send_stage1_reminder(member: Member, token: str, meeting: Meeting) -> None:
    """Email reminder to cast Stage 1 vote."""
    link = url_for('voting.ballot_token', token=token, _external=True)
    template_base = current_app.config.get('REMINDER_TEMPLATE', 'email/reminder')
    msg = Message(
        subject=f"Reminder: vote in {meeting.title}",
        recipients=[member.email],
    )
    msg.body = render_template(f"{template_base}.txt", member=member, meeting=meeting, link=link)
    msg.html = render_template(
        f"{template_base}.html",
        member=member,
        meeting=meeting,
        link=link,
        unsubscribe_url='#',
    )
    mail.send(msg)
