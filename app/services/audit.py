from flask_login import current_user
from datetime import datetime

from ..extensions import db
from ..models import AdminLog, User


def record_action(action: str, details: str | None = None, user_id: int | None = None) -> AdminLog:
    """Persist an administrative action."""
    user_id = user_id or getattr(current_user, "id", None)
    log = AdminLog(user_id=user_id, action=action, details=details)
    db.session.add(log)
    db.session.commit()
    return log


def get_logs(
    page: int = 1,
    per_page: int = 20,
    q: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
):
    """Return paginated audit log entries ordered by newest first."""
    query = AdminLog.query
    if q:
        search = f"%{q}%"
        query = query.join(AdminLog.user, isouter=True).filter(
            db.or_(
                AdminLog.action.ilike(search),
                AdminLog.details.ilike(search),
                AdminLog.user.has(User.email.ilike(search)),
            )
        )
    if start:
        query = query.filter(AdminLog.created_at >= start)
    if end:
        query = query.filter(AdminLog.created_at <= end)

    return query.order_by(AdminLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
