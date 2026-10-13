import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from models import db, Credential, Consent, Verification


verification_bp = Blueprint(
    "verification_bp",
    __name__,
    url_prefix="/api/verification",
)


# --------------------------------------------------
# Verify Credential
# --------------------------------------------------

@verification_bp.post("/credential")
def verify_credential():
    try:
        data = request.get_json(silent=True) or {}

        credential_uuid = data.get("credential_uuid")
        verifier_id = data.get("verifier_id")

        if not credential_uuid:
            return jsonify({
                "status": "error",
                "message": "credential_uuid is required",
            }), 400

        if not verifier_id:
            return jsonify({
                "status": "error",
                "message": "verifier_id is required",
            }), 400

        # Find credential
        credential = Credential.query.filter_by(
            credential_uuid=credential_uuid
        ).first()

        # Credential does not exist
        if not credential:
            return jsonify({
                "status": "success",
                "verification": {
                    "result": "INVALID",
                    "reason": "Credential not found",
                },
            }), 200

        # Credential is not active
        if credential.status != "ACTIVE":
            verification = Verification(
                verification_uuid=str(uuid.uuid4()),
                credential_id=credential.id,
                verifier_id=verifier_id,
                result="INVALID",
                verified_at=datetime.now(timezone.utc),
            )

            db.session.add(verification)
            db.session.commit()

            return jsonify({
                "status": "success",
                "verification": {
                    "result": "INVALID",
                    "reason": "Credential is not active",
                    "credential_status": credential.status,
                    "verification_uuid":
                        verification.verification_uuid,
                },
            }), 200

        # Check active consent
        consent = Consent.query.filter_by(
            credential_id=credential.id,
            verifier_id=verifier_id,
            status="GRANTED",
        ).first()

        # No active consent
        if not consent:
            verification = Verification(
                verification_uuid=str(uuid.uuid4()),
                credential_id=credential.id,
                verifier_id=verifier_id,
                result="DENIED",
                verified_at=datetime.now(timezone.utc),
            )

            db.session.add(verification)
            db.session.commit()

            return jsonify({
                "status": "success",
                "verification": {
                    "result": "DENIED",
                    "reason": "No active consent for this verifier",
                    "verification_uuid":
                        verification.verification_uuid,
                },
            }), 200

        # Credential and consent are valid
        verification = Verification(
            verification_uuid=str(uuid.uuid4()),
            credential_id=credential.id,
            verifier_id=verifier_id,
            result="VALID",
            verified_at=datetime.now(timezone.utc),
        )

        db.session.add(verification)
        db.session.commit()

        return jsonify({
            "status": "success",
            "verification": {
                "result": "VALID",
                "reason":
                    "Credential is active and consent is granted",
                "credential_uuid":
                    credential.credential_uuid,
                "credential_type":
                    credential.credential_type,
                "issuer_id":
                    credential.issuer_id,
                "verifier_id":
                    verifier_id,
                "consent_uuid":
                    consent.consent_uuid,
                "purpose":
                    consent.purpose,
                "verification_uuid":
                    verification.verification_uuid,
                "verified_at":
                    verification.verified_at.isoformat(),
            },
        }), 200

    except Exception as error:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Credential verification failed",
            "error": str(error),
        }), 500