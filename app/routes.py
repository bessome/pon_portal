from functools import wraps
from typing import Callable, TypeVar

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .models import OLT, ONU, User
from .olt_polling import poll_single_olt

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


@auth_bp.route("/olts", methods=["GET"])
@role_required("admin")
def list_olts():
    """List all OLT devices."""
    olts = OLT.query.all()
    return jsonify([
        {
            "id": olt.id,
            "ip": olt.ip,
            "address": olt.address,
            "model": olt.model,
            "polling_interval": olt.polling_interval,
            "last_polled_at": olt.last_polled_at.isoformat() if olt.last_polled_at else None,
        }
        for olt in olts
    ])


@auth_bp.route("/olts", methods=["POST"])
@role_required("admin")
def create_olt():
    """Create a new OLT entry."""
    data = request.get_json() or {}
    ip = (data.get("ip") or "").strip()
    address = (data.get("address") or "").strip()
    model = (data.get("model") or "").strip()
    polling_interval = int(data.get("polling_interval", 300))

    if not ip or not model:
        return jsonify({"message": "IP and model are required"}), 400

    if OLT.query.filter_by(ip=ip).first():
        return jsonify({"message": "OLT with this IP already exists"}), 409

    olt = OLT(
        ip=ip,
        address=address,
        model=model,
        polling_interval=max(polling_interval, 30),
    )
    db.session.add(olt)
    db.session.commit()
    return jsonify({"message": "OLT created", "id": olt.id}), 201


@auth_bp.route("/olts/<int:olt_id>", methods=["GET"])
@role_required("admin")
def get_olt(olt_id: int):
    """Retrieve OLT information."""
    olt = OLT.query.get_or_404(olt_id)
    return jsonify(
        {
            "id": olt.id,
            "ip": olt.ip,
            "address": olt.address,
            "model": olt.model,
            "polling_interval": olt.polling_interval,
            "last_polled_at": olt.last_polled_at.isoformat() if olt.last_polled_at else None,
        }
    )


@auth_bp.route("/olts/<int:olt_id>", methods=["PUT"])
@role_required("admin")
def update_olt(olt_id: int):
    """Update OLT attributes."""
    olt = OLT.query.get_or_404(olt_id)
    data = request.get_json() or {}

    if "ip" in data:
        new_ip = (data.get("ip") or "").strip()
        if not new_ip:
            return jsonify({"message": "IP cannot be empty"}), 400
        conflict = OLT.query.filter(OLT.id != olt.id, OLT.ip == new_ip).first()
        if conflict:
            return jsonify({"message": "IP already in use"}), 409
        olt.ip = new_ip

    if "address" in data:
        olt.address = (data.get("address") or "").strip()

    if "model" in data:
        updated_model = (data.get("model") or "").strip()
        if not updated_model:
            return jsonify({"message": "Model cannot be empty"}), 400
        olt.model = updated_model

    if "polling_interval" in data:
        try:
            interval = int(data.get("polling_interval"))
        except (TypeError, ValueError):
            return jsonify({"message": "Invalid interval"}), 400
        olt.polling_interval = max(interval, 30)

    db.session.commit()
    return jsonify({"message": "OLT updated"})


@auth_bp.route("/olts/<int:olt_id>", methods=["DELETE"])
@role_required("admin")
def delete_olt(olt_id: int):
    """Delete OLT entry."""
    olt = OLT.query.get_or_404(olt_id)
    db.session.delete(olt)
    db.session.commit()
    return jsonify({"message": "OLT deleted"})


@auth_bp.route("/olts/<int:olt_id>/onus", methods=["GET"])
@role_required("admin")
def list_onu(olt_id: int):
    """List ONUs associated with an OLT."""
    olt = OLT.query.get_or_404(olt_id)
    return jsonify(
        [
            {
                "id": onu.id,
                "interface": onu.interface,
                "serial_number": onu.serial_number,
                "status": onu.status,
                "last_seen": onu.last_seen.isoformat() if onu.last_seen else None,
            }
            for onu in olt.onus
        ]
    )


@auth_bp.route("/olts/<int:olt_id>/poll", methods=["POST"])
@role_required("admin")
def poll_olt(olt_id: int):
    """Trigger immediate polling of a single OLT."""
    olt = OLT.query.get_or_404(olt_id)
    poll_single_olt(olt)
    return jsonify({"message": "Polling finished"})
