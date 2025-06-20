import click
from flask.cli import with_appcontext
from datetime import datetime, timedelta
from flask import current_app
from .extensions import db
from .models import (
    User,
    Role,
    Meeting,
    Member,
    VoteToken,
    Motion,
    Amendment,
)
from faker import Faker

@click.command('create-admin')
@with_appcontext
def create_admin() -> None:
    """Create an admin user interactively."""
    email = click.prompt('Email')
    password = click.prompt('Password', hide_input=True)
    role_name = click.prompt('Role')

    role = Role.query.filter_by(name=role_name).first()
    if role is None:
        click.echo(f"Role '{role_name}' not found.")
        return
    if User.query.filter_by(email=email).first():
        click.echo(f"User {email} already exists.")
        return

    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Created user {email} with role {role.name}.")

@click.command('generate-fake-data')
@with_appcontext
def generate_fake_data() -> None:
    """Insert demo records for local testing."""
    fake = Faker()
    now = datetime.utcnow()

    coord_role = Role.query.filter_by(name='meeting_coordinator').first()
    ro_role = Role.query.filter_by(name='returning_officer').first()

    if coord_role and not User.query.filter_by(email='demo_coordinator@example.com').first():
        user = User(email='demo_coordinator@example.com', role=coord_role)
        user.set_password('password')
        db.session.add(user)

    if ro_role and not User.query.filter_by(email='demo_ro@example.com').first():
        ro = User(email='demo_ro@example.com', role=ro_role)
        ro.set_password('password')
        db.session.add(ro)

    db.session.commit()

    meeting = Meeting(
        title=f"Demo Meeting {now.year}-{fake.random_int(min=100, max=999)}",
        type='AGM',
        notice_date=now - timedelta(days=7),
        opens_at_stage1=now,
        closes_at_stage1=now + timedelta(days=2),
        opens_at_stage2=now + timedelta(days=3),
        closes_at_stage2=now + timedelta(days=5),
        ballot_mode='two-stage',
        status='Upcoming',
        quorum=15,
        public_results=True,
        comments_enabled=True,
    )
    db.session.add(meeting)
    db.session.commit()

    members = []
    for _ in range(30):
        member = Member(
            meeting_id=meeting.id,
            name=fake.name(),
            email=fake.unique.email(),
        )
        db.session.add(member)
        db.session.flush()
        VoteToken.create(member_id=member.id, stage=1, salt=current_app.config['TOKEN_SALT'])
        members.append(member)

    motions = []
    for i in range(3):
        motion = Motion(
            meeting_id=meeting.id,
            title=fake.sentence(nb_words=6)[:-1],
            text_md=fake.paragraph(nb_sentences=3),
            category='motion',
            threshold='normal',
            ordering=i + 1,
        )
        db.session.add(motion)
        motions.append(motion)
    db.session.flush()

    for motion in motions:
        for j in range(2):
            amend = Amendment(
                meeting_id=meeting.id,
                motion_id=motion.id,
                text_md=fake.sentence(nb_words=10),
                order=j + 1,
                status='draft',
                proposer_id=members[(j * 2) % len(members)].id,
                seconder_id=members[(j * 2 + 1) % len(members)].id,
                seconded_method='email',
                seconded_at=now,
            )
            db.session.add(amend)

    db.session.commit()
    click.echo('Fake data generated.')


__all__ = ['create_admin', 'generate_fake_data']
