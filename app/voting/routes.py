from flask import Blueprint, render_template

bp = Blueprint('voting', __name__, url_prefix='/vote')

@bp.route('/')
def ballot_home():
    return render_template('voting/home.html')
