import uuid

from flask import Blueprint, jsonify, request

from models import db, User
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    require_role,
)


auth_bp = Blueprint(
    "auth_bp",
    __name__,
    url_prefix="/api/auth",
)


# ==================================================
# REGISTER
# ==================================================

@auth_bp.post("/register")
def register():
    try:
        data = request.get_json(silent=True) or {}

        password = data.get("password")
        requested_role = str(data.get("role", "HOLDER")).upper()

        if requested_role != "HOLDER":
            return jsonify({
                "status": "error",
                "message": "Public registration is restricted to the HOLDER role",
            }), 403

        role = "HOLDER"

        user_uuid = str(uuid.uuid4())

        password_hash = hash_password(password)

        user = User(
            user_uuid=user_uuid,
            password_hash=password_hash,
            role=role,
            status="ACTIVE",
        )

        db.session.add(user)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "User registered successfully",
            "user": {
                "id": user.id,
                "user_uuid": user.user_uuid,
                "role": user.role,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
            },
        }), 201

    except Exception as error:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "User registration failed",
            "error": str(error),
        }), 500


# ==================================================
# LOGIN
# ==================================================

@auth_bp.post("/login")
def login():
    try:
        data = request.get_json(silent=True) or {}

        user_uuid = data.get("user_uuid")
        password = data.get("password")

        if not user_uuid:
            return jsonify({
                "status": "error",
                "message": "user_uuid is required",
            }), 400

        if not password:
            return jsonify({
                "status": "error",
                "message": "password is required",
            }), 400

        user = User.query.filter_by(
            user_uuid=user_uuid
        ).first()

        if not user:
            return jsonify({
                "status": "error",
                "message": "Invalid credentials",
            }), 401

        if user.status != "ACTIVE":
            return jsonify({
                "status": "error",
                "message": "User account is not active",
            }), 403

        if not user.password_hash:
            return jsonify({
                "status": "error",
                "message": "User does not have authentication credentials",
            }), 401

        if not verify_password(
            password,
            user.password_hash,
        ):
            return jsonify({
                "status": "error",
                "message": "Invalid credentials",
            }), 401

        token = create_access_token(
            user.user_uuid,
            user.role,
        )

        return jsonify({
            "status": "success",
            "message": "Login successful",
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "user": {
                "id": user.id,
                "user_uuid": user.user_uuid,
                "role": user.role,
                "status": user.status,
            },
        }), 200

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": "Login failed",
            "error": str(error),
        }), 500


# ==================================================
# AUTHENTICATED USER
# ==================================================

@auth_bp.get("/me")
def get_current_user():
    try:
        authorization = request.headers.get(
            "Authorization",
            "",
        )

        if not authorization.startswith("Bearer "):
            return jsonify({
                "status": "error",
                "message": "Bearer token is required",
            }), 401

        token = authorization.split(
            " ",
            1,
        )[1].strip()

        payload = decode_access_token(token)

        if not payload:
            return jsonify({
                "status": "error",
                "message": "Invalid or expired token",
            }), 401

        user_uuid = payload.get("sub")

        if not user_uuid:
            return jsonify({
                "status": "error",
                "message": "Invalid token payload",
            }), 401

        user = User.query.filter_by(
            user_uuid=user_uuid
        ).first()

        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found",
            }), 404

        if user.status != "ACTIVE":
            return jsonify({
                "status": "error",
                "message": "User account is not active",
            }), 403

        return jsonify({
            "status": "success",
            "user": {
                "id": user.id,
                "user_uuid": user.user_uuid,
                "role": user.role,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
            },
        }), 200

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve authenticated user",
            "error": str(error),
        }), 500


# ==================================================
# ROLE AUTHORIZATION TEST
# ==================================================

@auth_bp.get("/admin-test")
@require_role("ADMIN")
def admin_test():
    return jsonify({
        "status": "success",
        "message": "Admin authorization successful",
    }), 200
