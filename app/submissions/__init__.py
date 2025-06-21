from flask import Blueprint

bp = Blueprint('submissions', __name__, url_prefix='/submit')

from . import routes  # noqa
