from flask import Blueprint

bp = Blueprint('comments', __name__, url_prefix='/comments')

from . import routes  # noqa: E402
