import os
from flask import Flask, render_template

from .extensions import db, migrate, login_manager, bcrypt, csrf, mail, scheduler


def create_app(config_object='config.DevelopmentConfig'):
    app = Flask(__name__)
    app.config.from_object(config_object)

    if os.getenv('FLASK_ENV') == 'production':
        secret_key = app.config.get('SECRET_KEY', '')
        if not secret_key or secret_key == 'change-me':
            raise RuntimeError('SECRET_KEY must be set to a non-default value in production')

    register_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)

    @app.context_processor
    def inject_meeting_banner():
        """Provide currently open meeting with stage info for templates."""
        from .models import Meeting
        from datetime import datetime

        now = datetime.utcnow()
        meeting = None
        stage = None
        closes_at = None

        try:
            meetings = Meeting.query.all()
        except Exception:
            meetings = []

        for m in meetings:
            if m.opens_at_stage1 and m.opens_at_stage1 <= now < (m.closes_at_stage1 or now):
                meeting = m
                stage = 1
                closes_at = m.closes_at_stage1
                break
            if m.opens_at_stage2 and m.opens_at_stage2 <= now < (m.closes_at_stage2 or now):
                meeting = m
                stage = 2
                closes_at = m.closes_at_stage2
                break

        if not meeting:
            return dict(active_meeting=None)

        if stage == 1:
            time_remaining = meeting.stage1_time_remaining()
        else:
            if not closes_at:
                time_remaining = "N/A"
            else:
                delta = closes_at - now
                if delta.total_seconds() <= 0:
                    time_remaining = "Closed"
                else:
                    hours, rem = divmod(int(delta.total_seconds()), 3600)
                    minutes = rem // 60
                    time_remaining = f"{hours}h {minutes}m"

        return dict(
            active_meeting=meeting,
            stage_name=f"Stage {stage}",
            time_remaining=time_remaining,
            quorum_pct=f"{meeting.quorum_percentage():.1f}",
        )

    @app.after_request
    def set_frame_options(response):
        """Deny framing to mitigate clickjacking."""
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.after_request
    def set_content_security_policy(response):
        """Restrict script and style sources to self and htmx CDN."""
        csp = (
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com; "
            "style-src 'self' https://unpkg.com"
        )
        response.headers['Content-Security-Policy'] = csp
        return response

    return app


def register_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    if not scheduler.running:
        scheduler.init_app(app)
        from .tasks import register_jobs
        register_jobs()
        scheduler.start()
    login_manager.login_view = 'auth.login'

    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return User.query.get(int(user_id))


def register_blueprints(app):
    from .routes import bp as main_bp
    from .auth.routes import bp as auth_bp
    from .meetings.routes import bp as meetings_bp
    from .voting.routes import bp as voting_bp
    from .admin.routes import bp as admin_bp
    from .ro.routes import bp as ro_bp
    from .help.routes import bp as help_bp
    from .notifications.routes import bp as notifications_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(meetings_bp)
    app.register_blueprint(voting_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ro_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(notifications_bp)


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(_):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(_):
        return render_template('errors/404.html'), 404

