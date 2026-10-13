import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
load_dotenv()

# ==================================================
# JWT CONFIGURATION
# ==================================================

JWT_ALGORITHM = "HS256"

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not configured")


# Token lifetime
ACCESS_TOKEN_EXPIRES_MINUTES = 60


# ==================================================
# PASSWORD HASHING
# ==================================================

def hash_password(password: str) -> str:
    """
    Securely hash a user password.
    """

    if not password:
        raise ValueError("Password cannot be empty")

    return generate_password_hash(password)


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """
    Verify a plaintext password against its stored hash.
    """

    if not password or not password_hash:
        return False

    return check_password_hash(
        password_hash,
        password,
    )


# ==================================================
# CREATE JWT ACCESS TOKEN
# ==================================================

def create_access_token(
    user_uuid: str,
    role: str,
) -> str:
    """
    Create a JWT access token containing
    the user's UUID and role.
    """

    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_uuid,
        "role": role,
        "iat": now,
        "exp": now + timedelta(
            minutes=ACCESS_TOKEN_EXPIRES_MINUTES
        ),
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return token


# ==================================================
# DECODE JWT ACCESS TOKEN
# ==================================================

def decode_access_token(token: str):
    """
    Decode and validate a JWT access token.

    Returns the payload if valid.
    Returns None if invalid or expired.
    """

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        return payload

    except (
        jwt.ExpiredSignatureError,
        jwt.InvalidTokenError,
    ):
        return None


# ==================================================
# ROLE-BASED AUTHORIZATION
# ==================================================

from functools import wraps
from flask import request, jsonify


def require_role(*allowed_roles):
    """
    Require a valid Bearer token and one of the
    specified user roles.
    """

    def decorator(route_function):

        @wraps(route_function)
        def wrapper(*args, **kwargs):

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

            # Fetch the user's current role and status from the database.
            from models import User

            user = User.query.filter_by(
                user_uuid=user_uuid
            ).first()

            if not user:
                return jsonify({
                    "status": "error",
                    "message": "User not found",
                }), 401

            if user.status != "ACTIVE":
                return jsonify({
                    "status": "error",
                    "message": "User account is not active",
                }), 403

            current_role = str(user.role).upper()

            if current_role not in allowed_roles:
                return jsonify({
                    "status": "error",
                    "message": "Insufficient permissions",
                    "required_roles": list(allowed_roles),
                    "user_role": current_role,
                }), 403

            return route_function(*args, **kwargs)

        return wrapper

    return decorator
