from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
import json
from flask_login import login_required
from ..extensions import db
from ..models import (
    Meeting,
    User,
    Role,
    Permission,
    AppSetting,
    Amendment,
    Member,
    AmendmentObjection,
)
from .forms import UserForm, UserCreateForm, RoleForm, SettingsForm

from ..permissions import permission_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
@permission_required("view_dashboard")
def dashboard():
    meetings = Meeting.query.all()
    return render_template("admin/dashboard.html", meetings=meetings)


@bp.route("/meetings/<int:meeting_id>/toggle-public", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def toggle_public_results(meeting_id: int):
    meeting = Meeting.query.get_or_404(meeting_id)
    meeting.public_results = not meeting.public_results
    db.session.commit()
    return redirect(url_for("admin.dashboard"))


@bp.route("/objections")
@login_required
@permission_required("manage_meetings")
def list_objections():
    objs = (
        AmendmentObjection.query.join(Amendment, Amendment.id == AmendmentObjection.amendment_id)
        .join(Member, Member.id == AmendmentObjection.member_id)
        .add_columns(AmendmentObjection, Amendment, Member)
        .order_by(AmendmentObjection.created_at.desc())
        .all()
    )
    return render_template("admin/objections.html", objections=[(o[0], o[1], o[2]) for o in objs])


@bp.route("/objections/<int:amendment_id>/reinstate", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def reinstate_amendment(amendment_id: int):
    amendment = Amendment.query.get_or_404(amendment_id)
    count = AmendmentObjection.query.filter_by(amendment_id=amendment_id).count()
    total = Member.query.filter_by(meeting_id=amendment.meeting_id).count()
    threshold = max(25, int(total * 0.05))
    if count >= threshold:
        amendment.status = None
        db.session.commit()
        flash("Amendment reinstated", "success")
    else:
        flash("Objection threshold not met", "error")
    return redirect(url_for("admin.list_objections"))


@bp.route("/users")
@login_required
@permission_required("manage_users")
def list_users():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "email")
    direction = request.args.get("direction", "asc")

    query = User.query
    if q:
        search = f"%{q}%"
        query = query.filter(User.email.ilike(search))

    if sort == "created_at":
        order_attr = User.created_at
    else:
        order_attr = User.email
    query = query.order_by(
        order_attr.asc() if direction == "asc" else order_attr.desc()
    )

    users = query.all()

    template = (
        "admin/_user_rows.html"
        if request.headers.get("HX-Request")
        else "admin/users.html"
    )
    return render_template(
        template,
        users=users,
        q=q,
        sort=sort,
        direction=direction,
    )


def _save_user(form: UserForm, user: User | None = None) -> User:
    """Populate User from form and persist."""
    if user is None:
        user = User()

    user.email = form.email.data
    user.role_id = form.role_id.data
    user.is_active = form.is_active.data
    if form.password.data:
        user.set_password(form.password.data)

    db.session.add(user)
    db.session.commit()
    return user


@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def create_user():
    form = UserCreateForm()
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name)]
    if form.validate_on_submit():
        _save_user(form)
        return redirect(url_for("admin.list_users"))
    return render_template("admin/user_form.html", form=form, user=None)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name)]
    if form.validate_on_submit():
        _save_user(form, user)
        return redirect(url_for("admin.list_users"))
    return render_template("admin/user_form.html", form=form, user=user)


def _save_role(form: RoleForm, role: Role | None = None) -> Role:
    """Populate Role from form and persist."""
    if role is None:
        role = Role()

    role.name = form.name.data
    role.permissions = Permission.query.filter(
        Permission.id.in_(form.permission_ids.data)
    ).all()

    db.session.add(role)
    db.session.commit()
    return role


@bp.route("/roles")
@login_required
@permission_required("manage_users")
def list_roles():
    roles = Role.query.order_by(Role.name).all()
    return render_template("admin/roles.html", roles=roles)


@bp.route("/roles/create", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def create_role():
    form = RoleForm()
    form.permission_ids.choices = [
        (p.id, p.name) for p in Permission.query.order_by(Permission.name)
    ]
    if form.validate_on_submit():
        _save_role(form)
        return redirect(url_for("admin.list_roles"))
    return render_template("admin/role_form.html", form=form, role=None)


@bp.route("/roles/<int:role_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    form = RoleForm(obj=role)
    form.permission_ids.choices = [
        (p.id, p.name) for p in Permission.query.order_by(Permission.name)
    ]
    if request.method == "GET":
        form.permission_ids.data = [p.id for p in role.permissions]
    if form.validate_on_submit():
        _save_role(form, role)
        return redirect(url_for("admin.list_roles"))
    return render_template("admin/role_form.html", form=form, role=role)


@bp.route("/settings", methods=["GET", "POST"])
@login_required
@permission_required("manage_settings")
def manage_settings():
    form = SettingsForm()
    if request.method == "GET":
        form.site_title.data = AppSetting.get("site_title", "VoteBuddy")
        form.site_logo.data = AppSetting.get("site_logo", "")
        form.from_email.data = AppSetting.get(
            "from_email",
            current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@example.com"),
        )
        form.runoff_extension_minutes.data = int(
            AppSetting.get(
                "runoff_extension_minutes",
                current_app.config.get("RUNOFF_EXTENSION_MINUTES", 2880),
            )
        )
        form.reminder_hours_before_close.data = int(
            AppSetting.get(
                "reminder_hours_before_close",
                current_app.config.get("REMINDER_HOURS_BEFORE_CLOSE", 6),
            )
        )
        form.reminder_cooldown_hours.data = int(
            AppSetting.get(
                "reminder_cooldown_hours",
                current_app.config.get("REMINDER_COOLDOWN_HOURS", 24),
            )
        )
        form.reminder_template.data = AppSetting.get(
            "reminder_template",
            current_app.config.get("REMINDER_TEMPLATE", "email/reminder"),
        )
        form.tie_break_decisions.data = AppSetting.get(
            "tie_break_decisions",
            json.dumps(current_app.config.get("TIE_BREAK_DECISIONS", {})),
        )
        form.clerical_text.data = AppSetting.get(
            "clerical_text", current_app.config.get("CLERICAL_TEXT")
        )
        form.move_text.data = AppSetting.get(
            "move_text", current_app.config.get("MOVE_TEXT")
        )
    if form.validate_on_submit():
        AppSetting.set("site_title", form.site_title.data)
        AppSetting.set("site_logo", form.site_logo.data)
        AppSetting.set("from_email", form.from_email.data)
        AppSetting.set(
            "runoff_extension_minutes", str(form.runoff_extension_minutes.data)
        )
        AppSetting.set(
            "reminder_hours_before_close", str(form.reminder_hours_before_close.data)
        )
        AppSetting.set(
            "reminder_cooldown_hours", str(form.reminder_cooldown_hours.data)
        )
        AppSetting.set("reminder_template", form.reminder_template.data)
        AppSetting.set("tie_break_decisions", form.tie_break_decisions.data)
        AppSetting.set("clerical_text", form.clerical_text.data)
        AppSetting.set("move_text", form.move_text.data)
        flash("Settings updated", "success")
        return redirect(url_for("admin.manage_settings"))
    return render_template("admin/settings_form.html", form=form)


@bp.route("/settings/reset/<key>", methods=["POST"])
@login_required
@permission_required("manage_settings")
def reset_setting(key: str):
    AppSetting.delete(key)
    flash("Setting reset to default", "success")
    return redirect(url_for("admin.manage_settings"))
