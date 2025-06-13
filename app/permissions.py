from functools import wraps
from flask import abort
from flask_login import current_user


def permission_required(permission_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_permission(permission_name):
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator
