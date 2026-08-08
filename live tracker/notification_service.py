from extensions import db, socketio
from models import Notification


def create_notification(user, title, message, type_):
    """
    Creates a Notification row and, if the user is in a family, emits
    it live to that family's socket room (Step 2 + Step 7).
    Called from wherever an event happens: geofence crossings, low
    battery, SOS, going offline, etc. — so notification creation
    always goes through one place instead of being duplicated per event.
    """
    if not user.family_id:
        return None

    notification = Notification(
        user_id=user.id,
        family_id=user.family_id,
        title=title,
        message=message,
        type=type_
    )

    db.session.add(notification)
    db.session.commit()

    socketio.emit("notification", {
        "id": notification.id,
        "user": user.username,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat()
    }, room=f"family_{user.family_id}")

    return notification