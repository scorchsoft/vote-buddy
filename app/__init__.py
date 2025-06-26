import os
from datetime import datetime
from flask import Flask, render_template, g
from .utils import markdown_to_html, format_dt
import secrets

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

        token_salt = app.config.get('TOKEN_SALT', '')
        if not token_salt or token_salt == 'token-salt':
            raise RuntimeError('TOKEN_SALT must be set to a non-default value in production')

        api_token_salt = app.config.get('API_TOKEN_SALT', '')
        if not api_token_salt or api_token_salt == 'api-token-salt':
            raise RuntimeError('API_TOKEN_SALT must be set to a non-default value in production')

    register_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)
    register_cli_commands(app)

    @app.before_request
    def generate_nonce():
        """Generate a unique nonce for each request to allow inline scripts."""
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.after_request
    def set_frame_options(response):
        """Deny framing to mitigate clickjacking."""
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.after_request
    def set_content_security_policy(response):
        """Restrict script and style sources to self and htmx CDN."""
        nonce = getattr(g, 'csp_nonce', '')
        csp = (
            "default-src 'self'; "
            f"script-src 'self' https://unpkg.com 'nonce-{nonce}'; "
            "style-src 'self' https://unpkg.com 'unsafe-inline'; "
            "font-src 'self' https://unpkg.com; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers['Content-Security-Policy'] = csp
        return response

    @app.after_request
    def set_cache_control(response):
        """Set cache control headers - prevent caching in development."""
        if app.debug:  # Only in development mode
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            # Force CSP to be re-evaluated
            response.headers['Vary'] = 'Content-Security-Policy'
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
    app.jinja_env.filters['format_dt'] = format_dt

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

    @app.context_processor
    def inject_cache_bust():
        """Add cache busting timestamp for development."""
        return {
            'cache_bust': int(datetime.now().timestamp()) if app.debug else '1'
        }

    @app.context_processor
    def inject_csp_nonce():
        """Add CSP nonce to template context."""
        return {
            'csp_nonce': getattr(g, 'csp_nonce', '')
        }

    @app.context_processor
    def inject_notice_days():
        return {
            'notice_days': app.config.get('NOTICE_PERIOD_DAYS', 14)
        }

    @app.context_processor
    def inject_comment_utils():
        from .models import Comment, Meeting
        def editing_allowed(comment: Comment, meeting: Meeting) -> bool:
            minutes = app.config.get('COMMENT_EDIT_MINUTES', 15)
            return comment.can_edit(meeting, minutes)
        return {'editing_allowed': editing_allowed}


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
    from .api import bp as api_bp
    from .submissions import bp as submissions_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(meetings_bp)
    app.register_blueprint(voting_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ro_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(submissions_bp)


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
    from .cli import create_admin, generate_fake_data
    app.cli.add_command(create_admin)
    app.cli.add_command(generate_fake_data)

