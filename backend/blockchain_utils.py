import hashlib
import uuid
from datetime import datetime, timezone


# --------------------------------------------------
# Blockchain Configuration
# --------------------------------------------------

BLOCKCHAIN_NETWORK = "QuantumSafeKYC-Local"


# --------------------------------------------------
# Create Blockchain Transaction Reference
# --------------------------------------------------

def create_transaction_id(
    credential_hash: str,
):
    """
    Create a deterministic transaction reference
    for the credential hash.

    This is a local blockchain abstraction for Phase 3.
    """

    transaction_material = (
        f"{credential_hash}:"
        f"{datetime.now(timezone.utc).isoformat()}:"
        f"{uuid.uuid4()}"
    )

    transaction_id = hashlib.sha512(
        transaction_material.encode("utf-8")
    ).hexdigest()

    return transaction_id


# --------------------------------------------------
# Create Blockchain Anchor
# --------------------------------------------------

def create_blockchain_anchor(
    credential_hash: str,
):
    """
    Create a blockchain anchor representation.

    Only the cryptographic credential hash is anchored.
    No KYC or personally identifiable information is used.
    """

    transaction_id = create_transaction_id(
        credential_hash
    )

    anchored_at = datetime.now(timezone.utc)

    return {
        "transaction_id": transaction_id,
        "blockchain_network": BLOCKCHAIN_NETWORK,
        "block_number": None,
        "anchor_status": "ANCHORED",
        "anchored_at": anchored_at,
    }


# --------------------------------------------------
# Verify Blockchain Anchor
# --------------------------------------------------

def verify_blockchain_anchor(
    current_credential_hash: str,
    anchored_credential_hash: str,
):
    """
    Verify that the current credential hash matches
    the hash stored in the blockchain anchor.
    """

    return current_credential_hash == anchored_credential_hash

# --------------------------------------------------
# Verify Credential Against Blockchain Anchor
# --------------------------------------------------

def verify_credential_against_anchor(
    current_credential_hash: str,
    anchored_credential_hash: str,
):
    """
    Compare the current credential hash with the
    hash stored in the blockchain anchor.
    """

    if not current_credential_hash:
        return False

    if not anchored_credential_hash:
        return False

    return current_credential_hash == anchored_credential_hash