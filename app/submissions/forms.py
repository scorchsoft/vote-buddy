from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    SelectField,
    StringField,
    TextAreaField,
    SubmitField,
)
from wtforms.validators import DataRequired, Email


class MotionSubmissionForm(FlaskForm):
    name = StringField("Your Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    title = StringField("Motion Title", validators=[DataRequired()])
    text_md = TextAreaField(
        "Motion Text", validators=[DataRequired()], render_kw={"data-markdown-editor": "1"}
    )
    seconder_member_number = StringField(
        "Seconder Member #", validators=[DataRequired()]
    )
    seconder_name = StringField("Seconder Name", validators=[DataRequired()])
    allow_clerical = BooleanField(
        "Allow clerical corrections", default=True
    )
    allow_move = BooleanField(
        "Allow Articles/Bylaws placement", default=True
    )
    submit = SubmitField("Submit Motion")


class AmendmentSubmissionForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    text_md = TextAreaField('Amendment Text', validators=[DataRequired()])
    seconder_id = SelectField('Seconder', coerce=int)
    submit = SubmitField('Submit Amendment')


class MotionSubmissionEditForm(FlaskForm):
    """Form for admins to edit a motion submission."""

    title = StringField("Motion Title", validators=[DataRequired()])
    text_md = TextAreaField(
        "Motion Text", validators=[DataRequired()], render_kw={"data-markdown-editor": "1"}
    )
    submit = SubmitField("Save Changes")


class AmendmentSubmissionEditForm(FlaskForm):
    """Form for admins to edit an amendment submission."""

    text_md = TextAreaField(
        "Amendment Text", validators=[DataRequired()], render_kw={"data-markdown-editor": "1"}
    )
    submit = SubmitField("Save Changes")
