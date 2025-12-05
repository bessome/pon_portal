from functools import wraps
from typing import Callable, TypeVar

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .models import User

F = TypeVar("F", bound=Callable[..., object])

auth_bp = Blueprint("auth", __name__, url_prefix="/api")
page_bp = Blueprint("pages", __name__)


def role_required(*roles: str) -> Callable[[F], F]:
    """Require user to have one of the given roles."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"message": "Authentication required"}), 401
            if current_user.role not in roles:
                return jsonify({"message": "Forbidden"}), 403
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


@page_bp.route("/")
def index():
    """Serve main page."""
    return render_template("index.html")


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password")
    role = data.get("role", "user")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    if User.get_by_username(username):
        return jsonify({"message": "User already exists"}), 409

    if role not in {"admin", "user"}:
        return jsonify({"message": "Invalid role"}), 400

    if role == "admin" and (not current_user.is_authenticated or current_user.role != "admin"):
        return jsonify({"message": "Admin approval required for admin role"}), 403

    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created", "username": user.username, "role": user.role}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and create session."""
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password")

    user = User.get_by_username(username)
    if not user or not password or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    login_user(user)
    return jsonify({"message": "Logged in", "username": user.username, "role": user.role})


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Log current user out."""
    logout_user()
    return jsonify({"message": "Logged out"})


@auth_bp.route("/profile")
@login_required
def profile():
    """Return profile information for current user."""
    return jsonify({"username": current_user.username, "role": current_user.role})


@auth_bp.route("/admin")
@role_required("admin")
def admin_only():
    """Example admin-only endpoint."""
    return jsonify({"message": "Welcome, admin"})
