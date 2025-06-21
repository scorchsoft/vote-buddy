import os
import sys
from types import SimpleNamespace
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.extensions import db
from app.models import Meeting, Permission, Role, User
from app.meetings import routes as meetings


def _make_user():
    perm = Permission(name="manage_meetings")
    role = Role(permissions=[perm])
    user = User(role=role)
    user.email = "admin@example.com"
    user.is_active = True
    return user


def test_extend_stage_updates_reason():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()
        meeting = Meeting(title="AGM")
        db.session.add(meeting)
        db.session.commit()

        now = datetime.utcnow()
        data = {
            "opens_at": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
            "closes_at": (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M"),
            "reason": "Storm delay",
        }
        form = SimpleNamespace(
            validate_on_submit=lambda: True,
            opens_at=SimpleNamespace(data=datetime.strptime(data["opens_at"], "%Y-%m-%dT%H:%M")),
            closes_at=SimpleNamespace(data=datetime.strptime(data["closes_at"], "%Y-%m-%dT%H:%M")),
            reason=SimpleNamespace(data=data["reason"]),
        )
        with app.test_request_context(f"/meetings/{meeting.id}/extend/2", method="POST"):
            user = _make_user()
            with patch("flask_login.utils._get_user", return_value=user):
                with patch("app.meetings.routes.ExtendStageForm", return_value=form):
                    meetings.extend_stage(meeting.id, 2)
        assert meeting.extension_reason == "Storm delay"
        assert meeting.opens_at_stage2 is not None
