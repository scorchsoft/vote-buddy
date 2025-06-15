from datetime import datetime
import hashlib
from flask_login import UserMixin
from .extensions import db, bcrypt

# association table linking roles to permissions
roles_permissions = db.Table(
    'roles_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True),
)


class Role(db.Model):
    """User role with attached permissions."""

    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    permissions = db.relationship('Permission', secondary=roles_permissions, back_populates='roles')


class Permission(db.Model):
    """System permission that can be assigned to roles."""

    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    roles = db.relationship('Role', secondary=roles_permissions, back_populates='permissions')

class Meeting(db.Model):
    __tablename__ = 'meetings'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(10))
    opens_at_stage1 = db.Column(db.DateTime)
    closes_at_stage1 = db.Column(db.DateTime)
    opens_at_stage2 = db.Column(db.DateTime)
    closes_at_stage2 = db.Column(db.DateTime)
    ballot_mode = db.Column(db.String(20))
    revoting_allowed = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50))
    chair_notes_md = db.Column(db.Text)
    quorum = db.Column(db.Integer, default=0)
    stage1_locked = db.Column(db.Boolean, default=False)
    stage2_locked = db.Column(db.Boolean, default=False)
    stage1_reminder_sent_at = db.Column(db.DateTime)
    public_results = db.Column(db.Boolean, default=False)

    def stage1_votes_count(self) -> int:
        """Return number of verified Stage-1 votes."""
        return (
            VoteToken.query.join(Member, VoteToken.member_id == Member.id)
            .filter(
                VoteToken.stage == 1,
                VoteToken.used_at != None,
                Member.meeting_id == self.id,
            )
            .count()
        )

class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'))
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    proxy_for = db.Column(db.String(255))
    weight = db.Column(db.Integer, default=1)


class Motion(db.Model):
    __tablename__ = 'motions'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'))
    title = db.Column(db.String(255))
    text_md = db.Column(db.Text)
    final_text_md = db.Column(db.Text)
    category = db.Column(db.String(20))
    threshold = db.Column(db.String(20))
    ordering = db.Column(db.Integer)
    options = db.relationship('MotionOption', backref='motion')


class MotionOption(db.Model):
    __tablename__ = 'motion_options'
    id = db.Column(db.Integer, primary_key=True)
    motion_id = db.Column(db.Integer, db.ForeignKey('motions.id'))
    text = db.Column(db.String(255))

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
    motion_id = db.Column(db.Integer, db.ForeignKey('motions.id'))
    text_md = db.Column(db.Text)
    order = db.Column(db.Integer)
    status = db.Column(db.String(50))
    proposer_id = db.Column(db.Integer, db.ForeignKey('members.id'))
    seconder_id = db.Column(db.Integer, db.ForeignKey('members.id'))

    proposer = db.relationship('Member', foreign_keys=[proposer_id])
    seconder = db.relationship('Member', foreign_keys=[seconder_id])

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'))
    amendment_id = db.Column(db.Integer, db.ForeignKey('amendments.id'), nullable=True)
    motion_id = db.Column(db.Integer, db.ForeignKey('motions.id'), nullable=True)
    choice = db.Column(db.String(10))
    hash = db.Column(db.String(128))

    @classmethod
    def record(
        cls,
        member_id: int,
        choice: str,
        salt: str,
        amendment_id: int | None = None,
        motion_id: int | None = None,
    ) -> "Vote":
        """Create a vote with hashed choice."""
        digest = hashlib.sha256(
            f"{member_id}{choice}{salt}".encode()
        ).hexdigest()
        vote = cls(
            member_id=member_id,
            amendment_id=amendment_id,
            motion_id=motion_id,
            choice=choice,
            hash=digest,
        )
        db.session.add(vote)
        db.session.commit()
        return vote

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password_hash = db.Column(db.String(255))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    role = db.relationship('Role')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = (
            bcrypt.generate_password_hash(password).decode("utf-8")
        )

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def has_permission(self, permission_name: str) -> bool:
        if not self.role:
            return False
        return any(p.name == permission_name for p in self.role.permissions)

class Runoff(db.Model):
    __tablename__ = 'runoffs'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'))
    amendment_a_id = db.Column(db.Integer, db.ForeignKey('amendments.id'))
    amendment_b_id = db.Column(db.Integer, db.ForeignKey('amendments.id'))


class AmendmentConflict(db.Model):
    __tablename__ = 'amendment_conflicts'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'))
    amendment_a_id = db.Column(db.Integer, db.ForeignKey('amendments.id'))
    amendment_b_id = db.Column(db.Integer, db.ForeignKey('amendments.id'))

