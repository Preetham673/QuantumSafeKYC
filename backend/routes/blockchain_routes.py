from flask import Blueprint, jsonify

from models import db, Credential, BlockchainAnchor
from audit_utils import create_audit_event
from blockchain_utils import (
    create_blockchain_anchor,
    verify_credential_against_anchor,
)



blockchain_bp = Blueprint(
    "blockchain_bp",
    __name__,
    url_prefix="/api/blockchain",
)


# --------------------------------------------------
# Create Blockchain Anchor
# --------------------------------------------------

@blockchain_bp.post("/anchor/<string:credential_uuid>")
def anchor_credential(credential_uuid):
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

        # Credential must be active
        if credential.status != "ACTIVE":
            return jsonify(
                {
                    "status": "error",
                    "message": "Only ACTIVE credentials can be anchored",
                    "credential_status": credential.status,
                }
            ), 409

        # Check whether anchor already exists
        existing_anchor = BlockchainAnchor.query.filter_by(
            credential_id=credential.id
        ).first()

        if existing_anchor:
            return jsonify(
                {
                    "status": "error",
                    "message": "Credential is already anchored",
                    "anchor": {
                        "anchor_uuid": existing_anchor.anchor_uuid,
                        "transaction_id":
                            existing_anchor.transaction_id,
                        "blockchain_network":
                            existing_anchor.blockchain_network,
                        "anchor_status":
                            existing_anchor.anchor_status,
                    },
                }
            ), 409

        # Create blockchain anchor
        anchor_data = create_blockchain_anchor(
            credential.credential_hash
        )

        anchor = BlockchainAnchor(
            anchor_uuid=str(__import__("uuid").uuid4()),
            credential_id=credential.id,
            credential_hash=credential.credential_hash,
            blockchain_network=anchor_data[
                "blockchain_network"
            ],
            transaction_id=anchor_data[
                "transaction_id"
            ],
            block_number=anchor_data[
                "block_number"
            ],
            anchor_status=anchor_data[
                "anchor_status"
            ],
            anchored_at=anchor_data[
                "anchored_at"
            ],
        )

        db.session.add(anchor)
        db.session.flush()

        # Audit event
        create_audit_event(
            event_type="BLOCKCHAIN_ANCHORED",
            actor_id="SYSTEM",
            credential_id=credential.id,
            event_data=(
                f"transaction_id={anchor.transaction_id};"
                f"network={anchor.blockchain_network};"
                f"credential_hash={anchor.credential_hash}"
            ),
        )

        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "Credential anchored successfully",
                "anchor": {
                    "anchor_uuid":
                        anchor.anchor_uuid,
                    "credential_uuid":
                        credential.credential_uuid,
                    "credential_hash":
                        anchor.credential_hash,
                    "blockchain_network":
                        anchor.blockchain_network,
                    "transaction_id":
                        anchor.transaction_id,
                    "block_number":
                        anchor.block_number,
                    "anchor_status":
                        anchor.anchor_status,
                    "anchored_at":
                        anchor.anchored_at.isoformat(),
                },
            }
        ), 201

    except Exception as error:
        db.session.rollback()

        return jsonify(
            {
                "status": "error",
                "message": "Failed to anchor credential",
                "error": str(error),
            }
        ), 500


# --------------------------------------------------
# Verify Blockchain Anchor
# --------------------------------------------------

@blockchain_bp.post("/verify/<string:credential_uuid>")
def verify_blockchain_anchor_route(credential_uuid):
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

        # Find blockchain anchor
        anchor = BlockchainAnchor.query.filter_by(
            credential_id=credential.id
        ).first()


                # --------------------------------------------------
        # Revocation check
        # --------------------------------------------------

        if credential.status == "REVOKED":
            create_audit_event(
                event_type="BLOCKCHAIN_VERIFICATION_FAILED",
                actor_id="SYSTEM",
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"reason=credential_revoked;"
                    f"result=INVALID"
                ),
            )

            db.session.commit()

            return jsonify(
                {
                    "status": "success",
                    "result": "INVALID",
                    "message": "Credential is revoked",
                    "credential_uuid": credential_uuid,
                    "credential_status": credential.status,
                }
            ), 200

        if not anchor:
            return jsonify(
                {
                    "status": "success",
                    "result": "INVALID",
                    "message": "No blockchain anchor found",
                    "credential_uuid": credential_uuid,
                }
            ), 200

        # Compare credential hash with anchored hash
        is_valid = verify_credential_against_anchor(
            credential.credential_hash,
            anchor.credential_hash,
        )

        if is_valid:
            result = "VALID"
            message = "Blockchain anchor is valid"

            create_audit_event(
                event_type="BLOCKCHAIN_VERIFIED",
                actor_id="SYSTEM",
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"transaction_id={anchor.transaction_id};"
                    f"result=VALID"
                ),
            )

        else:
            result = "INVALID"
            message = "Blockchain anchor hash mismatch"

            create_audit_event(
                event_type="BLOCKCHAIN_VERIFICATION_FAILED",
                actor_id="SYSTEM",
                credential_id=credential.id,
                event_data=(
                    f"credential_uuid={credential.credential_uuid};"
                    f"transaction_id={anchor.transaction_id};"
                    f"result=INVALID"
                ),
            )

        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "result": result,
                "message": message,
                "credential_uuid": credential.credential_uuid,
                "blockchain_network":
                    anchor.blockchain_network,
                "transaction_id":
                    anchor.transaction_id,
                "anchor_status":
                    anchor.anchor_status,
            }
        ), 200

    except Exception as error:
        db.session.rollback()

        return jsonify(
            {
                "status": "error",
                "message": "Failed to verify blockchain anchor",
                "error": str(error),
            }
        ), 500