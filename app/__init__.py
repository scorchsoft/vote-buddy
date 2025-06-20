import os
from datetime import datetime
from flask import Flask, render_template
from .utils import markdown_to_html

from .extensions import (
    db,
    migrate,
    login_manager,
    bcrypt,
    csrf,
    mail,
    scheduler,
    limiter,
)


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
    register_cli_commands(app)

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
            "style-src 'self' https://unpkg.com 'unsafe-inline'"
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
    limiter.init_app(app)
    if not scheduler.running:
        scheduler.init_app(app)
        from .tasks import register_jobs
        register_jobs()
        scheduler.start()
    login_manager.login_view = 'auth.login'

    # register template filters
    app.jinja_env.filters['markdown_to_html'] = markdown_to_html

    from .models import User, AppSetting, Meeting

    @app.context_processor
    def inject_settings():
        def setting(key: str, default: str | None = None) -> str | None:
            return AppSetting.get(key, default)
        return {'setting': setting}

    @app.context_processor
    def inject_meeting_status():
        meeting = Meeting.query.order_by(Meeting.notice_date.desc()).first()
        if meeting:
            stage_label = meeting.status or 'Draft'
            quorum_pct = meeting.quorum_percentage()
        else:
            stage_label = None
            quorum_pct = None
        return {
            'current_stage_label': stage_label,
            'current_quorum_pct': quorum_pct,
        }


    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))


def register_blueprints(app):
    from .routes import bp as main_bp
    from .auth.routes import bp as auth_bp
    from .meetings.routes import bp as meetings_bp
    from .voting.routes import bp as voting_bp
    from .admin.routes import bp as admin_bp
    from .ro.routes import bp as ro_bp
    from .help.routes import bp as help_bp
    from .notifications.routes import bp as notifications_bp
    from .comments import bp as comments_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(meetings_bp)
    app.register_blueprint(voting_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ro_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(comments_bp)


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(_):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(_):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(_):
        return render_template('errors/500.html'), 500


def register_cli_commands(app):
    from .cli import create_admin
    app.cli.add_command(create_admin)

