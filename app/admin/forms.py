from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Optional


class UserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional()])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')


class UserCreateForm(UserForm):
    password = PasswordField('Password', validators=[DataRequired()])

