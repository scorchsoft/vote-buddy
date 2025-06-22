from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
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
from wtforms.validators import DataRequired, Email, Optional, URL


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
    logo_file = FileField(
        "Upload Logo",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "svg"], "Images only!")],
    )
    from_email = StringField("From Email", validators=[DataRequired(), Email()])
    runoff_extension_minutes = IntegerField("Run-off Extension Minutes", validators=[Optional()])
    reminder_hours_before_close = IntegerField("Reminder Hours Before Close", validators=[Optional()])
    reminder_cooldown_hours = IntegerField("Reminder Cooldown Hours", validators=[Optional()])
    stage2_reminder_hours_before_close = IntegerField("Stage 2 Reminder Hours Before Close", validators=[Optional()])
    stage2_reminder_cooldown_hours = IntegerField("Stage 2 Reminder Cooldown Hours", validators=[Optional()])
    reminder_template = StringField("Reminder Template", validators=[Optional()])
    tie_break_decisions = TextAreaField("Tie Break Decisions", validators=[Optional()])
    clerical_text = TextAreaField(
        "Clerical Amendment Text",
        validators=[Optional()],
        render_kw={"data-markdown-editor": "1"},
    )
    move_text = TextAreaField(
        "Articles/Bylaws Placement Text",
        validators=[Optional()],
        render_kw={"data-markdown-editor": "1"},
    )
    final_message = TextAreaField(
        "Final Stage Message",
        validators=[Optional()],
        render_kw={"data-markdown-editor": "1"},
    )
    manual_email_mode = BooleanField("Disable Automatic Emails")
    contact_url = StringField("Contact URL", validators=[Optional(), URL()])
    submit = SubmitField("Save")


class ApiTokenForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Generate")
