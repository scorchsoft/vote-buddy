from flask import Flask

from .extensions import db, migrate, login_manager, bcrypt, csrf


def create_app(config_object='config.DevelopmentConfig'):
    app = Flask(__name__)
    app.config.from_object(config_object)

    register_extensions(app)
    register_blueprints(app)

    @app.after_request
    def set_frame_options(response):
        """Deny framing to mitigate clickjacking."""
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    return app


def register_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
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

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(meetings_bp)
    app.register_blueprint(voting_bp)
    app.register_blueprint(admin_bp)
