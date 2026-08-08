from .auth import auth_bp
from .tracking import tracking_bp
from .family import family_bp
from .dashboard import dashboard_bp
from .geofence import geofence_bp
from .sos import sos_bp
from .analytics import analytics_bp
from .notifications import notifications_bp
from .replay import replay_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(family_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(geofence_bp)
    app.register_blueprint(sos_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(replay_bp)