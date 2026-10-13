import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from routes.user_routes import user_bp
from routes.kyc_routes import kyc_bp
from routes.credential_routes import credential_bp
from routes.consent_routes import consent_bp
from routes.verification_routes import verification_bp
from routes.revocation_routes import revocation_bp
from routes.blockchain_routes import blockchain_bp
from routes.mcp_routes import mcp_bp
from flask_jwt_extended import JWTManager
from routes.auth_routes import auth_bp

from models import (
    db,
    User,
    KYCRecord,
    KYCDocument,
    Credential,
    Consent,
    Verification,
    Revocation,
    AuditEvent,
    BlockchainAnchor,
)

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()

# --------------------------------------------------
# Create Flask application
# --------------------------------------------------

app = Flask(__name__)


# --------------------------------------------------
# JWT Configuration
# --------------------------------------------------

app.config["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY",
    "CHANGE_THIS_IN_PRODUCTION",
)

jwt = JWTManager(app)

# --------------------------------------------------
# CORS Configuration
# --------------------------------------------------

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
                "http://localhost:3000",
            ]
        }
    },
)

# --------------------------------------------------
# Database Configuration
# --------------------------------------------------

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is not configured")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --------------------------------------------------
# Initialize SQLAlchemy
# --------------------------------------------------

db.init_app(app)

# --------------------------------------------------
# Initialize Flask-Migrate
# --------------------------------------------------

migrate = Migrate(app, db)

# --------------------------------------------------
# Register API Routes
# --------------------------------------------------

app.register_blueprint(user_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(kyc_bp)
app.register_blueprint(credential_bp)
app.register_blueprint(consent_bp)
app.register_blueprint(verification_bp)
app.register_blueprint(revocation_bp)
app.register_blueprint(blockchain_bp)
app.register_blueprint(mcp_bp)

# --------------------------------------------------
# API Health Check
# --------------------------------------------------

@app.get("/api/health")
def health_check():
    return jsonify(
        {
            "status": "ok",
            "service": "QuantumSafeKYC Backend",
            "phase": "Phase 1",
        }
    )


# --------------------------------------------------
# Database Health Check
# --------------------------------------------------

@app.get("/api/db-health")
def database_health_check():
    try:
        db.session.execute(db.text("SELECT 1"))

        return jsonify(
            {
                "status": "ok",
                "database": "PostgreSQL",
                "connection": "successful",
            }
        )

    except Exception as error:
        return jsonify(
            {
                "status": "error",
                "database": "PostgreSQL",
                "connection": "failed",
                "message": str(error),
            }
        ), 500


# --------------------------------------------------
# Start Flask Application
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=True,
    )