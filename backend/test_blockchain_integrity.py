from app import app
from models import Credential, BlockchainAnchor
from blockchain_utils import verify_credential_against_anchor


CREDENTIAL_UUID = "b7910bb9-c906-4195-8a99-72046142aaca"


with app.app_context():

    print("=" * 60)
    print("QuantumSafeKYC - BLOCKCHAIN INTEGRITY TEST")
    print("=" * 60)

    # --------------------------------------------------
    # Load credential
    # --------------------------------------------------

    credential = Credential.query.filter_by(
        credential_uuid=CREDENTIAL_UUID
    ).first()

    if not credential:
        print("ERROR: Credential not found")
        raise SystemExit(1)

    # --------------------------------------------------
    # Load blockchain anchor
    # --------------------------------------------------

    anchor = BlockchainAnchor.query.filter_by(
        credential_id=credential.id
    ).first()

    if not anchor:
        print("ERROR: Blockchain anchor not found")
        raise SystemExit(1)

    print()
    print("[1] Original credential")

    print("Credential UUID :", credential.credential_uuid)
    print("Credential ID   :", credential.id)
    print("Credential Hash :", credential.credential_hash)

    print()
    print("[2] Blockchain anchor")

    print("Anchor UUID     :", anchor.anchor_uuid)
    print("Transaction ID  :", anchor.transaction_id)
    print("Anchor Hash     :", anchor.credential_hash)

    # --------------------------------------------------
    # Original verification
    # --------------------------------------------------

    original_result = verify_credential_against_anchor(
        credential.credential_hash,
        anchor.credential_hash,
    )

    print()
    print("[3] Original integrity verification")

    if original_result:
        print("Original credential: VALID")
    else:
        print("Original credential: INVALID")
        raise SystemExit(1)

    # --------------------------------------------------
    # Controlled tampering
    # --------------------------------------------------

    tampered_hash = "TAMPERED_" + credential.credential_hash

    tampered_result = verify_credential_against_anchor(
        tampered_hash,
        anchor.credential_hash,
    )

    print()
    print("[4] Tamper detection")

    if not tampered_result:
        print("Tampered credential: INVALID")
        print("Tampering detected successfully.")
    else:
        print("ERROR: Tampering was NOT detected")
        raise SystemExit(1)

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    print()
    print("=" * 60)
    print("BLOCKCHAIN INTEGRITY TEST PASSED")
    print("=" * 60)