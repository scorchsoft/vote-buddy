from flask import render_template, url_for
from flask_mail import Message

from ..extensions import mail
from ..models import Member, Meeting


def send_vote_invite(member: Member, token: str, meeting: Meeting) -> None:
    """Send voting link to a member using Flask-Mail."""
    link = url_for('voting.ballot_home', token=token, _external=True)
    msg = Message(
        subject=f"Your voting link for {meeting.title}",
        recipients=[member.email],
    )
    msg.body = render_template('email/invite.txt', member=member, meeting=meeting, link=link)
    msg.html = render_template('email/invite.html', member=member, meeting=meeting, link=link, unsubscribe_url='#')
    mail.send(msg)


def send_stage2_invite(member: Member, token: str, meeting: Meeting) -> None:
    """Email Stage 2 voting link to a member."""
    link = url_for('voting.ballot_home', token=token, _external=True)
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
