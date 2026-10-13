import uuid
from datetime import datetime, timezone
from audit_utils import create_audit_event



from flask import Blueprint, jsonify, request

from models import db, User, Credential, Consent


consent_bp = Blueprint(
    "consent_bp",
    __name__,
    url_prefix="/api/consents",
)


# --------------------------------------------------
# Grant Consent
# --------------------------------------------------

@consent_bp.post("")
def grant_consent():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is required",
            }), 400

        user_uuid = data.get("user_uuid")
        verifier_id = data.get("verifier_id")
        purpose = data.get("purpose")
        expires_at_value = data.get("expires_at")

        if not user_uuid:
            return jsonify({
                "status": "error",
                "message": "user_uuid is required",
            }), 400

        if not verifier_id:
            return jsonify({
                "status": "error",
                "message": "verifier_id is required",
            }), 400

        if not purpose:
            return jsonify({
                "status": "error",
                "message": "purpose is required",
            }), 400

        # --------------------------------------------------
        # Find User
        # --------------------------------------------------

        user = User.query.filter_by(
            user_uuid=user_uuid
        ).first()

        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found",
            }), 404

        # --------------------------------------------------
        # Find Active Credential
        # --------------------------------------------------

        credential = Credential.query.filter_by(
            user_id=user.id,
            status="ACTIVE",
        ).order_by(
            Credential.id.desc()
        ).first()

        if not credential:
            return jsonify({
                "status": "error",
                "message": "Active credential not found",
            }), 404

        # --------------------------------------------------
        # Check Existing Active Consent
        # --------------------------------------------------

        existing_consent = Consent.query.filter_by(
            user_id=user.id,
            credential_id=credential.id,
            verifier_id=verifier_id,
            status="GRANTED",
        ).first()

        if existing_consent:
            return jsonify({
                "status": "error",
                "message": "Active consent already exists",
                "consent": {
                    "consent_uuid": existing_consent.consent_uuid,
                    "status": existing_consent.status,
                },
            }), 409

        # --------------------------------------------------
        # Parse Expiry
        # --------------------------------------------------

        expires_at = None

        if expires_at_value:
            try:
                expires_at = datetime.fromisoformat(
                    expires_at_value.replace("Z", "+00:00")
                )

                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(
                        tzinfo=timezone.utc
                    )

            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid expires_at format. Use ISO-8601 format.",
                }), 400

        # --------------------------------------------------
        # Create Consent
        # --------------------------------------------------

        consent = Consent(
            consent_uuid=str(uuid.uuid4()),
            user_id=user.id,
            credential_id=credential.id,
            verifier_id=verifier_id,
            purpose=purpose,
            status="GRANTED",
            expires_at=expires_at,
        )

        db.session.add(consent)

        db.session.flush()

        create_audit_event(
        event_type="CONSENT_GRANTED",
        actor_id=user.user_uuid,
        credential_id=credential.id,
        event_data=(
        f"Consent {consent.consent_uuid} granted "
        f"to verifier {consent.verifier_id} "
        f"for purpose: {consent.purpose}"
        ),
        )







        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Consent granted successfully",
            "consent": {
                "consent_uuid": consent.consent_uuid,
                "user_uuid": user.user_uuid,
                "credential_uuid": credential.credential_uuid,
                "verifier_id": consent.verifier_id,
                "purpose": consent.purpose,
                "status": consent.status,
                "created_at": consent.created_at.isoformat(),
                "expires_at": (
                    consent.expires_at.isoformat()
                    if consent.expires_at
                    else None
                ),
            },
        }), 201

    except Exception as error:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Failed to grant consent",
            "error": str(error),
        }), 500


# --------------------------------------------------
# Get User Consents
# --------------------------------------------------

@consent_bp.get("/<string:user_uuid>")
def get_user_consents(user_uuid):
    try:
        user = User.query.filter_by(
            user_uuid=user_uuid
        ).first()

        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found",
            }), 404

        consents = Consent.query.filter_by(
            user_id=user.id
        ).order_by(
            Consent.id.desc()
        ).all()

        result = []

        for consent in consents:
            result.append({
                "consent_uuid": consent.consent_uuid,
                "credential_uuid": (
                    consent.credential.credential_uuid
                    if consent.credential
                    else None
                ),
                "verifier_id": consent.verifier_id,
                "purpose": consent.purpose,
                "status": consent.status,
                "created_at": consent.created_at.isoformat(),
                "expires_at": (
                    consent.expires_at.isoformat()
                    if consent.expires_at
                    else None
                ),
            })

        return jsonify({
            "status": "success",
            "user_uuid": user.user_uuid,
            "consents": result,
        }), 200

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve consents",
            "error": str(error),
        }), 500


# --------------------------------------------------
# Revoke Consent
# --------------------------------------------------

@consent_bp.patch("/<string:consent_uuid>/revoke")
def revoke_consent(consent_uuid):
    try:
        consent = Consent.query.filter_by(
            consent_uuid=consent_uuid
        ).first()

        if not consent:
            return jsonify({
                "status": "error",
                "message": "Consent not found",
            }), 404

        if consent.status == "REVOKED":
            return jsonify({
                "status": "error",
                "message": "Consent is already revoked",
            }), 409

        consent.status = "REVOKED"

        create_audit_event(
        event_type="CONSENT_REVOKED",
        actor_id="SYSTEM",
        credential_id=consent.credential_id,
        event_data=(
        f"Consent {consent.consent_uuid} revoked "
        f"for verifier {consent.verifier_id}"
        ),
        )


        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Consent revoked successfully",
            "consent": {
                "consent_uuid": consent.consent_uuid,
                "status": consent.status,
                "verifier_id": consent.verifier_id,
                "purpose": consent.purpose,
            },
        }), 200

    except Exception as error:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Failed to revoke consent",
            "error": str(error),
        }), 500


# --------------------------------------------------
# Check Consent
# --------------------------------------------------

@consent_bp.post("/<string:consent_uuid>/check")
def check_consent(consent_uuid):
    try:
        consent = Consent.query.filter_by(
            consent_uuid=consent_uuid
        ).first()

        if not consent:
            return jsonify({
                "status": "error",
                "message": "Consent not found",
            }), 404

        # --------------------------------------------------
        # Check Revocation
        # --------------------------------------------------

        if consent.status != "GRANTED":
            return jsonify({
                "status": "success",
                "result": "INVALID",
                "message": "Consent is not active",
                "consent_uuid": consent.consent_uuid,
                "consent_status": consent.status,
            }), 200

        # --------------------------------------------------
        # Check Expiry
        # --------------------------------------------------

        now = datetime.now(timezone.utc)

        if consent.expires_at:
            expires_at = consent.expires_at

            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(
                    tzinfo=timezone.utc
                )

            if expires_at <= now:
                return jsonify({
                    "status": "success",
                    "result": "INVALID",
                    "message": "Consent has expired",
                    "consent_uuid": consent.consent_uuid,
                    "consent_status": consent.status,
                    "expires_at": expires_at.isoformat(),
                }), 200

        return jsonify({
            "status": "success",
            "result": "VALID",
            "message": "Consent is valid",
            "consent_uuid": consent.consent_uuid,
            "verifier_id": consent.verifier_id,
            "purpose": consent.purpose,
            "consent_status": consent.status,
            "expires_at": (
                consent.expires_at.isoformat()
                if consent.expires_at
                else None
            ),
        }), 200

    except Exception as error:
        return jsonify({
            "status": "error",
            "message": "Failed to check consent",
            "error": str(error),
        }), 500