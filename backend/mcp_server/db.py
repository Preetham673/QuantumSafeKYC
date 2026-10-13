import os

from dotenv import load_dotenv
from flask import Flask

from models import db


load_dotenv()


def create_mcp_app():
    """
    Create a minimal Flask application for MCP database operations.
    This does not register the normal API routes.
    """

    app = Flask(__name__)

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    return app