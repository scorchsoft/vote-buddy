from datetime import datetime, timedelta
from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (
    StringField,
    SelectField,
    DateTimeLocalField,
    BooleanField,
    IntegerField,
    TextAreaField,
    SubmitField,
    HiddenField,
)
from wtforms.validators import DataRequired, Optional, Email
from wtforms import SelectMultipleField


class MeetingForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    type = SelectField("Type", choices=[("AGM", "AGM"), ("EGM", "EGM")])
    notice_date = DateTimeLocalField(
        "Notice Date",
        format="%Y-%m-%dT%H:%M",
        description="Must be at least 14 days before Stage 1 opens.",
    )
    opens_at_stage1 = DateTimeLocalField(
        "Stage 1 Opens",
        format="%Y-%m-%dT%H:%M",
        description="At least 14 days after notice date.",
    )
    closes_at_stage1 = DateTimeLocalField(
        "Stage 1 Closes",
        format="%Y-%m-%dT%H:%M",
        description="Must remain open for at least 7 days.",
    )
    motions_opens_at = DateTimeLocalField(
        "Motions Open",
        format="%Y-%m-%dT%H:%M",
        description="When members may start submitting motions.",
    )
    motions_closes_at = DateTimeLocalField(
        "Motions Close",
        format="%Y-%m-%dT%H:%M",
        description="Deadline for new motion submissions.",
    )
    amendments_opens_at = DateTimeLocalField(
        "Amendments Open",
        format="%Y-%m-%dT%H:%M",
        description="When members may start submitting amendments.",
    )
    amendments_closes_at = DateTimeLocalField(
        "Amendments Close",
        format="%Y-%m-%dT%H:%M",
        description="Deadline for amendment submissions.",
    )
    opens_at_stage2 = DateTimeLocalField(
        "Stage 2 Opens",
        format="%Y-%m-%dT%H:%M",
        description="At least 1 day after Stage 1 closes.",
    )
    closes_at_stage2 = DateTimeLocalField(
        "AGM Date",
        format="%Y-%m-%dT%H:%M",
        description="Final voting deadline; at least 5 days after Stage 2 opens.",
    )
    ballot_mode = SelectField(
        "Ballot Mode",
        choices=[
            ("two-stage", "Two-stage"),
            ("combined", "Combined"),
            ("in-person", "In-person/Hybrid"),
        ],
    )
    revoting_allowed = BooleanField("Revoting Allowed")
    public_results = BooleanField("Public Results")
    early_public_results = BooleanField("Early Public Results")
    results_doc_published = BooleanField("Publish Final Results Doc")
    results_doc_intro_md = TextAreaField(
        "Results Doc Intro",
        description="Intro paragraph added to the certified results document.",
        render_kw={"data-markdown-editor": "1"},
    )
    comments_enabled = BooleanField("Enable Comments")
    quorum = IntegerField("Quorum")
    status = SelectField(
        "Status",
        choices=[
            ("Draft", "Draft"),
            ("Stage 1", "Stage 1"),
            ("Pending Stage 2", "Pending Stage 2"),
            ("Stage 2", "Stage 2"),
            ("Quorum not met", "Quorum not met"),
            ("Completed", "Completed"),
        ],
    )
    chair_notes_md = TextAreaField(
        "Chair Notes",
        description="Private notes for meeting admins; not shown to members.",
    )
    summary_md = TextAreaField(
        "Summary Paragraph",
        description="Shown on public motion pages as an overview of the meeting.",
        render_kw={"data-markdown-editor": "1"},
    )
    notice_md = TextAreaField(
        "Meeting Notice",
        validators=[Optional()],
        render_kw={"data-markdown-editor": "1"},
        description="Markdown included in Stage 1 invite emails.",
    )
    submit = SubmitField("Save")

    def validate(self, extra_validators=None):
        """Cross-field validations for meeting timelines."""
        is_valid = super().validate(extra_validators=extra_validators)

        now = datetime.utcnow()

        # check Stage 1 opens in the future
        if self.opens_at_stage1.data and self.opens_at_stage1.data <= now:
            self.opens_at_stage1.errors.append("Stage 1 must open in the future.")
            is_valid = False

        # check Stage 1 opens at least NOTICE_PERIOD_DAYS after notice date
        if self.opens_at_stage1.data and self.notice_date.data:
            notice_days = current_app.config.get('NOTICE_PERIOD_DAYS', 14)
            if self.opens_at_stage1.data - self.notice_date.data < timedelta(days=notice_days):
                self.opens_at_stage1.errors.append(
                    f'Stage 1 must open at least {notice_days} days after notice.'
                )
                is_valid = False

        # check Stage 2 opens after Stage 1 opens
        if (
            self.opens_at_stage1.data
            and self.opens_at_stage2.data
            and self.opens_at_stage2.data <= self.opens_at_stage1.data
        ):
            self.opens_at_stage2.errors.append("Stage 2 must open after Stage 1 opens.")
            is_valid = False

        # check Stage 1 duration >= 7 days
        if self.opens_at_stage1.data and self.closes_at_stage1.data:
            if self.closes_at_stage1.data - self.opens_at_stage1.data < timedelta(
                days=7
            ):
                self.closes_at_stage1.errors.append(
                    "Stage 1 must remain open for at least 7 days."
                )
                is_valid = False

        # motion submission window
        if self.motions_opens_at.data and self.motions_closes_at.data:
            if self.motions_closes_at.data <= self.motions_opens_at.data:
                self.motions_closes_at.errors.append(
                    "Motion close must be after it opens."
                )
                is_valid = False

        if self.amendments_opens_at.data and self.amendments_closes_at.data:
            if self.amendments_closes_at.data <= self.amendments_opens_at.data:
                self.amendments_closes_at.errors.append(
                    "Amendment close must be after it opens."
                )
                is_valid = False

        # check Stage 2 duration >= 5 days
        if self.opens_at_stage2.data and self.closes_at_stage2.data:
            if self.closes_at_stage2.data - self.opens_at_stage2.data < timedelta(
                days=5
            ):
                self.closes_at_stage2.errors.append(
                    "Stage 2 must remain open for at least 5 days."
                )
                is_valid = False

        # check Stage 2 opens >= 1 day after Stage 1 closes
        if self.closes_at_stage1.data and self.opens_at_stage2.data:
            if self.opens_at_stage2.data - self.closes_at_stage1.data < timedelta(
                days=1
            ):
                self.opens_at_stage2.errors.append(
                    "Stage 2 must open at least 1 day after Stage 1 closes."
                )
                is_valid = False

        return is_valid


class MemberImportForm(FlaskForm):
    """Upload CSV file of members."""

    csv_file = FileField("CSV File", validators=[FileRequired()])
    submit = SubmitField("Upload")


class MeetingFileForm(FlaskForm):
    file = FileField(
        "PDF File", validators=[FileRequired(), FileAllowed(["pdf"], "PDF only!")]
    )
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description")
    submit = SubmitField("Upload")


class AmendmentForm(FlaskForm):
    text_md = TextAreaField("Amendment Text", validators=[DataRequired()])
    proposer_id = SelectField("Proposer", coerce=int, validators=[DataRequired()])
    seconder_id = SelectField("Seconder", coerce=int, validators=[Optional()])
    board_seconded = BooleanField("Seconded by Board/Chair")
    seconded_method = StringField("Seconded Via", validators=[Optional()])
    submit = SubmitField("Save")


class ConflictForm(FlaskForm):
    amendment_a_id = SelectField("Amendment A", coerce=int)
    amendment_b_id = SelectField("Amendment B", coerce=int)
    submit = SubmitField("Add Conflict")


class ObjectionForm(FlaskForm):
    member_id = HiddenField("Member", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Submit objection")


class ManualEmailForm(FlaskForm):
    email_type = SelectField(
        "Email Type",
        choices=[
            ("stage1_invite", "Stage 1 Invite"),
            ("stage1_reminder", "Stage 1 Reminder"),
            ("runoff_invite", "Run-off Invite"),
            ("stage2_invite", "Stage 2 Invite"),
            ("submission_invite", "Motion Submission Invite"),
            ("review_invite", "Motion Review Invite"),
        ],
        validators=[DataRequired()],
    )
    member_ids = SelectMultipleField("Members", coerce=int)
    send_to_all = BooleanField("Send to all members")
    test_mode = BooleanField("Test Mode")
    submit = SubmitField("Send")


class MotionForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    text_md = TextAreaField("Motion Text", validators=[DataRequired()])
    category = SelectField(
        "Category",
        choices=[
            ("motion", "Motion"),
            ("directors_report", "Director's Report"),
            ("multiple_choice", "Multiple Choice"),
        ],
    )
    threshold = SelectField(
        "Voting Threshold",
        choices=[("normal", "Normal"), ("special", "Special")],
    )
    options = TextAreaField(
        "Options (one per line)",
        description="For multiple choice motions only. 'Abstain' is always added automatically.",
    )
    allow_clerical = BooleanField(
        "Allow clerical corrections",
        default=True,
    )
    allow_move = BooleanField(
        "Allow Articles/Bylaws placement",
        default=True,
    )
    submit = SubmitField("Save")


class ExtendStageForm(FlaskForm):
    """Admin form to extend a stage voting window."""

    opens_at = DateTimeLocalField("New Opens At", format="%Y-%m-%dT%H:%M")
    closes_at = DateTimeLocalField("New Closes At", format="%Y-%m-%dT%H:%M")
    reason = TextAreaField("Reason", validators=[DataRequired()])
    submit = SubmitField("Extend")


class MotionChangeRequestForm(FlaskForm):
    """Form for motion withdrawal or major edit requests."""

    text_md = TextAreaField("Revised Motion Text", validators=[Optional()])
    withdraw = BooleanField("Withdraw Motion")
    submit = SubmitField("Submit Request")

class Stage1TallyForm(FlaskForm):
    votes_cast = IntegerField("Votes Cast", validators=[DataRequired()])
    submit = SubmitField("Save")


class Stage2TallyForm(FlaskForm):
    for_votes = IntegerField("For", validators=[DataRequired()])
    against_votes = IntegerField("Against", validators=[DataRequired()])
    abstain_votes = IntegerField("Abstain", validators=[DataRequired()])
    submit = SubmitField("Save")
