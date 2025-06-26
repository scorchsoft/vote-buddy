import click
from flask.cli import with_appcontext
from datetime import datetime, timedelta
from flask import current_app
import random
from .extensions import db
from .models import (
    User,
    Role,
    Meeting,
    Member,
    VoteToken,
    Motion,
    Amendment,
    Comment,
    Vote,
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

    meetings = []
    for idx in range(3):
        fake.unique.clear()
        status = "Stage 1" if idx == 0 else "Stage 2" if idx == 1 else "Completed"
        meeting = Meeting(
            title=f"Demo Meeting {idx + 1} {now.year}-{fake.random_int(min=100, max=999)}",
            type="AGM",
            notice_date=now - timedelta(days=14),
            ballot_mode="two-stage",
            quorum=15,
            public_results=True,
            comments_enabled=True,
            status=status,
        )

        if idx == 0:
            meeting.opens_at_stage1 = now - timedelta(days=1)
            meeting.closes_at_stage1 = now + timedelta(days=1)
            meeting.opens_at_stage2 = now + timedelta(days=2)
            meeting.closes_at_stage2 = now + timedelta(days=5)
        elif idx == 1:
            meeting.opens_at_stage1 = now - timedelta(days=5)
            meeting.closes_at_stage1 = now - timedelta(days=3)
            meeting.opens_at_stage2 = now - timedelta(days=1)
            meeting.closes_at_stage2 = now + timedelta(days=2)
        else:
            meeting.opens_at_stage1 = now - timedelta(days=15)
            meeting.closes_at_stage1 = now - timedelta(days=13)
            meeting.opens_at_stage2 = now - timedelta(days=10)
            meeting.closes_at_stage2 = now - timedelta(days=8)
            meeting.stage1_closed_at = meeting.closes_at_stage1
            meeting.stage2_locked = True

        db.session.add(meeting)
        db.session.commit()
        meetings.append(meeting)

        members: list[Member] = []
        for i in range(20):
            member = Member(
                meeting_id=meeting.id,
                name=fake.name(),
                email=f"{fake.unique.user_name()}@example.invalid",
                member_number=str(1000 + i + idx * 100),
                is_test=True,
            )
            db.session.add(member)
            db.session.flush()
            t1, _ = VoteToken.create(
                member_id=member.id,
                stage=1,
                salt=current_app.config["TOKEN_SALT"],
            )
            t2, _ = VoteToken.create(
                member_id=member.id,
                stage=2,
                salt=current_app.config["TOKEN_SALT"],
            )
            t1.is_test = True
            t2.is_test = True
            members.append(member)

        motions: list[Motion] = []
        for i in range(3):
            motion = Motion(
                meeting_id=meeting.id,
                title=fake.sentence(nb_words=6)[:-1],
                text_md=fake.paragraph(nb_sentences=3),
                category="motion",
                threshold="normal",
                ordering=i + 1,
            )
            db.session.add(motion)
            motions.append(motion)
        db.session.flush()

        amendments: list[Amendment] = []
        for motion in motions:
            for j in range(2):
                amend = Amendment(
                    meeting_id=meeting.id,
                    motion_id=motion.id,
                    text_md=fake.sentence(nb_words=10),
                    order=j + 1,
                    status="draft",
                    proposer_id=members[(j * 2) % len(members)].id,
                    seconder_id=members[(j * 2 + 1) % len(members)].id,
                    seconded_method="email",
                    seconded_at=now,
                )
                db.session.add(amend)
                amendments.append(amend)

        db.session.flush()

        for motion in motions:
            for _ in range(2):
                comment = Comment(
                    meeting_id=meeting.id,
                    motion_id=motion.id,
                    member_id=random.choice(members).id,
                    text_md=fake.sentence(nb_words=8),
                    created_at=now,
                )
                db.session.add(comment)
        for amend in amendments:
            for _ in range(2):
                comment = Comment(
                    meeting_id=meeting.id,
                    amendment_id=amend.id,
                    member_id=random.choice(members).id,
                    text_md=fake.sentence(nb_words=8),
                    created_at=now,
                )
                db.session.add(comment)

        choices = ["for", "against", "abstain"]
        for member in members:
            for amend in amendments:
                Vote.record(
                    member_id=member.id,
                    amendment_id=amend.id,
                    choice=random.choice(choices),
                    salt=current_app.config["VOTE_SALT"],
                    stage=1,
                    is_test=True,
                )
            for motion in motions:
                Vote.record(
                    member_id=member.id,
                    motion_id=motion.id,
                    choice=random.choice(choices),
                    salt=current_app.config["VOTE_SALT"],
                    stage=2,
                    is_test=True,
                )
            t1 = VoteToken.query.filter_by(member_id=member.id, stage=1).first()
            t2 = VoteToken.query.filter_by(member_id=member.id, stage=2).first()
            if t1:
                t1.used_at = now
            if t2:
                t2.used_at = now

    db.session.commit()
    click.echo('Fake data generated.')


__all__ = ['create_admin', 'generate_fake_data']
