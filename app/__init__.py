from flask import Flask

from .extensions import db, migrate


def create_app(config_object='config.DevelopmentConfig'):
    app = Flask(__name__)
    app.config.from_object(config_object)

    register_extensions(app)
    register_blueprints(app)

    return app


def register_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)


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
