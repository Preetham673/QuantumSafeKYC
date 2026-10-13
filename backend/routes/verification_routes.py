import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from models import (
    db,
    Credential,
    Consent,
    Verification,
    BlockchainAnchor,
)

from pqc_utils import verify_credential

from blockchain_utils import (
    verify_credential_against_anchor,
)

from audit_utils import create_audit_event


verification_bp = Blueprint(
    "verification_bp",
    __name__,
    url_prefix="/api/verification",
)


# --------------------------------------------------
# Unified Credential Verification - Phase 4
# --------------------------------------------------

@verification_bp.post("/credential")
def verify_credential_unified():
    try:
        data = request.get_json(silent=True) or {}

        credential_uuid = data.get("credential_uuid")
        verifier_id = data.get("verifier_id")

        # --------------------------------------------------
        # 1. Validate request
        # --------------------------------------------------

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

        # --------------------------------------------------
        # 2. Find credential
        # --------------------------------------------------

        credential = Credential.query.filter_by(
            credential_uuid=credential_uuid
        ).first()

        if not credential:
            return jsonify({
                "status": "success",
                "verification": {
                    "result": "INVALID",
                    "reason": "Credential not found",
                },
            }), 200

        # --------------------------------------------------
        # 3. Check credential status
        # --------------------------------------------------

        if credential.status != "ACTIVE":

            verification = Verification(
                verification_uuid=str(uuid.uuid4()),
                credential_id=credential.id,
                verifier_id=verifier_id,
                result="INVALID",
                verified_at=datetime.now(timezone.utc),
            )

            db.session.add(verification)

            create_audit_event(
                event_type="VERIFICATION_FAILED",
                actor_id=verifier_id,
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"reason=credential_status;"
                    f"credential_status={credential.status}"
                ),
            )

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

        # --------------------------------------------------
        # 4. Check credential expiration
        # --------------------------------------------------

        now = datetime.now(timezone.utc)

        if (
            credential.expires_at is not None
            and credential.expires_at <= now
        ):

            verification = Verification(
                verification_uuid=str(uuid.uuid4()),
                credential_id=credential.id,
                verifier_id=verifier_id,
                result="INVALID",
                verified_at=now,
            )

            db.session.add(verification)

            create_audit_event(
                event_type="VERIFICATION_FAILED",
                actor_id=verifier_id,
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"reason=credential_expired"
                ),
            )

            db.session.commit()

            return jsonify({
                "status": "success",
                "verification": {
                    "result": "INVALID",
                    "reason": "Credential has expired",
                    "verification_uuid":
                        verification.verification_uuid,
                },
            }), 200

        # --------------------------------------------------
        # 5. Verify PQC signature
        # --------------------------------------------------

        pqc_valid = False

        if (
            credential.pqc_signed_data
            and credential.pqc_public_key
            and credential.pqc_signature
        ):
            pqc_valid = verify_credential(
                credential.pqc_signed_data,
                credential.pqc_public_key,
                credential.pqc_signature,
            )

        if not pqc_valid:

            verification = Verification(
                verification_uuid=str(uuid.uuid4()),
                credential_id=credential.id,
                verifier_id=verifier_id,
                result="INVALID",
                verified_at=now,
            )

            db.session.add(verification)

            create_audit_event(
                event_type="VERIFICATION_FAILED",
                actor_id=verifier_id,
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"reason=pqc_signature_invalid"
                ),
            )

            db.session.commit()

            return jsonify({
                "status": "success",
                "verification": {
                    "result": "INVALID",
                    "reason": "PQC signature is invalid",
                    "pqc_algorithm":
                        credential.pqc_algorithm,
                    "verification_uuid":
                        verification.verification_uuid,
                },
            }), 200

        # --------------------------------------------------
        # 6. Check active consent
        # --------------------------------------------------

        consent = Consent.query.filter_by(
            credential_id=credential.id,
            verifier_id=verifier_id,
            status="GRANTED",
        ).first()

        if not consent:

            verification = Verification(
                verification_uuid=str(uuid.uuid4()),
                credential_id=credential.id,
                verifier_id=verifier_id,
                result="DENIED",
                verified_at=now,
            )

            db.session.add(verification)

            create_audit_event(
                event_type="VERIFICATION_DENIED",
                actor_id=verifier_id,
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"reason=no_active_consent"
                ),
            )

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

        # --------------------------------------------------
        # 7. Check consent expiration
        # --------------------------------------------------

        if (
            consent.expires_at is not None
            and consent.expires_at <= now
        ):

            verification = Verification(
                verification_uuid=str(uuid.uuid4()),
                credential_id=credential.id,
                verifier_id=verifier_id,
                result="DENIED",
                verified_at=now,
            )

            db.session.add(verification)

            create_audit_event(
                event_type="VERIFICATION_DENIED",
                actor_id=verifier_id,
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"reason=consent_expired;"
                    f"consent_uuid={consent.consent_uuid}"
                ),
            )

            db.session.commit()

            return jsonify({
                "status": "success",
                "verification": {
                    "result": "DENIED",
                    "reason": "Consent has expired",
                    "consent_uuid":
                        consent.consent_uuid,
                    "verification_uuid":
                        verification.verification_uuid,
                },
            }), 200

        # --------------------------------------------------
        # 8. Find blockchain anchor
        # --------------------------------------------------

        anchor = BlockchainAnchor.query.filter_by(
            credential_id=credential.id
        ).first()

        if not anchor:

            verification = Verification(
                verification_uuid=str(uuid.uuid4()),
                credential_id=credential.id,
                verifier_id=verifier_id,
                result="INVALID",
                verified_at=now,
            )

            db.session.add(verification)

            create_audit_event(
                event_type="VERIFICATION_FAILED",
                actor_id=verifier_id,
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"reason=no_blockchain_anchor"
                ),
            )

            db.session.commit()

            return jsonify({
                "status": "success",
                "verification": {
                    "result": "INVALID",
                    "reason": "No blockchain anchor found",
                    "verification_uuid":
                        verification.verification_uuid,
                },
            }), 200

        # --------------------------------------------------
        # 9. Verify blockchain hash
        # --------------------------------------------------

        blockchain_valid = verify_credential_against_anchor(
            credential.credential_hash,
            anchor.credential_hash,
        )

        if not blockchain_valid:

            verification = Verification(
                verification_uuid=str(uuid.uuid4()),
                credential_id=credential.id,
                verifier_id=verifier_id,
                result="INVALID",
                verified_at=now,
            )

            db.session.add(verification)

            create_audit_event(
                event_type="VERIFICATION_FAILED",
                actor_id=verifier_id,
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"reason=blockchain_hash_mismatch;"
                    f"transaction_id={anchor.transaction_id}"
                ),
            )

            db.session.commit()

            return jsonify({
                "status": "success",
                "verification": {
                    "result": "INVALID",
                    "reason": "Blockchain anchor hash mismatch",
                    "verification_uuid":
                        verification.verification_uuid,
                },
            }), 200

        # --------------------------------------------------
        # 10. All security checks passed
        # --------------------------------------------------

        verification = Verification(
            verification_uuid=str(uuid.uuid4()),
            credential_id=credential.id,
            verifier_id=verifier_id,
            result="VALID",
            verified_at=now,
        )

        db.session.add(verification)

        create_audit_event(
            event_type="VERIFICATION_SUCCESS",
            actor_id=verifier_id,
            credential_id=credential.id,
            event_data=(
                f"credential_uuid={credential.credential_uuid};"
                f"pqc_algorithm={credential.pqc_algorithm};"
                f"consent_uuid={consent.consent_uuid};"
                f"anchor_uuid={anchor.anchor_uuid};"
                f"transaction_id={anchor.transaction_id};"
                f"result=VALID"
            ),
        )

        db.session.commit()

        return jsonify({
            "status": "success",
            "verification": {
                "result": "VALID",
                "reason": (
                    "Credential passed all verification checks"
                ),
                "credential_uuid":
                    credential.credential_uuid,
                "credential_type":
                    credential.credential_type,
                "issuer_id":
                    credential.issuer_id,
                "verifier_id":
                    verifier_id,
                "pqc": {
                    "algorithm":
                        credential.pqc_algorithm,
                    "result": "VALID",
                },
                "consent": {
                    "result": "VALID",
                    "consent_uuid":
                        consent.consent_uuid,
                    "purpose":
                        consent.purpose,
                },
                "blockchain": {
                    "result": "VALID",
                    "anchor_uuid":
                        anchor.anchor_uuid,
                    "network":
                        anchor.blockchain_network,
                    "transaction_id":
                        anchor.transaction_id,
                },
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
            "message": "Unified credential verification failed",
            "error": str(error),
        }), 500