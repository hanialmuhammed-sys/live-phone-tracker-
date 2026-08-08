import secrets
import string

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Family, User, ActivityLog
from activity_service import log_activity
from permissions import (
    OWNER, ADMIN, MEMBER,
    can_invite, can_remove_members, can_delete_family,
    can_transfer_ownership, can_change_roles
)

family_bp = Blueprint("family", __name__, url_prefix="/family")


def generate_invite_code(length=6):
    chars = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(chars) for _ in range(length))

    while Family.query.filter_by(invite_code=code).first():
        code = "".join(secrets.choice(chars) for _ in range(length))

    return code


# ---------------------------------------------------------------------
# Setup: create or join
# ---------------------------------------------------------------------

@family_bp.route("/")
@login_required
def family_setup():
    if current_user.family_id:
        return redirect(url_for("dashboard.dashboard"))

    return render_template("family_setup.html")


@family_bp.route("/create", methods=["POST"])
@login_required
def create_family():
    if current_user.family_id:
        flash("You're already in a family.")
        return redirect(url_for("dashboard.dashboard"))

    name = request.form["name"]

    family = Family(
        family_name=name,
        invite_code=generate_invite_code(),
        owner_id=current_user.id
    )
    db.session.add(family)
    db.session.commit()

    current_user.family_id = family.id
    current_user.role = OWNER
    db.session.commit()

    log_activity(family.id, f"{current_user.username} created the family")

    return redirect(url_for("dashboard.dashboard"))


@family_bp.route("/join", methods=["POST"])
@login_required
def join_family():
    if current_user.family_id:
        flash("You're already in a family.")
        return redirect(url_for("dashboard.dashboard"))

    code = request.form["invite_code"].strip().upper()
    family = Family.query.filter_by(invite_code=code).first()

    if not family:
        flash("Invalid invite code.")
        return redirect(url_for("family.family_setup"))

    current_user.family_id = family.id
    current_user.role = MEMBER
    db.session.commit()

    log_activity(family.id, f"{current_user.username} joined the family")

    return redirect(url_for("dashboard.dashboard"))


# ---------------------------------------------------------------------
# Step 5 — invite link ("https://.../invite/<code>")
# Note: because this blueprint has url_prefix="/family", the real path
# is /family/invite/<code>, not the bare /invite/<code> shown in the
# spec's mockup. Functionally identical, just nested under /family.
# ---------------------------------------------------------------------

@family_bp.route("/invite/<code>")
@login_required
def invite_link(code):
    family = Family.query.filter_by(invite_code=code.strip().upper()).first()

    if not family:
        flash("That invite link is invalid or has expired.")
        return redirect(url_for("family.family_setup"))

    if current_user.family_id:
        flash("You're already in a family — leave it first to join another.")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("invite_confirm.html", family=family, code=code.strip().upper())


# ---------------------------------------------------------------------
# Leave / remove
# ---------------------------------------------------------------------

@family_bp.route("/leave", methods=["POST"])
@login_required
def leave_family():
    if current_user.role == OWNER:
        flash("Family owners must delete or transfer the family instead of leaving.")
        return redirect(url_for("dashboard.dashboard"))

    family_id = current_user.family_id
    username = current_user.username

    current_user.family_id = None
    current_user.role = MEMBER
    db.session.commit()

    log_activity(family_id, f"{username} left the family")

    return redirect(url_for("family.family_setup"))


@family_bp.route("/remove/<int:user_id>", methods=["POST"])
@login_required
def remove_member(user_id):
    family = Family.query.get(current_user.family_id)

    if not family or not can_remove_members(current_user):
        flash("You don't have permission to remove members.")
        return redirect(url_for("dashboard.dashboard"))

    member = User.query.get(user_id)

    if not member or member.family_id != family.id:
        return redirect(url_for("dashboard.dashboard"))

    if member.role == OWNER:
        flash("The owner can't be removed — transfer ownership first.")
        return redirect(url_for("dashboard.dashboard"))

    if member.id == current_user.id:
        flash("Use \"Leave Family\" to remove yourself.")
        return redirect(url_for("dashboard.dashboard"))

    member.family_id = None
    member.role = MEMBER
    db.session.commit()

    log_activity(family.id, f"{member.username} was removed by {current_user.username}")

    return redirect(url_for("dashboard.dashboard"))


# ---------------------------------------------------------------------
# Step 7 — promote / demote
# ---------------------------------------------------------------------

@family_bp.route("/promote/<int:user_id>", methods=["POST"])
@login_required
def promote_member(user_id):
    family = Family.query.get(current_user.family_id)

    if not family or not can_change_roles(current_user):
        flash("Only the owner can change roles.")
        return redirect(url_for("dashboard.dashboard"))

    member = User.query.get(user_id)

    if not member or member.family_id != family.id or member.role != MEMBER:
        return redirect(url_for("dashboard.dashboard"))

    member.role = ADMIN
    db.session.commit()

    log_activity(family.id, f"{member.username} promoted to Admin")

    return redirect(url_for("dashboard.dashboard"))


@family_bp.route("/demote/<int:user_id>", methods=["POST"])
@login_required
def demote_member(user_id):
    family = Family.query.get(current_user.family_id)

    if not family or not can_change_roles(current_user):
        flash("Only the owner can change roles.")
        return redirect(url_for("dashboard.dashboard"))

    member = User.query.get(user_id)

    if not member or member.family_id != family.id or member.role != ADMIN:
        return redirect(url_for("dashboard.dashboard"))

    member.role = MEMBER
    db.session.commit()

    log_activity(family.id, f"{member.username} demoted to Member")

    return redirect(url_for("dashboard.dashboard"))


# ---------------------------------------------------------------------
# Step 8 — transfer ownership
# ---------------------------------------------------------------------

@family_bp.route("/transfer/<int:user_id>", methods=["POST"])
@login_required
def transfer_ownership(user_id):
    family = Family.query.get(current_user.family_id)

    if not family or not can_transfer_ownership(current_user):
        flash("Only the owner can transfer ownership.")
        return redirect(url_for("dashboard.dashboard"))

    new_owner = User.query.get(user_id)

    if not new_owner or new_owner.family_id != family.id or new_owner.id == current_user.id:
        flash("Choose another family member to transfer ownership to.")
        return redirect(url_for("dashboard.dashboard"))

    new_owner.role = OWNER
    current_user.role = ADMIN  # old owner becomes Admin, per Step 8
    family.owner_id = new_owner.id
    db.session.commit()

    log_activity(family.id, f"{current_user.username} transferred ownership to {new_owner.username}")

    return redirect(url_for("dashboard.dashboard"))


# ---------------------------------------------------------------------
# Rename / regenerate code / delete
# ---------------------------------------------------------------------

@family_bp.route("/rename", methods=["POST"])
@login_required
def rename_family():
    family = Family.query.get(current_user.family_id)

    if not family or not can_delete_family(current_user):  # owner-only, same tier as delete
        flash("Only the owner can rename the family.")
        return redirect(url_for("dashboard.dashboard"))

    old_name = family.family_name
    family.family_name = request.form["name"]
    db.session.commit()

    log_activity(family.id, f"Family renamed from \"{old_name}\" to \"{family.family_name}\"")

    return redirect(url_for("dashboard.dashboard"))


@family_bp.route("/regenerate-code", methods=["POST"])
@login_required
def regenerate_invite_code():
    family = Family.query.get(current_user.family_id)

    if not family or not can_invite(current_user):
        flash("You don't have permission to do that.")
        return redirect(url_for("dashboard.dashboard"))

    family.invite_code = generate_invite_code()
    db.session.commit()

    log_activity(family.id, f"{current_user.username} generated a new invite code")

    return redirect(url_for("family.manage"))


@family_bp.route("/delete", methods=["POST"])
@login_required
def delete_family():
    family = Family.query.get(current_user.family_id)

    if not family or not can_delete_family(current_user):
        flash("Only the family owner can delete the family.")
        return redirect(url_for("dashboard.dashboard"))

    User.query.filter_by(family_id=family.id).update({"family_id": None, "role": MEMBER})
    ActivityLog.query.filter_by(family_id=family.id).delete()
    db.session.delete(family)
    db.session.commit()

    return redirect(url_for("family.family_setup"))


# ---------------------------------------------------------------------
# Step 3/4/10 — management + settings page
# ---------------------------------------------------------------------

@family_bp.route("/manage")
@login_required
def manage():
    family = Family.query.get(current_user.family_id)

    if not family:
        return redirect(url_for("family.family_setup"))

    members = User.query.filter_by(family_id=family.id).order_by(
        db.case((User.role == OWNER, 0), (User.role == ADMIN, 1), else_=2),
        User.username
    ).all()

    activity = (
        ActivityLog.query
        .filter_by(family_id=family.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(50)
        .all()
    )

    return render_template(
        "family_manage.html",
        family=family,
        members=members,
        activity=activity,
        can_invite=can_invite(current_user),
        can_remove=can_remove_members(current_user),
        can_change_roles=can_change_roles(current_user),
        can_transfer=can_transfer_ownership(current_user),
        can_delete=can_delete_family(current_user)
    )


# ---------------------------------------------------------------------
# Step 12 — member profile (JSON, used by a small modal in the UI)
# ---------------------------------------------------------------------

@family_bp.route("/member/<int:user_id>/profile")
@login_required
def member_profile(user_id):
    member = User.query.get(user_id)

    if not member or member.family_id != current_user.family_id:
        return jsonify({"error": "Not a member of your family"}), 403

    from models import Location, Geofence
    from utils import haversine_distance
    from routes.analytics import compute_daily_stats

    last_location = (
        Location.query
        .filter_by(user_id=member.id)
        .order_by(Location.timestamp.desc())
        .first()
    )

    current_place = None
    if last_location:
        fences = Geofence.query.filter_by(user_id=member.id).all()
        for fence in fences:
            distance = haversine_distance(
                last_location.latitude, last_location.longitude,
                fence.latitude, fence.longitude
            )
            if distance <= fence.radius:
                current_place = fence.name
                break

    stats = compute_daily_stats(member.id)

    return jsonify({
        "username": member.username,
        "role": member.role,
        "battery": last_location.battery if last_location else None,
        "last_seen": last_location.timestamp.isoformat() if last_location else None,
        "distance_today": stats["distance"],
        "average_speed": stats["average_speed"],
        "current_place": current_place
    })