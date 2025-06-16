import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from werkzeug.exceptions import NotFound
from app import create_app
from app.extensions import db
from app.models import Meeting, Amendment, Motion, Member, Vote
from app import routes as main


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['VOTE_SALT'] = 's'
    return app


def test_public_results_respects_flag_and_renders():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM')
        db.session.add(meeting)
        db.session.commit()

        with app.test_request_context(f'/results/{meeting.id}'):
            with pytest.raises(NotFound):
                main.public_results(meeting.id)

        meeting.public_results = True
        db.session.add(meeting)
        db.session.flush()
        member = Member(meeting_id=meeting.id, name='Alice')
        db.session.add(member)
        db.session.flush()
        amend = Amendment(meeting_id=meeting.id, motion_id=None, text_md='A1', order=1)
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='T', category='motion', threshold='normal', ordering=1)
        db.session.add_all([amend, motion])
        db.session.commit()
        Vote.record(member_id=member.id, amendment_id=amend.id, choice='for', salt='s')
        Vote.record(member_id=member.id, motion_id=motion.id, choice='against', salt='s')

        with app.test_request_context(f'/results/{meeting.id}'):
            html = main.public_results(meeting.id)
            assert 'Stage 1' in html
            assert 'Stage 2' in html


def test_public_results_json_counts():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM', public_results=True)
        db.session.add(meeting)
        db.session.flush()
        amend = Amendment(meeting_id=meeting.id, motion_id=None, text_md='A1', order=1)
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='T', category='motion', threshold='normal', ordering=1)
        db.session.add_all([amend, motion])
        member = Member(meeting_id=meeting.id, name='Alice')
        db.session.add(member)
        db.session.commit()
        Vote.record(member_id=member.id, amendment_id=amend.id, choice='for', salt='s')
        Vote.record(member_id=member.id, motion_id=motion.id, choice='against', salt='s')

        with app.test_request_context(f'/results/{meeting.id}/tallies.json'):
            resp = main.public_results_json(meeting.id)
            data = resp.get_json()
            assert data['meeting_id'] == meeting.id
            a_row = next(r for r in data['tallies'] if r['type'] == 'amendment')
            m_row = next(r for r in data['tallies'] if r['type'] == 'motion')
            assert a_row['for'] == 1
            assert m_row['against'] == 1
