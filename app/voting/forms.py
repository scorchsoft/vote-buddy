from flask_wtf import FlaskForm
from wtforms import RadioField, SubmitField
from wtforms.validators import DataRequired

class VoteForm(FlaskForm):
    choice = RadioField(
        'Your vote',
        choices=[('yes', 'Yes'), ('no', 'No'), ('abstain', 'Abstain')],
        validators=[DataRequired()],
    )
    submit = SubmitField('Submit vote')
