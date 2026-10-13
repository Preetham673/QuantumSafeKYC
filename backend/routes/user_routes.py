import uuid

from flask import Blueprint, jsonify

from models import db, User


user_bp = Blueprint(
    "user_bp",
    __name__,
    url_prefix="/api/users",
)


# --------------------------------------------------
# Create User
# --------------------------------------------------

@user_bp.post("")
def create_user():
    try:
        user_uuid = str(uuid.uuid4())

        user = User(
            user_uuid=user_uuid,
            status="ACTIVE",
        )

        db.session.add(user)
        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "User created successfully",
                "user": {
                    "id": user.id,
                    "user_uuid": user.user_uuid,
                    "status": user.status,
                    "created_at": user.created_at.isoformat(),
                },
            }
        ), 201

    except Exception as error:
        db.session.rollback()

        return jsonify(
            {
                "status": "error",
                "message": "Failed to create user",
                "error": str(error),
            }
        ), 500


# --------------------------------------------------
# Get User
# --------------------------------------------------

@user_bp.get("/<string:user_uuid>")
def get_user(user_uuid):
    try:
        user = User.query.filter_by(
            user_uuid=user_uuid
        ).first()

        if not user:
            return jsonify(
                {
                    "status": "error",
                    "message": "User not found",
                }
            ), 404

        return jsonify(
            {
                "status": "success",
                "user": {
                    "id": user.id,
                    "user_uuid": user.user_uuid,
                    "status": user.status,
                    "created_at": user.created_at.isoformat(),
                },
            }
        ), 200

    except Exception as error:
        return jsonify(
            {
                "status": "error",
                "message": "Failed to retrieve user",
                "error": str(error),
            }
        ), 500