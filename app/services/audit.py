from flask_login import current_user

from ..extensions import db
from ..models import AdminLog


def record_action(action: str, details: str | None = None, user_id: int | None = None) -> AdminLog:
    """Persist an administrative action."""
    user_id = user_id or getattr(current_user, "id", None)
    log = AdminLog(user_id=user_id, action=action, details=details)
    db.session.add(log)
    db.session.commit()
    return log


def get_logs(page: int = 1, per_page: int = 20):
    """Return paginated audit log entries ordered by newest first."""
    return (
        AdminLog.query.order_by(AdminLog.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
