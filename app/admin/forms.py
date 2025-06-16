from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SelectField,
    BooleanField,
    SubmitField,
    SelectMultipleField,
    IntegerField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Optional


class UserForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[Optional()])
    role_id = SelectField("Role", coerce=int, validators=[DataRequired()])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save")


class UserCreateForm(UserForm):
    password = PasswordField("Password", validators=[DataRequired()])


class RoleForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    permission_ids = SelectMultipleField("Permissions", coerce=int)
    submit = SubmitField("Save")


class PermissionForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Save")


class SettingsForm(FlaskForm):
    site_title = StringField("Site Title", validators=[DataRequired()])
    site_logo = StringField("Site Logo", validators=[Optional()])
    from_email = StringField("From Email", validators=[DataRequired(), Email()])
    runoff_extension_minutes = IntegerField("Run-off Extension Minutes")
    reminder_hours_before_close = IntegerField("Reminder Hours Before Close")
    reminder_cooldown_hours = IntegerField("Reminder Cooldown Hours")
    reminder_template = StringField("Reminder Template")
    tie_break_decisions = TextAreaField("Tie Break Decisions", validators=[Optional()])
    clerical_text = TextAreaField("Clerical Amendment Text", validators=[Optional()])
    move_text = TextAreaField("Articles/Bylaws Placement Text", validators=[Optional()])
    submit = SubmitField("Save")
