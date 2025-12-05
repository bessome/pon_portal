from typing import Optional

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")

    def set_password(self, password: str) -> None:
        """Hash and set password for user."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check provided password against stored hash."""
        return check_password_hash(self.password_hash, password)

    @classmethod
    def get_by_username(cls, username: str) -> Optional["User"]:
        """Retrieve user by username."""
        return cls.query.filter_by(username=username).first()
