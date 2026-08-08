from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from models import Family, User

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def home():
    return redirect(url_for("dashboard.dashboard"))


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    if not current_user.family_id:
        return redirect(url_for("family.family_setup"))

    family = Family.query.get(current_user.family_id)
    members = User.query.filter_by(family_id=family.id).all()

    return render_template(
        "index.html",
        family=family,
        members=members,
        is_owner=(current_user.role == "owner"),
        current_role=current_user.role
    )