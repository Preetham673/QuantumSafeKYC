import hashlib
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify

from models import db, User, KYCRecord, Credential, Revocation
from pqc_utils import verify_credential
from audit_utils import create_audit_event
from auth_utils import require_role
from flask import Blueprint, jsonify, request
from auth_utils import decode_access_token, require_role


from pqc_utils import (
    ALGORITHM,
    sign_credential,
    encode_bytes,
)


credential_bp = Blueprint(
    "credential_bp",
    __name__,
    url_prefix="/api/credentials",
)

def get_authenticated_actor():
    """Return the active user authenticated by the Bearer token."""
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)

    if not payload:
        return None

    user_uuid = payload.get("sub")
    if not user_uuid:
        return None

    actor = User.query.filter_by(user_uuid=user_uuid).first()

    if not actor or actor.status != "ACTIVE":
        return None

    return actor
# --------------------------------------------------
# Issue KYC Credential
# --------------------------------------------------

@credential_bp.post("/<string:user_uuid>/issue")
@require_role("ISSUER", "ADMIN")
def issue_credential(user_uuid):
    try:

        actor = get_authenticated_actor()

        if not actor:
            return jsonify({
                "status": "error",
                "message": "Authenticated actor not found",
            }), 401

        # --------------------------------------------------
        # Find User
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Find KYC Record
        # --------------------------------------------------

        kyc_record = KYCRecord.query.filter_by(
            user_id=user.id
        ).first()

        if not kyc_record:
            return jsonify(
                {
                    "status": "error",
                    "message": "KYC record not found",
                }
            ), 404

        # --------------------------------------------------
        # KYC Must Be Verified
        # --------------------------------------------------

        if kyc_record.verification_status != "VERIFIED":
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "KYC must be VERIFIED before "
                        "credential issuance"
                    ),
                    "verification_status":
                        kyc_record.verification_status,
                }
            ), 409

        # --------------------------------------------------
        # Check Existing Active Credential
        # --------------------------------------------------

        existing_credential = Credential.query.filter_by(
            user_id=user.id,
            status="ACTIVE",
        ).first()

        if existing_credential:
            return jsonify(
                {
                    "status": "error",
                    "message": "Active credential already exists",
                    "credential": {
                        "credential_uuid":
                            existing_credential.credential_uuid,
                        "status":
                            existing_credential.status,
                    },
                }
            ), 409

        # --------------------------------------------------
        # Generate Credential UUID
        # --------------------------------------------------

        credential_uuid = str(uuid.uuid4())

        issued_at = datetime.now(timezone.utc)

        # --------------------------------------------------
        # Create Credential Material
        # --------------------------------------------------

        credential_material = (
            f"{credential_uuid}:"
            f"{user.user_uuid}:"
            f"{kyc_record.id}:"
            f"{issued_at.isoformat()}"
        )

        # --------------------------------------------------
        # SHA-512 Credential Hash
        # --------------------------------------------------

        credential_hash = hashlib.sha512(
            credential_material.encode("utf-8")
        ).hexdigest()

        # --------------------------------------------------
        # PQC Signing
        # --------------------------------------------------

        pqc_public_key, pqc_signature = sign_credential(
            credential_material
        )

        # --------------------------------------------------
        # Create Credential
        # --------------------------------------------------

        credential = Credential(
            credential_uuid=credential_uuid,
            user_id=user.id,
            credential_type="KYC",
            credential_hash=credential_hash,
            issuer_id="QuantumSafeKYC",
            status="ACTIVE",
            issued_at=issued_at,
            pqc_algorithm=ALGORITHM,
            pqc_public_key=pqc_public_key,
            pqc_signature=pqc_signature,
            pqc_signed_data=credential_material,
        )

       
        db.session.add(credential)

        db.session.flush()

        create_audit_event(
            event_type="CREDENTIAL_ISSUED",
            actor_id=actor.user_uuid,
            credential_id=credential.id,
            event_data=(
                f"Credential {credential.credential_uuid} "
                f"issued by {actor.user_uuid} "
                f"for user {user.user_uuid}"
            ),
        )

        db.session.commit()

        # --------------------------------------------------
        # Response
        # --------------------------------------------------

        return jsonify(
            {
                "status": "success",
                "message": (
                    "PQC-protected KYC credential "
                    "issued successfully"
                ),
                "credential": {
                    "credential_uuid":
                        credential.credential_uuid,

                    "credential_type":
                        credential.credential_type,

                    "credential_hash":
                        credential.credential_hash,

                    "issuer_id":
                        credential.issuer_id,

                    "status":
                        credential.status,

                    "issued_at":
                        credential.issued_at.isoformat(),

                    "pqc": {
                        "algorithm":
                            credential.pqc_algorithm,

                        "public_key":
                            encode_bytes(
                                credential.pqc_public_key
                            ),

                        "signature":
                            encode_bytes(
                                credential.pqc_signature
                            ),
                    },
                },
            }
        ), 201

    except Exception as error:

        db.session.rollback()

        return jsonify(
            {
                "status": "error",
                "message": "Failed to issue credential",
                "error": str(error),
            }
        ), 500


# --------------------------------------------------
# Get Credential
# --------------------------------------------------

@credential_bp.get("/<string:user_uuid>")
def get_credential(user_uuid):
    try:
        # --------------------------------------------------
        # Find User
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Find Latest Credential
        # --------------------------------------------------

        credential = Credential.query.filter_by(
            user_id=user.id
        ).order_by(
            Credential.id.desc()
        ).first()

        if not credential:
            return jsonify(
                {
                    "status": "error",
                    "message": "Credential not found",
                }
            ), 404

        # --------------------------------------------------
        # Return Credential
        # --------------------------------------------------

        return jsonify(
            {
                "status": "success",
                "credential": {
                    "credential_uuid":
                        credential.credential_uuid,

                    "credential_type":
                        credential.credential_type,

                    "credential_hash":
                        credential.credential_hash,

                    "issuer_id":
                        credential.issuer_id,

                    "status":
                        credential.status,

                    "issued_at":
                        credential.issued_at.isoformat(),

                    "expires_at":
                        (
                            credential.expires_at.isoformat()
                            if credential.expires_at
                            else None
                        ),

                    "pqc": {
                        "algorithm":
                            credential.pqc_algorithm,

                        "public_key":
                            (
                                encode_bytes(
                                    credential.pqc_public_key
                                )
                                if credential.pqc_public_key
                                else None
                            ),

                        "signature":
                            (
                                encode_bytes(
                                    credential.pqc_signature
                                )
                                if credential.pqc_signature
                                else None
                            ),
                    },
                },
            }
        ), 200

    except Exception as error:

        return jsonify(
            {
                "status": "error",
                "message": "Failed to retrieve credential",
                "error": str(error),
            }
        ), 500


# --------------------------------------------------
# Verify Credential using ML-DSA-65
# --------------------------------------------------

# --------------------------------------------------
# Verify Credential using ML-DSA-65
# --------------------------------------------------

@credential_bp.post("/verify-pqc/<string:credential_uuid>")
def verify_pqc_credential(credential_uuid):
    try:
        # --------------------------------------------------
        # Find Credential
        # --------------------------------------------------

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

        # --------------------------------------------------
        # Check PQC Data
        # --------------------------------------------------

        if (
            credential.pqc_algorithm != ALGORITHM
            or not credential.pqc_public_key
            or not credential.pqc_signature
        ):
            return jsonify(
                {
                    "status": "error",
                    "message": "PQC data not available for this credential",
                }
            ), 409

        # --------------------------------------------------
        # Find User
        # --------------------------------------------------

        user = User.query.filter_by(
            id=credential.user_id
        ).first()

        if not user:
            return jsonify(
                {
                    "status": "error",
                    "message": "Credential owner not found",
                }
            ), 404

        # --------------------------------------------------
        # Find KYC Record
        # --------------------------------------------------

        kyc_record = KYCRecord.query.filter_by(
            user_id=user.id
        ).first()

        if not kyc_record:
            return jsonify(
                {
                    "status": "error",
                    "message": "KYC record not found",
                }
            ), 404

        # --------------------------------------------------
        # Reconstruct EXACT signed material
        # --------------------------------------------------

        if not credential.pqc_signed_data:
          return jsonify(
        {
            "status": "error",
            "message": "Signed credential data is not available",
        }
        ), 409

        credential_material = credential.pqc_signed_data

        print("========== PQC DEBUG ==========")
        print("Credential UUID:", credential.credential_uuid)
        print("User UUID:", user.user_uuid)
        print("KYC ID:", kyc_record.id)
        print("Issued At:", credential.issued_at.isoformat())
        print("Credential Material:", repr(credential_material))
        print("Public Key Length:", len(credential.pqc_public_key))
        print("Signature Length:", len(credential.pqc_signature))
        print("================================")

        #--------------------------------------------------
        # Verify ML-DSA-65 Signature
        # --------------------------------------------------

        is_valid = verify_credential(
            credential_material,
            bytes(credential.pqc_public_key),
            bytes(credential.pqc_signature),
        )

        if is_valid:
          create_audit_event(
        event_type="PQC_VERIFIED",
        actor_id="SYSTEM",
        credential_id=credential.id,
        event_data=(
            f"PQC verification successful for "
            f"credential {credential.credential_uuid}"
        ),
    )
        else:
         create_audit_event(
        event_type="PQC_VERIFICATION_FAILED",
        actor_id="SYSTEM",
        credential_id=credential.id,
        event_data=(
            f"PQC verification failed for "
            f"credential {credential.credential_uuid}"
        ),
    )

        db.session.commit()

        # --------------------------------------------------
        # Verification Result
        # --------------------------------------------------

        if is_valid:
            return jsonify(
                {
                    "status": "success",
                    "result": "VALID",
                    "message": "PQC credential signature is valid",
                    "credential_uuid":
                        credential.credential_uuid,
                    "pqc_algorithm":
                        credential.pqc_algorithm,
                }
            ), 200

        return jsonify(
            {
                "status": "success",
                "result": "INVALID",
                "message": "PQC credential signature is invalid",
                "credential_uuid":
                    credential.credential_uuid,
                "pqc_algorithm":
                    credential.pqc_algorithm,
            }
        ), 200

    except Exception as error:
        return jsonify(
            {
                "status": "error",
                "message": "PQC credential verification failed",
                "error": str(error),
            }
        ), 500


# --------------------------------------------------
# Revoke Credential
# --------------------------------------------------

@credential_bp.patch("/<string:credential_uuid>/revoke")
@require_role("ISSUER", "ADMIN")
def revoke_credential(credential_uuid):
    try:
        actor = get_authenticated_actor()
        if not actor:
            return jsonify({
                "status": "error",
                "message": "Authenticated actor not found",
            }), 401

        credential = Credential.query.filter_by(
            credential_uuid=credential_uuid
        ).first()

        if not credential:
            return jsonify({
                "status": "error",
                "message": "Credential not found",
            }), 404

        if credential.status == "REVOKED":
            return jsonify({
                "status": "error",
                "message": "Credential is already revoked",
                "credential_uuid": credential.credential_uuid,
            }), 409

        data = request.get_json(silent=True) or {}
        reason = data.get("reason", f"Credential revoked by {actor.user_uuid}")

        # Revoke credential
        credential.status = "REVOKED"

        # Create revocation record
        revocation = Revocation(
            revocation_uuid=str(uuid.uuid4()),
            credential_id=credential.id,
            reason=reason,
            status="REVOKED",
            revoked_at=datetime.now(timezone.utc),
        )
        db.session.add(revocation)

        # Record authenticated actor in the audit trail
        create_audit_event(
            event_type="CREDENTIAL_REVOKED",
            actor_id=actor.user_uuid,
            credential_id=credential.id,
            event_data=(
                f"Credential {credential.credential_uuid} "
                f"revoked by {actor.user_uuid}. Reason: {reason}"
            ),
        )

        db.session.commit()
        return jsonify(
            {
                "status": "success",
                "message": "Credential revoked successfully",
                "credential": {
                    "credential_uuid":
                        credential.credential_uuid,
                    "status":
                        credential.status,
                    "pqc_algorithm":
                        credential.pqc_algorithm,
                },
                "revocation": {
                    "revocation_uuid":
                        revocation.revocation_uuid,
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
# Complete Credential Verification
# --------------------------------------------------

@credential_bp.post("/verify/<string:credential_uuid>")
def verify_credential_complete(credential_uuid):
    try:
        # Find credential
        credential = Credential.query.filter_by(
            credential_uuid=credential_uuid
        ).first()

        if not credential:
            return jsonify({
                "status": "error",
                "message": "Credential not found",
                "result": "INVALID",
            }), 404

        # --------------------------------------------------
        # 1. Check credential status
        # --------------------------------------------------

        if credential.status != "ACTIVE":
            return jsonify({
                "status": "success",
                "result": "INVALID",
                "credential_uuid": credential.credential_uuid,
                "credential_status": credential.status,
                "signature_valid": False,
                "message": "Credential is not active",
            }), 200

        # --------------------------------------------------
        # 2. Check required PQC data
        # --------------------------------------------------

        if (
            not credential.pqc_public_key
            or not credential.pqc_signature
            or not credential.pqc_signed_data
        ):
            return jsonify({
                "status": "success",
                "result": "INVALID",
                "credential_uuid": credential.credential_uuid,
                "credential_status": credential.status,
                "signature_valid": False,
                "message": "PQC verification data is incomplete",
            }), 200

        # --------------------------------------------------
        # 3. Verify ML-DSA signature
        # --------------------------------------------------

        signature_valid = verify_credential(
            credential.pqc_signed_data,
            credential.pqc_public_key,
            credential.pqc_signature,
        )

        # --------------------------------------------------
        # 4. Final result
        # --------------------------------------------------

        if not signature_valid:
            return jsonify({
                "status": "success",
                "result": "INVALID",
                "credential_uuid": credential.credential_uuid,
                "credential_status": credential.status,
                "pqc_algorithm": credential.pqc_algorithm,
                "signature_valid": False,
                "message": "PQC signature verification failed",
            }), 200

        return jsonify({
            "status": "success",
            "result": "VALID",
            "credential_uuid": credential.credential_uuid,
            "credential_status": credential.status,
            "pqc_algorithm": credential.pqc_algorithm,
            "signature_valid": True,
            "message": "Credential is valid and PQC signature is verified",
        }), 200

    except Exception as error:
        return jsonify({
            "status": "error",
            "result": "INVALID",
            "message": "Credential verification failed",
            "error": str(error),
        }), 500