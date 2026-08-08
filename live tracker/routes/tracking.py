from datetime import datetime

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from flask_socketio import join_room

from extensions import db, socketio
from models import Location, User, Geofence, Visit
from utils import haversine_distance
from notification_service import create_notification

tracking_bp = Blueprint("tracking", __name__)

# In-memory "was this user last inside this geofence?" tracker.
# Keyed by (user_id, geofence_id) -> True (inside) / False (outside).
# Resets on server restart, which just means the first reading after
# a restart is recorded silently instead of firing a false "arrived".
geofence_status = {}

# In-memory arrival-time tracker, so we know how long someone has been
# inside a geofence when they eventually leave (Part 4).
# Keyed by (user_id, geofence_id) -> datetime they arrived.
geofence_arrival_time = {}

MIN_VISIT_SECONDS = 10 * 60  # 10 minutes, per Part 4

# In-memory "have we already warned about low battery?" tracker, so we
# notify once per drop below the threshold instead of on every single
# location ping while the battery stays low. Keyed by user_id -> bool.
low_battery_notified = {}

LOW_BATTERY_THRESHOLD = 20


@tracking_bp.route("/phone")
@login_required
def phone():
    return render_template("phone.html")


@socketio.on("connect")
def handle_connect():
    if current_user.is_authenticated and current_user.family_id:
        join_room(f"family_{current_user.family_id}")


@socketio.on("disconnect")
def handle_disconnect():
    if current_user.is_authenticated and current_user.family_id:
        create_notification(
            current_user,
            title="Offline",
            message=f"{current_user.username} went offline",
            type_="system"
        )


def check_low_battery(user, location):
    if location.battery is None:
        return

    was_notified = low_battery_notified.get(user.id, False)

    if location.battery <= LOW_BATTERY_THRESHOLD and not was_notified:
        low_battery_notified[user.id] = True
        create_notification(
            user,
            title="Battery Low",
            message=f"{user.username} battery {location.battery}%",
            type_="battery"
        )
    elif location.battery > LOW_BATTERY_THRESHOLD:
        low_battery_notified[user.id] = False


@tracking_bp.route("/location", methods=["POST"])
@login_required
def update_location():
    if not current_user.family_id:
        return jsonify({"error": "You must join or create a family first"}), 400

    data = request.get_json()

    new_location = Location(
        user_id=current_user.id,
        latitude=data["lat"],
        longitude=data["lon"],
        battery=data.get("battery"),
        speed=data.get("speed"),
        heading=data.get("heading"),
        altitude=data.get("altitude")
    )

    db.session.add(new_location)
    db.session.commit()

    socketio.emit("location_update", {
        "id": current_user.id,
        "name": current_user.username,
        "lat": new_location.latitude,
        "lon": new_location.longitude,
        "battery": new_location.battery
    }, room=f"family_{current_user.family_id}")

    check_geofences(current_user, new_location)
    check_low_battery(current_user, new_location)

    return jsonify({"message": "Location Updated"})


def check_geofences(user, location):
    """
    Part 4 — compares the new location against every geofence this
    user owns. If they've just crossed a boundary (inside <-> outside),
    emit a notification to the family room (Part 5), and if they were
    inside for 10+ minutes, record a Visit for analytics.
    """
    fences = Geofence.query.filter_by(user_id=user.id).all()

    for fence in fences:
        distance = haversine_distance(
            location.latitude, location.longitude,
            fence.latitude, fence.longitude
        )
        is_inside = distance <= fence.radius

        key = (user.id, fence.id)
        was_inside = geofence_status.get(key)
        geofence_status[key] = is_inside

        if was_inside is None:
            # First reading for this user/geofence pair — record it
            # silently so a server restart doesn't fire a false event.
            if is_inside:
                geofence_arrival_time[key] = location.timestamp
            continue

        if is_inside and not was_inside:
            geofence_arrival_time[key] = location.timestamp

            socketio.emit("geofence_event", {
                "user": user.username,
                "place": fence.name,
                "event": "arrived"
            }, room=f"family_{user.family_id}")

            create_notification(
                user,
                title=f"Arrived {fence.name}",
                message=f"{user.username} arrived at {fence.name}",
                type_="arrival"
            )

        elif not is_inside and was_inside:
            arrival = geofence_arrival_time.pop(key, None)

            if arrival:
                duration = (location.timestamp - arrival).total_seconds()

                if duration >= MIN_VISIT_SECONDS:
                    db.session.add(Visit(
                        user_id=user.id,
                        geofence_id=fence.id,
                        place_name=fence.name,
                        arrival_time=arrival,
                        departure_time=location.timestamp,
                        duration_seconds=int(duration)
                    ))
                    db.session.commit()

            socketio.emit("geofence_event", {
                "user": user.username,
                "place": fence.name,
                "event": "left"
            }, room=f"family_{user.family_id}")

            create_notification(
                user,
                title=f"Left {fence.name}",
                message=f"{user.username} left {fence.name}",
                type_="departure"
            )


@tracking_bp.route("/location", methods=["GET"])
@login_required
def get_location():
    if not current_user.family_id:
        return jsonify([])

    members = User.query.filter_by(family_id=current_user.family_id).all()
    result = []

    for member in members:
        latest = (
            Location.query
            .filter_by(user_id=member.id)
            .order_by(Location.timestamp.desc())
            .first()
        )

        if latest:
            result.append({
                "id": member.id,
                "name": member.username,
                "lat": latest.latitude,
                "lon": latest.longitude,
                "battery": latest.battery,
                "time": latest.timestamp.strftime("%H:%M:%S")
            })

    return jsonify(result)


@tracking_bp.route("/history")
@login_required
def history():
    user_id = request.args.get("user_id", type=int) or current_user.id

    member = User.query.get(user_id)
    if not member or member.family_id != current_user.family_id:
        return jsonify({"error": "Not a member of your family"}), 403

    locations = Location.query.filter_by(user_id=user_id).order_by(Location.timestamp).all()

    result = []

    for loc in locations:
        result.append({
            "lat": loc.latitude,
            "lon": loc.longitude,
            "battery": loc.battery,
            "time": loc.timestamp.strftime("%H:%M:%S")
        })

    return jsonify(result)