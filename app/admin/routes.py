from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    abort,
)
import os
from uuid6 import uuid7
from werkzeug.utils import secure_filename
from PIL import Image
import json
from flask_login import login_required
from datetime import datetime
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
    ApiToken,
)
from .forms import (
    UserForm,
    UserCreateForm,
    RoleForm,
    PermissionForm,
    SettingsForm,
    ApiTokenForm,
)

from ..permissions import permission_required
from ..services.audit import record_action, get_logs

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required
@permission_required("view_dashboard")
def dashboard():
    meetings = Meeting.query.all()
    now = datetime.utcnow()
    objection_amend_ids = (
        db.session.query(AmendmentObjection.amendment_id)
        .filter(AmendmentObjection.confirmed_at.isnot(None))
        .group_by(AmendmentObjection.amendment_id)
        .all()
    )
    objections = []
    for (aid,) in objection_amend_ids:
        amend = db.session.get(Amendment, aid)
        count = (
            AmendmentObjection.query.filter_by(amendment_id=aid)
            .filter(AmendmentObjection.confirmed_at.isnot(None))
            .count()
        )
        deadlines = [
            o.deadline_final or o.deadline_first
            for o in AmendmentObjection.query.filter_by(amendment_id=aid)
            .filter(AmendmentObjection.confirmed_at.isnot(None))
        ]
        upcoming = [d for d in deadlines if d and d > now]
        if upcoming:
            deadline = min(upcoming)
            diff = deadline - now
            days = diff.days
            hours = diff.seconds // 3600
            remain = f"{days}d {hours}h"
        else:
            remain = "Closed"
        objections.append((amend, count, remain))
    return render_template(
        "admin/dashboard.html", meetings=meetings, objections=objections
    )


@bp.route("/meetings/<int:meeting_id>/toggle-public", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def toggle_public_results(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    meeting.public_results = not meeting.public_results
    db.session.commit()
    record_action('toggle_public_results', f'meeting_id={meeting.id}')
    return redirect(url_for("admin.dashboard"))


@bp.route("/meetings/<int:meeting_id>/toggle-doc", methods=["POST"])
@login_required
@permission_required("manage_meetings")
def toggle_results_doc(meeting_id: int):
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    meeting.results_doc_published = not meeting.results_doc_published
    db.session.commit()
    record_action('toggle_results_doc', f'meeting_id={meeting.id}')
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
    amendment = db.session.get(Amendment, amendment_id)
    if amendment is None:
        abort(404)
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

    # Only return partial template for specific HTMX requests (search/sort)
    # Not for general page navigation via hx-boost
    if request.headers.get("HX-Request") and request.headers.get("HX-Target") == "user-table-body":
        template = "admin/_user_rows.html"
    else:
        template = "admin/users.html"
    
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
        user = _save_user(form)
        record_action("create_user", f"user_id={user.id}")
        return redirect(url_for("admin.list_users"))
    return render_template("admin/user_form.html", form=form, user=None)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    form = UserForm(obj=user)
    form.role_id.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name)]
    if form.validate_on_submit():
        updated = _save_user(form, user)
        record_action("edit_user", f"user_id={updated.id}")
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
    role = db.session.get(Role, role_id)
    if role is None:
        abort(404)
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


def _save_permission(form: PermissionForm, perm: Permission | None = None) -> Permission:
    """Populate Permission from form and persist."""
    if perm is None:
        perm = Permission()

    perm.name = form.name.data

    db.session.add(perm)
    db.session.commit()
    return perm


@bp.route("/permissions")
@login_required
@permission_required("manage_users")
def list_permissions():
    permissions = Permission.query.order_by(Permission.name).all()
    return render_template("admin/permissions.html", permissions=permissions)


@bp.route("/permissions/create", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def create_permission():
    form = PermissionForm()
    if form.validate_on_submit():
        _save_permission(form)
        return redirect(url_for("admin.list_permissions"))
    return render_template("admin/permission_form.html", form=form, permission=None)


@bp.route("/permissions/<int:permission_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("manage_users")
def edit_permission(permission_id):
    perm = db.session.get(Permission, permission_id)
    if perm is None:
        abort(404)
    form = PermissionForm(obj=perm)
    if form.validate_on_submit():
        _save_permission(form, perm)
        return redirect(url_for("admin.list_permissions"))
    return render_template("admin/permission_form.html", form=form, permission=perm)


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
            ) or current_app.config.get("RUNOFF_EXTENSION_MINUTES", 2880)
        )
        form.reminder_hours_before_close.data = int(
            AppSetting.get(
                "reminder_hours_before_close",
                current_app.config.get("REMINDER_HOURS_BEFORE_CLOSE", 6),
            ) or current_app.config.get("REMINDER_HOURS_BEFORE_CLOSE", 6)
        )
        form.reminder_cooldown_hours.data = int(
            AppSetting.get(
                "reminder_cooldown_hours",
                current_app.config.get("REMINDER_COOLDOWN_HOURS", 24),
            ) or current_app.config.get("REMINDER_COOLDOWN_HOURS", 24)
        )
        form.stage2_reminder_hours_before_close.data = int(
            AppSetting.get(
                "stage2_reminder_hours_before_close",
                current_app.config.get("STAGE2_REMINDER_HOURS_BEFORE_CLOSE", 6),
            ) or current_app.config.get("STAGE2_REMINDER_HOURS_BEFORE_CLOSE", 6)
        )
        form.stage2_reminder_cooldown_hours.data = int(
            AppSetting.get(
                "stage2_reminder_cooldown_hours",
                current_app.config.get("STAGE2_REMINDER_COOLDOWN_HOURS", 24),
            ) or current_app.config.get("STAGE2_REMINDER_COOLDOWN_HOURS", 24)
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
        form.final_message.data = AppSetting.get(
            "final_message",
            current_app.config.get("FINAL_STAGE_MESSAGE"),
        )
        form.contact_url.data = AppSetting.get(
            "contact_url",
            "https://www.britishpowerlifting.org/contactus",
        )
        form.manual_email_mode.data = AppSetting.get("manual_email_mode", "0") == "1"
    if form.validate_on_submit():
        AppSetting.set("site_title", form.site_title.data)
        if form.logo_file.data:
            file = form.logo_file.data
            ext = os.path.splitext(file.filename)[1].lower()
            filename = f"{uuid7()}{ext}"
            upload_dir = os.path.join(current_app.static_folder, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, filename)
            if ext == ".svg":
                file.save(path)
            else:
                img = Image.open(file)
                img.thumbnail((400, 400))
                img.save(path)
            AppSetting.set("site_logo", f"uploads/{filename}")
        else:
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
        AppSetting.set(
            "stage2_reminder_hours_before_close",
            str(form.stage2_reminder_hours_before_close.data),
        )
        AppSetting.set(
            "stage2_reminder_cooldown_hours",
            str(form.stage2_reminder_cooldown_hours.data),
        )
        AppSetting.set("reminder_template", form.reminder_template.data)
        AppSetting.set("tie_break_decisions", form.tie_break_decisions.data)
        AppSetting.set("clerical_text", form.clerical_text.data)
        AppSetting.set("move_text", form.move_text.data)
        AppSetting.set("final_message", form.final_message.data)
        if form.contact_url.data:
            AppSetting.set("contact_url", form.contact_url.data)
        else:
            AppSetting.delete("contact_url")
        AppSetting.set("manual_email_mode", "1" if form.manual_email_mode.data else "0")
        record_action("update_settings")
        flash("Settings updated", "success")
        return redirect(url_for("admin.manage_settings"))
    return render_template("admin/settings_form.html", form=form)


@bp.route("/settings/reset/<key>", methods=["POST"])
@login_required
@permission_required("manage_settings")
def reset_setting(key: str):
    AppSetting.delete(key)
    record_action("reset_setting", key)
    flash("Setting reset to default", "success")
    return redirect(url_for("admin.manage_settings"))


@bp.route("/api-tokens", methods=["GET", "POST"])
@login_required
@permission_required("manage_settings")
def manage_api_tokens():
    form = ApiTokenForm()
    if form.validate_on_submit():
        token_obj, plain = ApiToken.create(
            form.name.data, current_app.config["API_TOKEN_SALT"]
        )
        db.session.commit()
        flash(f"New token: {plain}", "success")
        return redirect(url_for("admin.manage_api_tokens"))
    tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()
    return render_template("admin/api_tokens.html", form=form, tokens=tokens)


@bp.post("/api-tokens/<int:token_id>/revoke")
@login_required
@permission_required("manage_settings")
def revoke_api_token(token_id: int):
    token = db.session.get(ApiToken, token_id)
    if token:
        db.session.delete(token)
        db.session.commit()
        flash("Token revoked", "success")
    return redirect(url_for("admin.manage_api_tokens"))

@bp.route("/audit")
@login_required
@permission_required("manage_users")
def view_audit():
    page = request.args.get("page", 1, type=int)
    pagination = get_logs(page=page, per_page=20)
    return render_template(
        "admin/audit.html",
        logs=pagination.items,
        pagination=pagination,
    )
