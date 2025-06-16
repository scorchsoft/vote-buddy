from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import (
    StringField,
    SelectField,
    DateTimeLocalField,
    BooleanField,
    IntegerField,
    TextAreaField,
    SubmitField,
)
from wtforms.validators import DataRequired


class MeetingForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    type = SelectField("Type", choices=[("AGM", "AGM"), ("EGM", "EGM")])
    opens_at_stage1 = DateTimeLocalField("Stage 1 Opens", format="%Y-%m-%dT%H:%M")
    closes_at_stage1 = DateTimeLocalField("Stage 1 Closes", format="%Y-%m-%dT%H:%M")
    opens_at_stage2 = DateTimeLocalField("Stage 2 Opens", format="%Y-%m-%dT%H:%M")
    closes_at_stage2 = DateTimeLocalField("Stage 2 Closes", format="%Y-%m-%dT%H:%M")
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
    quorum = IntegerField("Quorum")
    status = StringField("Status")
    chair_notes_md = TextAreaField("Chair Notes")
    submit = SubmitField("Save")

    def validate(self, extra_validators=None):
        """Cross-field validations for meeting timelines."""
        is_valid = super().validate(extra_validators=extra_validators)

        now = datetime.utcnow()

        # check Stage 1 opens in the future
        if self.opens_at_stage1.data and self.opens_at_stage1.data <= now:
            self.opens_at_stage1.errors.append(
                'Stage 1 must open in the future.'
            )
            is_valid = False

        # check Stage 2 opens after Stage 1 opens
        if (
            self.opens_at_stage1.data
            and self.opens_at_stage2.data
            and self.opens_at_stage2.data <= self.opens_at_stage1.data
        ):
            self.opens_at_stage2.errors.append(
                'Stage 2 must open after Stage 1 opens.'
            )
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


class AmendmentForm(FlaskForm):
    text_md = TextAreaField("Amendment Text", validators=[DataRequired()])
    proposer_id = SelectField("Proposer", coerce=int, validators=[DataRequired()])
    seconder_id = SelectField("Seconder", coerce=int, validators=[DataRequired()])
    seconded_method = StringField("Seconded Via")
    submit = SubmitField("Save")


class ConflictForm(FlaskForm):
    amendment_a_id = SelectField("Amendment A", coerce=int)
    amendment_b_id = SelectField("Amendment B", coerce=int)
    submit = SubmitField("Add Conflict")


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
    options = TextAreaField("Options (one per line)")
    allow_clerical = BooleanField(
        "Allow clerical corrections",
        default=True,
    )
    allow_move = BooleanField(
        "Allow Articles/Bylaws placement",
        default=True,
    )
    submit = SubmitField("Save")
