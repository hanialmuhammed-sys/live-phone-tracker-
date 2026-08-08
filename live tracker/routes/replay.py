from datetime import datetime

from flask import Blueprint, render_template, jsonify, abort
from flask_login import login_required, current_user

from extensions import db
from models import Location, Visit
from routes.analytics import compute_daily_stats
from activity_service import log_activity

replay_bp = Blueprint("replay", __name__)


def _parse_date(date):
    try:
        return datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        abort(400, description="Date must be in YYYY-MM-DD format")


@replay_bp.route("/replay")
@login_required
def replay_page():
    if current_user.family_id:
        log_activity(current_user.family_id, f"{current_user.username} viewed replay")
    return render_template("replay.html")


@replay_bp.route("/replay/<date>")
@login_required
def replay(date):
    _parse_date(date)  # validates the format, matches Step 1's route

    locations = Location.query.filter(
        db.func.date(Location.timestamp) == date,
        Location.user_id == current_user.id
    ).order_by(Location.timestamp).all()

    return jsonify([
        {
            "lat": l.latitude,
            "lon": l.longitude,
            "time": l.timestamp.strftime("%H:%M:%S")
        }
        for l in locations
    ])


@replay_bp.route("/replay/<date>/stats")
@login_required
def replay_stats(date):
    parsed_date = _parse_date(date)

    stats = compute_daily_stats(current_user.id, parsed_date)

    stops = Visit.query.filter(
        Visit.user_id == current_user.id,
        db.func.date(Visit.arrival_time) == date
    ).count()

    return jsonify({
        "distance": stats["distance"],
        "stops": stops,
        "duration_seconds": stats["moving_time"] + stats["stationary_time"],
        "average_speed": stats["average_speed"]
    })