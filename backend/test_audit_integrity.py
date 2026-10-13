import hashlib
import uuid
from datetime import datetime, timezone

from app import app
from models import db, AuditEvent


def calculate_hash(
    event_uuid,
    event_type,
    actor_id,
    credential_id,
    event_data,
    created_at,
):
    audit_material = (
        f"{event_uuid}:"
        f"{event_type}:"
        f"{actor_id or ''}:"
        f"{credential_id or ''}:"
        f"{event_data or ''}:"
        f"{created_at.isoformat()}"
    )

    return hashlib.sha512(
        audit_material.encode("utf-8")
    ).hexdigest()


with app.app_context():

    print("=" * 60)
    print("QuantumSafeKYC - AUDIT INTEGRITY TEST")
    print("=" * 60)

    # --------------------------------------------------
    # Create test event data
    # --------------------------------------------------

    event_uuid = str(uuid.uuid4())
    event_type = "INTEGRITY_TEST"
    actor_id = "SYSTEM"
    credential_id = 38
    event_data = "Original audit event"
    created_at = datetime.now(timezone.utc)

    # --------------------------------------------------
    # Calculate original hash
    # --------------------------------------------------

    original_hash = calculate_hash(
        event_uuid,
        event_type,
        actor_id,
        credential_id,
        event_data,
        created_at,
    )

    print("\n[1] Original audit event")
    print("Event UUID :", event_uuid)
    print("Event Type :", event_type)
    print("Actor ID   :", actor_id)
    print("Credential :", credential_id)
    print("Hash       :", original_hash)

    # --------------------------------------------------
    # Store event
    # --------------------------------------------------

    event = AuditEvent(
        event_uuid=event_uuid,
        event_type=event_type,
        actor_id=actor_id,
        credential_id=credential_id,
        event_hash=original_hash,
        created_at=created_at,
    )

    db.session.add(event)
    db.session.commit()

    print("\n[2] Audit event stored successfully")

    # --------------------------------------------------
    # Recalculate using original data
    # --------------------------------------------------

    recalculated_hash = calculate_hash(
        event_uuid,
        event_type,
        actor_id,
        credential_id,
        event_data,
        created_at,
    )

    print("\n[3] Integrity verification")

    if recalculated_hash == event.event_hash:
        print("Original event: VALID")
    else:
        print("Original event: INVALID")

    # --------------------------------------------------
    # Simulate tampering
    # --------------------------------------------------

    tampered_event_data = "TAMPERED audit event"

    tampered_hash = calculate_hash(
        event_uuid,
        event_type,
        actor_id,
        credential_id,
        tampered_event_data,
        created_at,
    )

    print("\n[4] Tamper detection")

    if tampered_hash != event.event_hash:
        print("Tampered event: INVALID")
        print("Tampering detected successfully.")
    else:
        print("Tampered event: VALID")
        print("ERROR: Tampering was not detected.")

    print("\n" + "=" * 60)

    if (
        recalculated_hash == event.event_hash
        and tampered_hash != event.event_hash
    ):
        print("AUDIT INTEGRITY TEST PASSED")
    else:
        print("AUDIT INTEGRITY TEST FAILED")

    print("=" * 60)