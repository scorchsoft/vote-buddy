from datetime import datetime
from flask_login import UserMixin
from .extensions import db, bcrypt

class Meeting(db.Model):
    __tablename__ = 'meetings'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50))

class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'))
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    proxy_for = db.Column(db.String(255))
    weight = db.Column(db.Integer, default=1)

class VoteToken(db.Model):
    __tablename__ = 'vote_tokens'
    token = db.Column(db.String(36), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'))
    stage = db.Column(db.Integer)
    used_at = db.Column(db.DateTime)

class Amendment(db.Model):
    __tablename__ = 'amendments'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'))
    text_md = db.Column(db.Text)
    order = db.Column(db.Integer)
    status = db.Column(db.String(50))

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'))
    amendment_id = db.Column(db.Integer, db.ForeignKey('amendments.id'), nullable=True)
    motion = db.Column(db.Boolean, default=False)
    choice = db.Column(db.String(10))
    hash = db.Column(db.String(128))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = (
            bcrypt.generate_password_hash(password).decode("utf-8")
        )

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

class Runoff(db.Model):
    __tablename__ = 'runoffs'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'))
    amendment_a_id = db.Column(db.Integer, db.ForeignKey('amendments.id'))
    amendment_b_id = db.Column(db.Integer, db.ForeignKey('amendments.id'))
