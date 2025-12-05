import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"


def create_app() -> Flask:
    """Create configured Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///app.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User  # noqa: WPS433 (import inside factory)
    from .olt_polling import schedule_polling_jobs  # noqa: WPS433

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        """Load user by id for Flask-Login."""
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

    from .routes import auth_bp, page_bp  # noqa: WPS433

    app.register_blueprint(auth_bp)
    app.register_blueprint(page_bp)

    schedule_polling_jobs(app)

    return app
