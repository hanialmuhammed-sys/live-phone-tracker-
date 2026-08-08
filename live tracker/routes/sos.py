from datetime import datetime

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from extensions import db, socketio
from models import SOS, Family, User
from notification_service import create_notification
from activity_service import log_activity

sos_bp = Blueprint("sos", __name__)


@sos_bp.route("/sos", methods=["POST"])
@login_required
def send_sos():
    if not current_user.family_id:
        return jsonify({"error": "You must join or create a family first"}), 400

    data = request.get_json()

    if not data or "lat" not in data or "lon" not in data:
        return jsonify({"error": "lat and lon are required"}), 400

    alert = SOS(
        user_id=current_user.id,
        latitude=data["lat"],
        longitude=data["lon"],
        message=data.get("message", "Need Help"),
        status="ACTIVE"
    )

    db.session.add(alert)
    db.session.commit()

    socketio.emit("sos_alert", {
        "id": alert.id,
        "user_id": current_user.id,
        "name": current_user.username,
        "lat": alert.latitude,
        "lon": alert.longitude,
        "message": alert.message,
        "time": alert.created_at.strftime("%H:%M"),
        "status": alert.status
    }, room=f"family_{current_user.family_id}")

    create_notification(
        current_user,
        title="SOS",
        message=f"{current_user.username} triggered SOS",
        type_="sos"
    )

    log_activity(current_user.family_id, f"SOS triggered by {current_user.username}")

    return jsonify({"message": "SOS sent", "id": alert.id})


@sos_bp.route("/sos/history")
@login_required
def sos_history():
    if not current_user.family_id:
        return render_template("sos_history.html", alerts=[])

    member_ids = [
        member.id for member in
        User.query.filter_by(family_id=current_user.family_id).all()
    ]

    alerts = (
        SOS.query
        .filter(SOS.user_id.in_(member_ids))
        .order_by(SOS.created_at.desc())
        .all()
    )

    users_by_id = {member.id: member for member in User.query.filter(User.id.in_(member_ids)).all()}

    return render_template("sos_history.html", alerts=alerts, users_by_id=users_by_id)


@sos_bp.route("/sos/resolve/<int:alert_id>", methods=["POST"])
@login_required
def resolve_sos(alert_id):
    alert = SOS.query.get_or_404(alert_id)

    family = Family.query.get(current_user.family_id)
    sender = User.query.get(alert.user_id)

    is_family_owner = family and family.owner_id == current_user.id
    is_sender = alert.user_id == current_user.id
    same_family = sender and sender.family_id == current_user.family_id

    if not same_family or not (is_family_owner or is_sender):
        return jsonify({"error": "Not authorized to resolve this alert"}), 403

    alert.status = "RESOLVED"
    db.session.commit()

    socketio.emit("sos_resolved", {
        "id": alert.id,
        "user_id": alert.user_id
    }, room=f"family_{current_user.family_id}")

    return jsonify({"message": "SOS resolved"})