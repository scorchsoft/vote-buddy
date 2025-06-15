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
    title = StringField('Title', validators=[DataRequired()])
    type = SelectField('Type', choices=[('AGM', 'AGM'), ('EGM', 'EGM')])
    opens_at_stage1 = DateTimeLocalField('Stage 1 Opens', format='%Y-%m-%dT%H:%M')
    closes_at_stage1 = DateTimeLocalField('Stage 1 Closes', format='%Y-%m-%dT%H:%M')
    opens_at_stage2 = DateTimeLocalField('Stage 2 Opens', format='%Y-%m-%dT%H:%M')
    closes_at_stage2 = DateTimeLocalField('Stage 2 Closes', format='%Y-%m-%dT%H:%M')
    ballot_mode = SelectField('Ballot Mode', choices=[('two-stage', 'Two-stage'), ('combined', 'Combined'), ('in-person', 'In-person/Hybrid')])
    revoting_allowed = BooleanField('Revoting Allowed')
    public_results = BooleanField('Public Results')
    quorum = IntegerField('Quorum')
    status = StringField('Status')
    chair_notes_md = TextAreaField('Chair Notes')
    submit = SubmitField('Save')


class MemberImportForm(FlaskForm):
    """Upload CSV file of members."""

    csv_file = FileField('CSV File', validators=[FileRequired()])
    submit = SubmitField('Upload')


class AmendmentForm(FlaskForm):
    text_md = TextAreaField('Amendment Text', validators=[DataRequired()])
    proposer_id = SelectField('Proposer', coerce=int, validators=[DataRequired()])
    seconder_id = SelectField('Seconder', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Save')


class MotionForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    text_md = TextAreaField('Motion Text', validators=[DataRequired()])
    category = SelectField(
        'Category',
        choices=[
            ('motion', 'Motion'),
            ('directors_report', "Director's Report"),
            ('multiple_choice', 'Multiple Choice'),
        ],
    )
    threshold = SelectField(
        'Voting Threshold',
        choices=[('normal', 'Normal'), ('special', 'Special')],
    )
    options = TextAreaField('Options (one per line)')
    submit = SubmitField('Save')
