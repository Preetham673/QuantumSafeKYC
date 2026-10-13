import hashlib
import uuid
from datetime import datetime, timezone

from models import db, AuditEvent


def create_audit_event(
    event_type,
    actor_id=None,
    credential_id=None,
    event_data=None,
):
    """
    Create and store an immutable-style audit event.

    event_data should contain the important information
    associated with the event.
    """

    event_uuid = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    # --------------------------------------------------
    # Create deterministic audit material
    # --------------------------------------------------

    audit_material = (
        f"{event_uuid}:"
        f"{event_type}:"
        f"{actor_id or ''}:"
        f"{credential_id or ''}:"
        f"{event_data or ''}:"
        f"{created_at.isoformat()}"
    )

    # --------------------------------------------------
    # SHA-512 event hash
    # --------------------------------------------------

    event_hash = hashlib.sha512(
        audit_material.encode("utf-8")
    ).hexdigest()

    # --------------------------------------------------
    # Store audit event
    # --------------------------------------------------

    audit_event = AuditEvent(
        event_uuid=event_uuid,
        event_type=event_type,
        actor_id=actor_id,
        credential_id=credential_id,
        event_hash=event_hash,
        created_at=created_at,
    )

    db.session.add(audit_event)

    return audit_event

