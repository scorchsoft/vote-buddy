from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email


class MotionSubmissionForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    title = StringField('Motion Title', validators=[DataRequired()])
    text_md = TextAreaField('Motion Text', validators=[DataRequired()])
    submit = SubmitField('Submit Motion')


class AmendmentSubmissionForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    text_md = TextAreaField('Amendment Text', validators=[DataRequired()])
    submit = SubmitField('Submit Amendment')
