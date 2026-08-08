import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-fallback-do-not-use-in-production")

    # DATABASE_URL will be set by Render once we move to PostgreSQL in 18.2.
    # Until then, this falls back to the local SQLite file so nothing breaks.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tracker4.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False