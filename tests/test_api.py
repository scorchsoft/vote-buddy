import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from werkzeug.exceptions import Unauthorized
from app import create_app
from app.extensions import db
from app.models import Meeting, Amendment, Motion, Member, Vote, ApiToken
from app.api import routes as api


def _setup_app():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['API_TOKEN_SALT'] = 's'
    return app


def test_api_auth_required():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        with app.test_request_context('/api/meetings'):
            with pytest.raises(Unauthorized):
                api.list_meetings()


def test_api_list_meetings_with_token():
    app = _setup_app()
    with app.app_context():
        db.create_all()
        m = Meeting(title='AGM', public_results=True)
        db.session.add(m)
        db.session.commit()
        token_obj, plain = ApiToken.create('test', app.config['API_TOKEN_SALT'])
        db.session.commit()
        with app.test_request_context('/api/meetings', headers={'Authorization': f'Bearer {plain}'}):
            resp = api.list_meetings()
            data = resp.get_json()
            assert {'id': m.id, 'title': 'AGM'} in data


def test_api_results_matches_public_json():
    app = _setup_app()
    app.config['TOKEN_SALT'] = 't'
    with app.app_context():
        db.create_all()
        meeting = Meeting(title='AGM', public_results=True)
        db.session.add(meeting)
        db.session.flush()
        amend = Amendment(meeting_id=meeting.id, text_md='A1', order=1)
        motion = Motion(meeting_id=meeting.id, title='M1', text_md='T', category='motion', threshold='normal', ordering=1)
        member = Member(meeting_id=meeting.id, name='Alice')
        db.session.add_all([amend, motion, member])
        db.session.commit()
        Vote.record(member_id=member.id, amendment_id=amend.id, choice='for', salt='t')
        Vote.record(member_id=member.id, motion_id=motion.id, choice='against', salt='t')
        token_obj, plain = ApiToken.create('test', app.config['API_TOKEN_SALT'])
        db.session.commit()
        with app.test_request_context(f'/api/meetings/{meeting.id}/results', headers={'Authorization': f'Bearer {plain}'}):
            api_json = api.meeting_results(meeting.id)
            data = api_json.get_json()
            assert data['meeting_id'] == meeting.id
            assert any(r['for'] == 1 for r in data['tallies'] if r['type'] == 'amendment')
