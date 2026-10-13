from datetime import datetime, timezone

from models import (
    Credential,
    Consent,
    User,
    BlockchainAnchor,
    Revocation,
    Verification,
)

from pqc_utils import (
    verify_credential,
    ALGORITHM,
)

from blockchain_utils import (
    verify_credential_against_anchor,
)


# ==================================================
# GET USER
# ==================================================

def get_user(user_uuid: str) -> dict:

    if not user_uuid:
        return {
            "status": "error",
            "message": "user_uuid is required",
        }

    user = User.query.filter_by(
        user_uuid=user_uuid
    ).first()

    if not user:
        return {
            "status": "error",
            "message": "User not found",
            "user_uuid": user_uuid,
        }

    return {
        "status": "success",
        "user": {
            "user_uuid": str(
                user.user_uuid
            ),
            "role": user.role,
            "status": user.status,
            "created_at": (
                user.created_at.isoformat()
                if user.created_at
                else None
            ),
        },
    }


# ==================================================
# GET CREDENTIAL
# ==================================================

def get_credential(
    credential_uuid: str,
) -> dict:

    if not credential_uuid:
        return {
            "status": "error",
            "message": "credential_uuid is required",
        }

    credential = Credential.query.filter_by(
        credential_uuid=credential_uuid
    ).first()

    if not credential:
        return {
            "status": "error",
            "message": "Credential not found",
            "credential_uuid": credential_uuid,
        }

    return {
        "status": "success",
        "credential": {
            "credential_uuid": str(
                credential.credential_uuid
            ),
            "credential_type": (
                credential.credential_type
            ),
            "credential_hash": (
                credential.credential_hash
            ),
            "pqc_algorithm": (
                credential.pqc_algorithm
            ),
            "issuer_id": credential.issuer_id,
            "status": credential.status,
            "issued_at": (
                credential.issued_at.isoformat()
                if credential.issued_at
                else None
            ),
            "expires_at": (
                credential.expires_at.isoformat()
                if credential.expires_at
                else None
            ),
        },
    }


# ==================================================
# CHECK CONSENT
# ==================================================

def check_consent(
    user_uuid: str,
    credential_uuid: str,
    verifier_id: str,
    purpose: str,
) -> dict:

    if not user_uuid:
        return {
            "status": "error",
            "message": "user_uuid is required",
        }

    if not credential_uuid:
        return {
            "status": "error",
            "message": "credential_uuid is required",
        }

    if not verifier_id:
        return {
            "status": "error",
            "message": "verifier_id is required",
        }

    if not purpose:
        return {
            "status": "error",
            "message": "purpose is required",
        }

    user = User.query.filter_by(
        user_uuid=user_uuid
    ).first()

    if not user:
        return {
            "status": "error",
            "message": "User not found",
            "user_uuid": user_uuid,
        }

    credential = Credential.query.filter_by(
        credential_uuid=credential_uuid
    ).first()

    if not credential:
        return {
            "status": "error",
            "message": "Credential not found",
            "credential_uuid": credential_uuid,
        }

    # Security check:
    # Make sure the credential belongs
    # to the requested user.
    if credential.user_id != user.id:
        return {
            "status": "error",
            "message": "Credential does not belong to user",
        }

    consent = Consent.query.filter_by(
        user_id=user.id,
        credential_id=credential.id,
        verifier_id=verifier_id,
        purpose=purpose,
    ).order_by(
        Consent.created_at.desc()
    ).first()

    if not consent:
        return {
            "status": "success",
            "consent": {
                "granted": False,
                "status": "NOT_FOUND",
            },
        }

    now = datetime.now(timezone.utc)

    # Check consent status.
    if consent.status != "GRANTED":
        return {
            "status": "success",
            "consent": {
                "granted": False,
                "status": consent.status,
                "consent_uuid": str(
                    consent.consent_uuid
                ),
            },
        }

    # Check expiration.
    if consent.expires_at:

        expires_at = consent.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        if expires_at <= now:
            return {
                "status": "success",
                "consent": {
                    "granted": False,
                    "status": "EXPIRED",
                    "consent_uuid": str(
                        consent.consent_uuid
                    ),
                    "expires_at": (
                        expires_at.isoformat()
                    ),
                },
            }

    return {
        "status": "success",
        "consent": {
            "granted": True,
            "status": "GRANTED",
            "consent_uuid": str(
                consent.consent_uuid
            ),
            "verifier_id": consent.verifier_id,
            "purpose": consent.purpose,
            "created_at": (
                consent.created_at.isoformat()
                if consent.created_at
                else None
            ),
            "expires_at": (
                consent.expires_at.isoformat()
                if consent.expires_at
                else None
            ),
        },
    }


# ==================================================
# VERIFY PQC
# ==================================================

def verify_pqc(
    credential_uuid: str,
) -> dict:

    if not credential_uuid:
        return {
            "status": "error",
            "message": "credential_uuid is required",
        }

    credential = Credential.query.filter_by(
        credential_uuid=credential_uuid
    ).first()

    if not credential:
        return {
            "status": "error",
            "message": "Credential not found",
            "credential_uuid": credential_uuid,
        }

    # Credential must be active.
    if credential.status != "ACTIVE":
        return {
            "status": "success",
            "result": "INVALID",
            "credential_uuid": (
                credential.credential_uuid
            ),
            "credential_status": (
                credential.status
            ),
            "signature_valid": False,
            "message": "Credential is not active",
        }

    # Check PQC data.
    if (
        credential.pqc_algorithm != ALGORITHM
        or not credential.pqc_public_key
        or not credential.pqc_signature
        or not credential.pqc_signed_data
    ):
        return {
            "status": "success",
            "result": "INVALID",
            "credential_uuid": (
                credential.credential_uuid
            ),
            "credential_status": (
                credential.status
            ),
            "signature_valid": False,
            "message": (
                "PQC verification data is incomplete"
            ),
        }

    try:

        signature_valid = verify_credential(
            credential.pqc_signed_data,
            credential.pqc_public_key,
            credential.pqc_signature,
        )

        if signature_valid:
            return {
                "status": "success",
                "result": "VALID",
                "credential_uuid": (
                    credential.credential_uuid
                ),
                "credential_status": (
                    credential.status
                ),
                "pqc_algorithm": (
                    credential.pqc_algorithm
                ),
                "signature_valid": True,
                "message": (
                    "Credential is valid and "
                    "PQC signature is verified"
                ),
            }

        return {
            "status": "success",
            "result": "INVALID",
            "credential_uuid": (
                credential.credential_uuid
            ),
            "credential_status": (
                credential.status
            ),
            "pqc_algorithm": (
                credential.pqc_algorithm
            ),
            "signature_valid": False,
            "message": (
                "PQC signature verification failed"
            ),
        }

    except Exception as error:

        return {
            "status": "error",
            "result": "INVALID",
            "credential_uuid": (
                credential.credential_uuid
            ),
            "message": (
                "PQC credential verification failed"
            ),
            "error": str(error),
        }


# ==================================================
# VERIFY CREDENTIAL
# ==================================================

def verify_credential_complete(
    credential_uuid: str,
) -> dict:

    if not credential_uuid:
        return {
            "status": "error",
            "message": "credential_uuid is required",
        }

    credential = Credential.query.filter_by(
        credential_uuid=credential_uuid
    ).first()

    if not credential:
        return {
            "status": "error",
            "result": "INVALID",
            "message": "Credential not found",
            "credential_uuid": credential_uuid,
        }

    # Credential must be active.
    if credential.status != "ACTIVE":
        return {
            "status": "success",
            "result": "INVALID",
            "credential_uuid": str(
                credential.credential_uuid
            ),
            "credential_status": (
                credential.status
            ),
            "signature_valid": False,
            "message": "Credential is not active",
        }

    # Required PQC data must exist.
    if (
        credential.pqc_algorithm != ALGORITHM
        or not credential.pqc_public_key
        or not credential.pqc_signature
        or not credential.pqc_signed_data
    ):
        return {
            "status": "success",
            "result": "INVALID",
            "credential_uuid": str(
                credential.credential_uuid
            ),
            "credential_status": (
                credential.status
            ),
            "pqc_algorithm": (
                credential.pqc_algorithm
            ),
            "signature_valid": False,
            "message": (
                "PQC verification data is incomplete"
            ),
        }

    try:

        signature_valid = verify_credential(
            credential.pqc_signed_data,
            credential.pqc_public_key,
            credential.pqc_signature,
        )

        if signature_valid:
            return {
                "status": "success",
                "result": "VALID",
                "credential_uuid": str(
                    credential.credential_uuid
                ),
                "credential_status": (
                    credential.status
                ),
                "pqc_algorithm": (
                    credential.pqc_algorithm
                ),
                "signature_valid": True,
                "message": (
                    "Credential verification successful"
                ),
            }

        return {
            "status": "success",
            "result": "INVALID",
            "credential_uuid": str(
                credential.credential_uuid
            ),
            "credential_status": (
                credential.status
            ),
            "pqc_algorithm": (
                credential.pqc_algorithm
            ),
            "signature_valid": False,
            "message": (
                "Credential signature verification failed"
            ),
        }

    except Exception as error:

        return {
            "status": "error",
            "result": "INVALID",
            "credential_uuid": str(
                credential.credential_uuid
            ),
            "message": (
                "Credential verification failed"
            ),
            "error": str(error),
        }


# ==================================================
# CHECK REVOCATION
# ==================================================

def check_revocation(
    credential_uuid: str,
) -> dict:

    if not credential_uuid:
        return {
            "status": "error",
            "message": "credential_uuid is required",
        }

    # ----------------------------------------------
    # Find credential
    # ----------------------------------------------

    credential = Credential.query.filter_by(
        credential_uuid=credential_uuid
    ).first()

    if not credential:
        return {
            "status": "error",
            "message": "Credential not found",
            "credential_uuid": credential_uuid,
        }

    # ----------------------------------------------
    # Find latest revocation record
    # ----------------------------------------------

    revocation = Revocation.query.filter_by(
        credential_id=credential.id
    ).order_by(
        Revocation.revoked_at.desc()
    ).first()

    # ----------------------------------------------
    # No revocation record
    # ----------------------------------------------

    if not revocation:

        if credential.status == "REVOKED":
            return {
                "status": "success",
                "result": "REVOKED",
                "credential_uuid": str(
                    credential.credential_uuid
                ),
                "credential_status": (
                    credential.status
                ),
                "message": (
                    "Credential is revoked"
                ),
                "revocation_record": False,
            }

        return {
            "status": "success",
            "result": "NOT_REVOKED",
            "credential_uuid": str(
                credential.credential_uuid
            ),
            "credential_status": (
                credential.status
            ),
            "message": (
                "Credential is not revoked"
            ),
            "revocation_record": False,
        }

    # ----------------------------------------------
    # Revocation record exists
    # ----------------------------------------------

    if revocation.status == "REVOKED":
        return {
            "status": "success",
            "result": "REVOKED",
            "credential_uuid": str(
                credential.credential_uuid
            ),
            "credential_status": (
                credential.status
            ),
            "revocation_uuid": str(
                revocation.revocation_uuid
            ),
            "revocation_status": (
                revocation.status
            ),
            "reason": revocation.reason,
            "revoked_at": (
                revocation.revoked_at.isoformat()
                if revocation.revoked_at
                else None
            ),
            "message": (
                "Credential is revoked"
            ),
            "revocation_record": True,
        }

    # ----------------------------------------------
    # Revocation record exists but is not active
    # ----------------------------------------------

    return {
        "status": "success",
        "result": "NOT_REVOKED",
        "credential_uuid": str(
            credential.credential_uuid
        ),
        "credential_status": (
            credential.status
        ),
        "revocation_uuid": str(
            revocation.revocation_uuid
        ),
        "revocation_status": (
            revocation.status
        ),
        "reason": revocation.reason,
        "revoked_at": (
            revocation.revoked_at.isoformat()
            if revocation.revoked_at
            else None
        ),
        "message": (
            "No active revocation found"
        ),
        "revocation_record": True,
    }


# ==================================================
# VERIFY BLOCKCHAIN
# ==================================================

def verify_blockchain(
    credential_uuid: str,
) -> dict:

    if not credential_uuid:
        return {
            "status": "error",
            "message": "credential_uuid is required",
        }

    # Find credential.
    credential = Credential.query.filter_by(
        credential_uuid=credential_uuid
    ).first()

    if not credential:
        return {
            "status": "error",
            "message": "Credential not found",
            "credential_uuid": credential_uuid,
        }

    # Revoked credentials are invalid.
    if credential.status == "REVOKED":
        return {
            "status": "success",
            "result": "INVALID",
            "message": "Credential is revoked",
            "credential_uuid": credential_uuid,
            "credential_status": (
                credential.status
            ),
        }

    # Find blockchain anchor.
    anchor = BlockchainAnchor.query.filter_by(
        credential_id=credential.id
    ).first()

    if not anchor:
        return {
            "status": "success",
            "result": "INVALID",
            "message": "No blockchain anchor found",
            "credential_uuid": credential_uuid,
        }

    # Compare current credential hash
    # with anchored credential hash.
    is_valid = verify_credential_against_anchor(
        credential.credential_hash,
        anchor.credential_hash,
    )

    if is_valid:
        return {
            "status": "success",
            "result": "VALID",
            "message": "Blockchain anchor is valid",
            "credential_uuid": (
                credential.credential_uuid
            ),
            "blockchain_network": (
                anchor.blockchain_network
            ),
            "transaction_id": (
                anchor.transaction_id
            ),
            "anchor_status": (
                anchor.anchor_status
            ),
        }

    return {
        "status": "success",
        "result": "INVALID",
        "message": (
            "Blockchain anchor hash mismatch"
        ),
        "credential_uuid": (
            credential.credential_uuid
        ),
        "blockchain_network": (
            anchor.blockchain_network
        ),
        "transaction_id": (
            anchor.transaction_id
        ),
        "anchor_status": (
            anchor.anchor_status
        ),
    }

# ==================================================
# GET VERIFICATION HISTORY
# ==================================================

def get_verification_history(
    credential_uuid: str,
) -> dict:

    if not credential_uuid:
        return {
            "status": "error",
            "message": "credential_uuid is required",
        }

    # ----------------------------------------------
    # Find credential
    # ----------------------------------------------

    credential = Credential.query.filter_by(
        credential_uuid=credential_uuid
    ).first()

    if not credential:
        return {
            "status": "error",
            "message": "Credential not found",
            "credential_uuid": credential_uuid,
        }

    # ----------------------------------------------
    # Find verification history
    # ----------------------------------------------

    verifications = Verification.query.filter_by(
        credential_id=credential.id
    ).order_by(
        Verification.verified_at.desc()
    ).all()

    # ----------------------------------------------
    # Build history
    # ----------------------------------------------

    history = []

    for verification in verifications:

        history.append({
            "verification_uuid": str(
                verification.verification_uuid
            ),
            "verifier_id": (
                verification.verifier_id
            ),
            "result": (
                verification.result
            ),
            "verified_at": (
                verification.verified_at.isoformat()
                if verification.verified_at
                else None
            ),
        })

    # ----------------------------------------------
    # Return result
    # ----------------------------------------------

    return {
        "status": "success",
        "credential_uuid": str(
            credential.credential_uuid
        ),
        "verification_count": len(history),
        "verification_history": history,
    }