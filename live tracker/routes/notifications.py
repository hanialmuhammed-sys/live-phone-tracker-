from datetime import datetime, timedelta, time

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Notification

notifications_bp = Blueprint("notifications", __name__)


def _range_bounds(range_name):
    """Step 9 — Today / Yesterday / This Week filters."""
    today = datetime.utcnow().date()

    if range_name == "today":
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)
    elif range_name == "yesterday":
        yesterday = today - timedelta(days=1)
        start = datetime.combine(yesterday, time.min)
        end = datetime.combine(yesterday, time.max)
    elif range_name == "week":
        week_start = today - timedelta(days=today.weekday())
        start = datetime.combine(week_start, time.min)
        end = datetime.combine(today, time.max)
    else:
        return None, None

    return start, end


@notifications_bp.route("/notifications")
@login_required
def get_notifications():
    if not current_user.family_id:
        return jsonify([])

    query = Notification.query.filter_by(family_id=current_user.family_id)

    # Step 9 — type filter: SOS / Geofence (arrival+departure) / Battery / System
    type_param = request.args.get("type")
    if type_param:
        types = [t.strip() for t in type_param.split(",") if t.strip()]
        if types:
            query = query.filter(Notification.type.in_(types))

    # Step 9 — date range filter
    range_param = request.args.get("range")
    if range_param:
        start, end = _range_bounds(range_param)
        if start and end:
            query = query.filter(Notification.created_at >= start, Notification.created_at <= end)

    notifications = query.order_by(Notification.created_at.desc()).limit(100).all()

    result = []
    for n in notifications:
        result.append({
            "id": n.id,
            "user_id": n.user_id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        })

    return jsonify(result)


@notifications_bp.route("/notification/read", methods=["POST"])
@login_required
def mark_read():
    """
    Body {"id": 5} marks one notification read.
    No body / empty body marks every notification in the family read
    (used when the panel is opened — Step 5's counter reset to 0).
    """
    data = request.get_json(silent=True) or {}
    notification_id = data.get("id")

    query = Notification.query.filter_by(family_id=current_user.family_id)

    if notification_id:
        query = query.filter_by(id=notification_id)

    query.update({"is_read": True})
    db.session.commit()

    return jsonify({"message": "Marked as read"})


@notifications_bp.route("/notifications", methods=["DELETE"])
@login_required
def clear_notifications():
    """Clears the whole family's notification history."""
    Notification.query.filter_by(family_id=current_user.family_id).delete()
    db.session.commit()

    return jsonify({"message": "Notifications cleared"})