from flask import Flask
from dotenv import load_dotenv

load_dotenv()  # reads .env into os.environ — must happen before Config is imported/used

from config import Config  # noqa: E402
from extensions import db, bcrypt, login_manager, socketio  # noqa: E402
from routes import register_blueprints  # noqa: E402
import models  # noqa: E402,F401 - imported so SQLAlchemy registers the model tables


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    socketio.init_app(app)

    register_blueprints(app)

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True)
