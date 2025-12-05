from datetime import datetime
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


class OLT(db.Model):
    __tablename__ = "olt"

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False, default="")
    model = db.Column(db.String(100), nullable=False)
    polling_interval = db.Column(db.Integer, nullable=False, default=300)
    last_polled_at = db.Column(db.DateTime)

    onus = db.relationship("ONU", backref="olt", cascade="all, delete-orphan", lazy=True)


class ONU(db.Model):
    __tablename__ = "onu"
    __table_args__ = (
        db.UniqueConstraint("olt_id", "interface", "serial_number", name="onu_identity"),
    )

    id = db.Column(db.Integer, primary_key=True)
    olt_id = db.Column(db.Integer, db.ForeignKey("olt.id"), nullable=False)
    interface = db.Column(db.String(64), nullable=False)
    serial_number = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="unknown")
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
