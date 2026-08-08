from extensions import db, socketio
from models import ActivityLog


def log_activity(family_id, message):
    if not family_id:
        return None

    entry = ActivityLog(family_id=family_id, message=message)
    db.session.add(entry)
    db.session.commit()

    socketio.emit("activity_log", {
        "id": entry.id,
        "message": entry.message,
        "created_at": entry.created_at.isoformat()
    }, room=f"family_{family_id}")

    return entry