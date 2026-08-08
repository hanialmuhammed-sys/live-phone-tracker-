from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Geofence, User
from activity_service import log_activity

geofence_bp = Blueprint("geofence", __name__)


@geofence_bp.route("/geofence/add")
@login_required
def add_geofence_page():
    return render_template("add_geofence.html")


@geofence_bp.route("/geofence", methods=["POST"])
@login_required
def create_geofence():
    name = request.form["name"]
    latitude = float(request.form["latitude"])
    longitude = float(request.form["longitude"])
    radius = int(request.form["radius"])

    geofence = Geofence(
        user_id=current_user.id,
        name=name,
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )

    db.session.add(geofence)
    db.session.commit()

    log_activity(current_user.family_id, f"{current_user.username} added a geofence: {name}")

    return redirect(url_for("dashboard.dashboard"))


@geofence_bp.route("/geofence", methods=["GET"])
@login_required
def list_geofences():
    if not current_user.family_id:
        return jsonify([])

    member_ids = [
        member.id for member in
        User.query.filter_by(family_id=current_user.family_id).all()
    ]

    geofences = Geofence.query.filter(Geofence.user_id.in_(member_ids)).all()

    result = []
    for fence in geofences:
        result.append({
            "id": fence.id,
            "user_id": fence.user_id,
            "name": fence.name,
            "lat": fence.latitude,
            "lon": fence.longitude,
            "radius": fence.radius
        })

    return jsonify(result)