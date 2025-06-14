from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateTimeLocalField, BooleanField, TextAreaField, SubmitField
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
    status = StringField('Status')
    chair_notes_md = TextAreaField('Chair Notes')
    submit = SubmitField('Save')
