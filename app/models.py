from datetime import datetime, timedelta
import hashlib
import math
from flask import current_app
from flask_login import UserMixin
from uuid6 import uuid7
from .extensions import db, bcrypt

# association table linking roles to permissions
roles_permissions = db.Table(
    "roles_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column(
        "permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True
    ),
)


class Role(db.Model):
    """User role with attached permissions."""

    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    permissions = db.relationship(
        "Permission", secondary=roles_permissions, back_populates="roles"
    )


class Permission(db.Model):
    """System permission that can be assigned to roles."""

    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    roles = db.relationship(
        "Role", secondary=roles_permissions, back_populates="permissions"
    )


class AppSetting(db.Model):
    """Key-value application setting stored in the database."""

    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255))
    group = db.Column(db.String(50))

    @classmethod
    def get(cls, key: str, default: str | None = None) -> str | None:
        try:
            setting = cls.query.filter_by(key=key).first()
        except Exception:
            return default
        return setting.value if setting else default

    @classmethod
    def set(cls, key: str, value: str) -> "AppSetting":
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key)
            db.session.add(setting)
        setting.value = value
        db.session.commit()
        return setting

    @classmethod
    def delete(cls, key: str) -> None:
        setting = cls.query.filter_by(key=key).first()
        if setting:
            db.session.delete(setting)
            db.session.commit()


class Meeting(db.Model):
    __tablename__ = "meetings"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(10))
    notice_date = db.Column(db.DateTime)
    opens_at_stage1 = db.Column(db.DateTime)
    closes_at_stage1 = db.Column(db.DateTime)
    opens_at_stage2 = db.Column(db.DateTime)
    closes_at_stage2 = db.Column(db.DateTime)
    runoff_opens_at = db.Column(db.DateTime)
    runoff_closes_at = db.Column(db.DateTime)
    motions_opens_at = db.Column(db.DateTime)
    motions_closes_at = db.Column(db.DateTime)
    amendments_opens_at = db.Column(db.DateTime)
    amendments_closes_at = db.Column(db.DateTime)
    ballot_mode = db.Column(db.String(20))
    revoting_allowed = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50))
    chair_notes_md = db.Column(db.Text)
    quorum = db.Column(db.Integer, default=0)
    stage1_locked = db.Column(db.Boolean, default=False)
    stage1_closed_at = db.Column(db.DateTime)
    stage2_locked = db.Column(db.Boolean, default=False)
    stage1_reminder_sent_at = db.Column(db.DateTime)
    stage2_reminder_sent_at = db.Column(db.DateTime)
    public_results = db.Column(db.Boolean, default=False)
    early_public_results = db.Column(db.Boolean, default=False)
    comments_enabled = db.Column(db.Boolean, default=False)
    extension_reason = db.Column(db.Text)
    results_doc_published = db.Column(db.Boolean, default=False)
    results_doc_intro_md = db.Column(db.Text)
    stage1_manual_votes = db.Column(db.Integer, default=0)
    stage2_manual_for = db.Column(db.Integer, default=0)
    stage2_manual_against = db.Column(db.Integer, default=0)
    stage2_manual_abstain = db.Column(db.Integer, default=0)
    submission_invites_sent_at = db.Column(db.DateTime)

    files = db.relationship(
        "MeetingFile", backref="meeting", cascade="all, delete-orphan"
    )

    def stage1_votes_count(self) -> int:
        """Return number of verified Stage-1 votes."""
        if self.ballot_mode == "in-person":
            return self.stage1_manual_votes or 0
        return (
            VoteToken.query.join(Member, VoteToken.member_id == Member.id)
            .filter(
                VoteToken.stage == 1,
                VoteToken.used_at.isnot(None),
                VoteToken.is_test.is_(False),
                Member.meeting_id == self.id,
            )
            .count()
        )

    def hours_until_next_reminder(self, now: datetime | None = None) -> int:
        """Return hours until the next reminder email should be sent."""
        if not self.closes_at_stage1:
            return 0
        now = now or datetime.utcnow()
        from .utils import config_or_setting

        hours_before = config_or_setting("REMINDER_HOURS_BEFORE_CLOSE", 6, parser=int)
        next_due = self.closes_at_stage1 - timedelta(hours=hours_before)
        if self.stage1_reminder_sent_at:
            cooldown = config_or_setting("REMINDER_COOLDOWN_HOURS", 24, parser=int)
            next_due = self.stage1_reminder_sent_at + timedelta(hours=cooldown)
        diff = (next_due - now).total_seconds() / 3600
        return max(0, math.ceil(diff))

    def quorum_percentage(self) -> float:
        """Return Stage-1 turnout as a percentage of quorum."""
        if not self.quorum:
            return 0.0
        return (self.stage1_votes_count() / self.quorum) * 100

    def stage1_time_remaining(self) -> str:
        """Return human-friendly countdown until Stage-1 closes."""
        if not self.closes_at_stage1:
            return "N/A"
        delta = self.closes_at_stage1 - datetime.utcnow()
        if delta.total_seconds() <= 0:
            return "Closed"
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes = rem // 60
        return f"{hours}h {minutes}m"

    def stage2_time_remaining(self) -> str:
        """Return human-friendly countdown until Stage-2 closes."""
        if not self.closes_at_stage2:
            return "N/A"
        delta = self.closes_at_stage2 - datetime.utcnow()
        if delta.total_seconds() <= 0:
            return "Closed"
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes = rem // 60
        return f"{hours}h {minutes}m"

    def stage1_progress_percent(self) -> int:
        """Return percentage of Stage-1 voting period elapsed."""
        if not self.opens_at_stage1 or not self.closes_at_stage1:
            return 0
        total = (self.closes_at_stage1 - self.opens_at_stage1).total_seconds()
        if total <= 0:
            return 0
        elapsed = (datetime.utcnow() - self.opens_at_stage1).total_seconds()
        percent = max(0.0, min(100.0, (elapsed / total) * 100))
        return int(percent)

    def stage2_progress_percent(self) -> int:
        """Return percentage of Stage-2 voting period elapsed."""
        if not self.opens_at_stage2 or not self.closes_at_stage2:
            return 0
        total = (self.closes_at_stage2 - self.opens_at_stage2).total_seconds()
        if total <= 0:
            return 0
        elapsed = (datetime.utcnow() - self.opens_at_stage2).total_seconds()
        percent = max(0.0, min(100.0, (elapsed / total) * 100))
        return int(percent)


class Member(db.Model):
    __tablename__ = "members"
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    member_number = db.Column(db.String(50))
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    proxy_for = db.Column(db.String(255))
    email_opt_out = db.Column(db.Boolean, default=False)
    can_comment = db.Column(db.Boolean, default=True)
    is_test = db.Column(db.Boolean, default=False)
    comments = db.relationship("Comment", backref="member")


class Motion(db.Model):
    __tablename__ = "motions"
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    title = db.Column(db.String(255))
    text_md = db.Column(db.Text)
    final_text_md = db.Column(db.Text)
    category = db.Column(db.String(20))
    threshold = db.Column(db.String(20))
    ordering = db.Column(db.Integer)
    status = db.Column(db.String(50))
    is_published = db.Column(db.Boolean, default=False)
    withdrawn = db.Column(db.Boolean, default=False)
    modified_at = db.Column(db.DateTime)
    withdrawal_requested_at = db.Column(db.DateTime)
    chair_approved_at = db.Column(db.DateTime)
    board_approved_at = db.Column(db.DateTime)
    options = db.relationship("MotionOption", backref="motion")


class MotionOption(db.Model):
    __tablename__ = "motion_options"
    id = db.Column(db.Integer, primary_key=True)
    motion_id = db.Column(db.Integer, db.ForeignKey("motions.id"), index=True)
    text = db.Column(db.String(255))


class VoteToken(db.Model):
    __tablename__ = "vote_tokens"
    token = db.Column(db.String(64), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), index=True)
    proxy_holder_id = db.Column(db.Integer, db.ForeignKey("members.id"))
    stage = db.Column(db.Integer, index=True)
    used_at = db.Column(db.DateTime)
    is_test = db.Column(db.Boolean, default=False)

    @staticmethod
    def _hash(token: str, salt: str) -> str:
        return hashlib.sha256(f"{token}{salt}".encode()).hexdigest()

    @classmethod
    def create(
        cls,
        member_id: int,
        stage: int,
        salt: str,
        *,
        proxy_holder_id: int | None = None,
    ) -> tuple["VoteToken", str]:
        """Create token, store hash and return plain value."""
        plain = str(uuid7())
        hashed = cls._hash(plain, salt)
        obj = cls(
            token=hashed,
            member_id=member_id,
            stage=stage,
            proxy_holder_id=proxy_holder_id,
        )
        db.session.add(obj)
        return obj, plain

    @classmethod
    def verify(cls, token: str, salt: str) -> "VoteToken | None":
        hashed = cls._hash(token, salt)
        return cls.query.filter_by(token=hashed).first()


class SubmissionToken(db.Model):
    """Token used for motion and amendment submissions."""

    __tablename__ = "submission_tokens"

    token = db.Column(db.String(64), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), index=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    used_at = db.Column(db.DateTime)

    @staticmethod
    def _hash(token: str, salt: str) -> str:
        return hashlib.sha256(f"{token}{salt}".encode()).hexdigest()

    @classmethod
    def create(cls, member_id: int, meeting_id: int, salt: str) -> tuple["SubmissionToken", str]:
        """Create token, store hash and return plain value."""
        plain = str(uuid7())
        hashed = cls._hash(plain, salt)
        obj = cls(token=hashed, member_id=member_id, meeting_id=meeting_id)
        db.session.add(obj)
        return obj, plain

    @classmethod
    def verify(cls, token: str, salt: str) -> "SubmissionToken | None":
        hashed = cls._hash(token, salt)
        return cls.query.filter_by(token=hashed).first()


class UnsubscribeToken(db.Model):
    __tablename__ = "unsubscribe_tokens"
    token = db.Column(db.String(36), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ApiToken(db.Model):
    """Token for authenticating API requests."""

    __tablename__ = "api_tokens"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def _hash(token: str, salt: str) -> str:
        return hashlib.sha256(f"{token}{salt}".encode()).hexdigest()

    @classmethod
    def create(cls, name: str, salt: str) -> tuple["ApiToken", str]:
        """Create token, store hash and return plain value."""
        plain = str(uuid7())
        hashed = cls._hash(plain, salt)
        obj = cls(name=name, token_hash=hashed)
        db.session.add(obj)
        return obj, plain

    @classmethod
    def verify(cls, token: str, salt: str) -> "ApiToken | None":
        hashed = cls._hash(token, salt)
        return cls.query.filter_by(token_hash=hashed).first()


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    token = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime)

    user = db.relationship("User")


class Amendment(db.Model):
    __tablename__ = "amendments"
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    motion_id = db.Column(db.Integer, db.ForeignKey("motions.id"), index=True)
    text_md = db.Column(db.Text)
    order = db.Column(db.Integer)
    status = db.Column(db.String(50))
    is_published = db.Column(db.Boolean, default=False)
    reason = db.Column(db.Text)
    proposer_id = db.Column(db.Integer, db.ForeignKey("members.id"))
    seconder_id = db.Column(db.Integer, db.ForeignKey("members.id"))
    board_seconded = db.Column(db.Boolean, default=False)
    tie_break_method = db.Column(db.String(20))
    seconded_at = db.Column(db.DateTime)
    seconded_method = db.Column(db.String(50))

    proposer = db.relationship("Member", foreign_keys=[proposer_id])
    seconder = db.relationship("Member", foreign_keys=[seconder_id])

    combined_from = db.relationship(
        "Amendment",
        secondary="amendment_merges",
        primaryjoin="Amendment.id==AmendmentMerge.combined_id",
        secondaryjoin="Amendment.id==AmendmentMerge.source_id",
        backref="combined_into",
    )


class Vote(db.Model):
    __tablename__ = "votes"
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), index=True)
    amendment_id = db.Column(db.Integer, db.ForeignKey("amendments.id"), nullable=True, index=True)
    motion_id = db.Column(db.Integer, db.ForeignKey("motions.id"), nullable=True, index=True)
    choice = db.Column(db.String(10))
    hash = db.Column(db.String(128))
    is_test = db.Column(db.Boolean, default=False)

    @classmethod
    def record(
        cls,
        member_id: int,
        choice: str,
        salt: str,
        amendment_id: int | None = None,
        motion_id: int | None = None,
        stage: int | None = None,
        is_test: bool = False,
    ) -> "Vote":
        """Create a vote with hashed choice."""
        target_id = amendment_id if amendment_id is not None else motion_id or ""
        stage_val = stage if stage is not None else ""
        digest_source = f"{member_id}{target_id}{stage_val}{choice}{salt}"
        digest = hashlib.sha256(digest_source.encode()).hexdigest()
        vote = cls(
            member_id=member_id,
            amendment_id=amendment_id,
            motion_id=motion_id,
            choice=choice,
            hash=digest,
            is_test=is_test,
        )
        db.session.add(vote)
        db.session.commit()
        return vote


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password_hash = db.Column(db.String(255))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    role = db.relationship("Role")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def has_permission(self, permission_name: str) -> bool:
        if not self.role:
            return False
        return any(p.name == permission_name for p in self.role.permissions)


class Runoff(db.Model):
    __tablename__ = "runoffs"
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    amendment_a_id = db.Column(db.Integer, db.ForeignKey("amendments.id"))
    amendment_b_id = db.Column(db.Integer, db.ForeignKey("amendments.id"))
    tie_break_method = db.Column(db.String(20), nullable=True)


class AmendmentConflict(db.Model):
    __tablename__ = "amendment_conflicts"
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    amendment_a_id = db.Column(db.Integer, db.ForeignKey("amendments.id"))
    amendment_b_id = db.Column(db.Integer, db.ForeignKey("amendments.id"))

    amendment_a = db.relationship("Amendment", foreign_keys=[amendment_a_id])
    amendment_b = db.relationship("Amendment", foreign_keys=[amendment_b_id])


class AmendmentMerge(db.Model):
    __tablename__ = "amendment_merges"
    id = db.Column(db.Integer, primary_key=True)
    combined_id = db.Column(db.Integer, db.ForeignKey("amendments.id"))
    source_id = db.Column(db.Integer, db.ForeignKey("amendments.id"))


class AmendmentObjection(db.Model):
    __tablename__ = "amendment_objections"
    id = db.Column(db.Integer, primary_key=True)
    amendment_id = db.Column(db.Integer, db.ForeignKey("amendments.id"))
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"))
    email = db.Column(db.String(255))
    token = db.Column(db.String(36))
    confirmed_at = db.Column(db.DateTime)
    deadline_first = db.Column(db.DateTime)
    deadline_final = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def confirmed(self) -> bool:
        return self.confirmed_at is not None


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    motion_id = db.Column(db.Integer, db.ForeignKey("motions.id"), nullable=True, index=True)
    amendment_id = db.Column(
        db.Integer, db.ForeignKey("amendments.id"), nullable=True, index=True
    )
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), index=True)
    text_md = db.Column(db.Text)
    hidden = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime)
    revisions = db.relationship("CommentRevision", backref="comment")

    def can_edit(self, meeting: "Meeting", minutes: int = 15) -> bool:
        deadline = self.created_at + timedelta(minutes=minutes)
        for closing in [meeting.closes_at_stage1, meeting.closes_at_stage2]:
            if closing and closing < deadline:
                deadline = closing
        return datetime.utcnow() < deadline


class CommentRevision(db.Model):
    __tablename__ = "comment_revisions"
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey("comments.id"))
    text_md = db.Column(db.Text)
    edited_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmailLog(db.Model):
    __tablename__ = "email_logs"
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), index=True)
    type = db.Column(db.String(50))
    is_test = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)


class AdminLog(db.Model):
    """Record an administrative action performed by a user."""

    __tablename__ = "admin_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    user = db.relationship("User")
    action = db.Column(db.String(50))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MotionSubmission(db.Model):
    __tablename__ = "motion_submissions"
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), index=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    seconder_id = db.Column(db.Integer, db.ForeignKey("members.id"))
    title = db.Column(db.String(255))
    text_md = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AmendmentSubmission(db.Model):
    __tablename__ = "amendment_submissions"
    id = db.Column(db.Integer, primary_key=True)
    motion_id = db.Column(db.Integer, db.ForeignKey("motions.id"), index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), index=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    seconder_id = db.Column(db.Integer, db.ForeignKey("members.id"))
    text_md = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MeetingFile(db.Model):
    __tablename__ = "meeting_files"
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey("meetings.id"), index=True)
    filename = db.Column(db.String(255))
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
