import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
import hashlib

import pytest
from werkzeug.exceptions import NotFound

from app import create_app
from app.extensions import db
from app.models import (
    Meeting,
    Member,
    VoteToken,
    Amendment,
    Motion,
    MotionOption,
    Vote,
)
from app.voting import routes as voting


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['VOTE_SALT'] = 'salty'
    app.config['WTF_CSRF_ENABLED'] = False
    return app


def test_ballot_token_not_found():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        with app.test_request_context('/vote/bad'):
            with pytest.raises(NotFound):
                voting.ballot_token('bad')


def test_cast_vote_records_hash_and_marks_used():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='Motion text', category='motion', threshold='normal', ordering=1)
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Alice', email='a@example.com')
        db.session.add(member)
        amendment = Amendment(meeting_id=meeting.id, motion_id=motion.id, text_md='Test', order=1)
        db.session.add(amendment)
        db.session.commit()
        token = VoteToken(token='tok123', member_id=member.id, stage=1)
        db.session.add(token)
        db.session.commit()
        member_id = member.id

        with app.test_request_context('/vote/tok123', method='POST', data={f'amend_{amendment.id}': 'for'}):
            voting.ballot_token('tok123')

        vote = Vote.query.first()
        token_db = VoteToken.query.filter_by(token='tok123').first()
        expected = hashlib.sha256(f"{member_id}forsalty".encode()).hexdigest()
    assert vote.hash == expected
    assert token_db.used_at is not None


def test_stage2_motion_vote():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.flush()
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='Motion text', category='motion', threshold='normal', ordering=1)
        db.session.add(motion)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Alice', email='a@example.com')
        db.session.add(member)
        db.session.commit()
        token = VoteToken(token='tok2', member_id=member.id, stage=2)
        db.session.add(token)
        db.session.commit()
        member_id = member.id

        with app.test_request_context('/vote/tok2', method='POST', data={f'motion_{motion.id}': 'against'}):
            voting.ballot_token('tok2')

        vote = Vote.query.first()
        expected = hashlib.sha256(f"{member_id}againstsalty".encode()).hexdigest()
        assert vote.motion_id == motion.id
        assert vote.hash == expected
        assert token.used_at is not None
