import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from models import db, Credential, Revocation
from audit_utils import create_audit_event


revocation_bp = Blueprint(
    "revocation_bp",
    __name__,
    url_prefix="/api/revocations",
)


# --------------------------------------------------
# Revoke Credential
# --------------------------------------------------

@revocation_bp.post("/<string:credential_uuid>")
def revoke_credential(credential_uuid):
    try:
        # Find credential
        credential = Credential.query.filter_by(
            credential_uuid=credential_uuid
        ).first()

        if not credential:
            return jsonify(
                {
                    "status": "error",
                    "message": "Credential not found",
                }
            ), 404

        # Credential must currently be active
        if credential.status != "ACTIVE":
            return jsonify(
                {
                    "status": "error",
                    "message": "Credential is not active",
                    "credential_status": credential.status,
                }
            ), 409

        # Request body
        data = request.get_json(silent=True) or {}

        reason = data.get(
            "reason",
            "Credential revoked",
        )

        if not reason.strip():
            return jsonify(
                {
                    "status": "error",
                    "message": "Revocation reason is required",
                }
            ), 400

        # Generate revocation UUID
        revocation_uuid = str(uuid.uuid4())

        # Create revocation record
        revocation = Revocation(
            revocation_uuid=revocation_uuid,
            credential_id=credential.id,
            reason=reason,
            status="REVOKED",
            revoked_at=datetime.now(timezone.utc),
        )

        db.session.add(revocation)

        # Update credential status
        credential.status = "REVOKED"

        # Make sure revocation ID exists
        db.session.flush()

        # Create audit event
        create_audit_event(
            event_type="CREDENTIAL_REVOKED",
            actor_id="SYSTEM",
            credential_id=credential.id,
            event_data=(
                f"Credential {credential.credential_uuid} "
                f"revoked. "
                f"Revocation {revocation.revocation_uuid}. "
                f"Reason: {reason}"
            ),
        )

        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Credential revoked successfully",
                "revocation": {
                    "revocation_uuid":
                        revocation.revocation_uuid,
                    "credential_uuid":
                        credential.credential_uuid,
                    "reason":
                        revocation.reason,
                    "status":
                        revocation.status,
                    "revoked_at":
                        revocation.revoked_at.isoformat(),
                },
            }
        ), 200

    except Exception as error:
        db.session.rollback()

        return jsonify(
            {
                "status": "error",
                "message": "Failed to revoke credential",
                "error": str(error),
            }
        ), 500


# --------------------------------------------------
# Get Revocation
# --------------------------------------------------

@revocation_bp.get("/<string:credential_uuid>")
def get_revocation(credential_uuid):
    try:
        credential = Credential.query.filter_by(
            credential_uuid=credential_uuid
        ).first()

        if not credential:
            return jsonify(
                {
                    "status": "error",
                    "message": "Credential not found",
                }
            ), 404

        revocation = Revocation.query.filter_by(
            credential_id=credential.id
        ).order_by(
            Revocation.id.desc()
        ).first()

        if not revocation:
            return jsonify(
                {
                    "status": "error",
                    "message": "Revocation record not found",
                }
            ), 404

        return jsonify(
            {
                "status": "success",
                "revocation": {
                    "revocation_uuid":
                        revocation.revocation_uuid,
                    "credential_uuid":
                        credential.credential_uuid,
                    "reason":
                        revocation.reason,
                    "status":
                        revocation.status,
                    "revoked_at":
                        revocation.revoked_at.isoformat(),
                },
            }
        ), 200

    except Exception as error:
        return jsonify(
            {
                "status": "error",
                "message": "Failed to retrieve revocation",
                "error": str(error),
            }
        ), 500