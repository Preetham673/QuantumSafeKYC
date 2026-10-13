import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, send_file
from audit_utils import create_audit_event
from auth_utils import decode_access_token, require_role
from models import db, User, KYCRecord, KYCDocument
from storage_utils import save_kyc_document

kyc_bp = Blueprint(
    "kyc_bp",
    __name__,
    url_prefix="/api/kyc",
)

VERIFICATION_DISCLAIMER = (
    "VERIFIED status indicates an authorized issuer reviewed and approved the submitted "
    "identity evidence according to the configured review procedure. QuantumSafeKYC verifies "
    "cryptographic signatures and file integrity; physical document authenticity is not "
    "independently certified against external government databases."
)


def get_authenticated_actor():
    """Extract and validate the active user authenticated by the Bearer token."""
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


def serialize_document(doc: KYCDocument) -> dict:
    """Format a KYCDocument metadata dictionary for client consumption."""
    return {
        "id": doc.id,
        "document_type": doc.document_type,
        "file_name": doc.file_name,
        "file_size": doc.file_size,
        "mime_type": doc.mime_type,
        "file_hash": doc.file_hash,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


def serialize_kyc_record(kyc: KYCRecord, include_documents: bool = True) -> dict:
    """Format a KYCRecord with identity fields, review metadata, and documents."""
    user = kyc.user
    reviewer = kyc.reviewer

    data = {
        "id": kyc.id,
        "user_uuid": user.user_uuid if user else None,
        "verification_status": kyc.verification_status,
        "verification_level": kyc.verification_level,
        "full_name": kyc.full_name,
        "date_of_birth": kyc.date_of_birth,
        "nationality": kyc.nationality,
        "document_type": kyc.document_type,
        "document_number": kyc.document_number,
        "residential_address": kyc.residential_address,
        "country_of_issue": kyc.country_of_issue,
        "expiry_date": kyc.expiry_date,
        "submitted_at": kyc.submitted_at.isoformat() if kyc.submitted_at else None,
        "reviewed_at": kyc.reviewed_at.isoformat() if kyc.reviewed_at else None,
        "reviewed_by": reviewer.user_uuid if reviewer else None,
        "rejection_reason": kyc.rejection_reason,
        "review_notes": kyc.review_notes,
        "verified_at": kyc.verified_at.isoformat() if kyc.verified_at else None,
        "created_at": kyc.created_at.isoformat() if kyc.created_at else None,
        "verification_notice": VERIFICATION_DISCLAIMER,
    }

    if include_documents:
        data["documents"] = [serialize_document(d) for d in kyc.documents]
        data["documents_count"] = len(kyc.documents)

    return data


# ==================================================
# 1. HOLDER: Get Own KYC Status & Details
# ==================================================

@kyc_bp.get("/me")
@kyc_bp.get("/my-status")
@require_role("HOLDER")
def get_my_kyc_status():
    """Retrieve the authenticated holder's current KYC submission status."""
    actor = get_authenticated_actor()
    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    kyc = KYCRecord.query.filter_by(user_id=actor.id).first()
    if not kyc:
        return jsonify({
            "status": "success",
            "has_record": False,
            "kyc": {
                "user_uuid": actor.user_uuid,
                "verification_status": "NOT_SUBMITTED",
                "verification_level": None,
                "documents": [],
            },
        }), 200

    return jsonify({
        "status": "success",
        "has_record": True,
        "kyc": serialize_kyc_record(kyc, include_documents=True),
    }), 200


# ==================================================
# 2. HOLDER: Submit or Resubmit KYC Application
# ==================================================

@kyc_bp.post("/submit")
@kyc_bp.post("")
@require_role("HOLDER")
def submit_kyc_application():
    """
    Submit or resubmit a KYC application with identity details and document uploads.
    Accepts multipart/form-data (with file uploads) or application/json.
    """
    actor = get_authenticated_actor()
    if not actor:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        # Determine content source (multipart or JSON)
        is_multipart = request.content_type and "multipart/form-data" in request.content_type
        if is_multipart:
            data = request.form.to_dict()
        else:
            data = request.get_json(silent=True) or {}

        target_uuid = data.get("user_uuid") or actor.user_uuid
        # Prevent IDOR: HOLDER can only submit for themselves
        if target_uuid != actor.user_uuid:
            return jsonify({
                "status": "error",
                "message": "Holders may only submit KYC applications for their own identity",
            }), 403

        verification_level = str(data.get("verification_level", "BASIC")).upper().strip()
        if verification_level not in ("BASIC", "ENHANCED"):
            verification_level = "BASIC"

        # Check existing KYC record
        existing_kyc = KYCRecord.query.filter_by(user_id=actor.id).first()

        if existing_kyc:
            if existing_kyc.verification_status == "VERIFIED":
                return jsonify({
                    "status": "error",
                    "message": "KYC record already exists and is VERIFIED",
                    "kyc": serialize_kyc_record(existing_kyc, include_documents=False),
                }), 409
            elif existing_kyc.verification_status == "PENDING":
                return jsonify({
                    "status": "error",
                    "message": "KYC record already exists and is PENDING issuer review",
                    "kyc": serialize_kyc_record(existing_kyc, include_documents=False),
                }), 409
            # Allow updating if RESUBMISSION_REQUIRED or REJECTED
            kyc_record = existing_kyc
        else:
            kyc_record = KYCRecord(user_id=actor.id)
            db.session.add(kyc_record)

        # Update KYC record fields
        kyc_record.verification_level = verification_level
        kyc_record.verification_status = "PENDING"
        kyc_record.submitted_at = datetime.now(timezone.utc)

        # Clear previous rejection reasons upon fresh resubmission
        kyc_record.rejection_reason = None
        kyc_record.review_notes = None
        kyc_record.reviewed_by_id = None
        kyc_record.reviewed_at = None

        # Identity fields
        if "full_name" in data:
            kyc_record.full_name = data.get("full_name", "").strip() or None
        if "date_of_birth" in data:
            kyc_record.date_of_birth = data.get("date_of_birth", "").strip() or None
        if "nationality" in data:
            kyc_record.nationality = data.get("nationality", "").strip() or None
        if "document_type" in data:
            kyc_record.document_type = data.get("document_type", "").strip() or None
        if "document_number" in data:
            kyc_record.document_number = data.get("document_number", "").strip() or None

        # Enhanced KYC fields
        if "residential_address" in data:
            kyc_record.residential_address = data.get("residential_address", "").strip() or None
        if "country_of_issue" in data:
            kyc_record.country_of_issue = data.get("country_of_issue", "").strip() or None
        if "expiry_date" in data:
            kyc_record.expiry_date = data.get("expiry_date", "").strip() or None

        db.session.flush()

        # Handle file uploads if present
        saved_docs = []
        if is_multipart and request.files:
            for key, file_storage in request.files.items():
                if not file_storage or not file_storage.filename:
                    continue

                doc_type = "IDENTITY_DOCUMENT"
                if "passport" in key.lower():
                    doc_type = "PASSPORT"
                elif "national" in key.lower() or "id" in key.lower():
                    doc_type = "NATIONAL_ID"
                elif "address" in key.lower():
                    doc_type = "PROOF_OF_ADDRESS"
                elif kyc_record.document_type:
                    doc_type = kyc_record.document_type

                success, meta, error_msg = save_kyc_document(file_storage, document_type=doc_type)
                if not success:
                    db.session.rollback()
                    return jsonify({
                        "status": "error",
                        "message": f"Document upload failed for '{file_storage.filename}': {error_msg}",
                    }), 400

                doc_entry = KYCDocument(
                    kyc_record_id=kyc_record.id,
                    document_type=meta["document_type"],
                    file_name=meta["file_name"],
                    stored_file_name=meta["stored_file_name"],
                    file_path=meta["file_path"],
                    file_size=meta["file_size"],
                    mime_type=meta["mime_type"],
                    file_hash=meta["file_hash"],
                )
                db.session.add(doc_entry)
                saved_docs.append(doc_entry)

        # Audit Event for KYC submission
        create_audit_event(
            event_type="KYC_SUBMITTED",
            actor_id=actor.user_uuid,
            event_data=(
                f"KYC application {kyc_record.id} submitted for user {actor.user_uuid} "
                f"at level {verification_level}. Uploaded docs: {len(saved_docs)}"
            ),
        )

        db.session.commit()

        status_code = 201 if not existing_kyc else 200
        return jsonify({
            "status": "success",
            "message": "KYC application submitted successfully and pending issuer review",
            "kyc": serialize_kyc_record(kyc_record, include_documents=True),
        }), status_code

    except Exception as error:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Failed to submit KYC application",
            "error": str(error),
        }), 500


# ==================================================
# 3. ISSUER / ADMIN: List Pending KYC Applications
# ==================================================

@kyc_bp.get("/pending")
@require_role("ISSUER", "ADMIN")
def list_pending_kyc():
    """Retrieve all pending KYC applications awaiting review."""
    status_filter = request.args.get("status", "PENDING").upper()

    query = KYCRecord.query
    if status_filter != "ALL":
        query = query.filter_by(verification_status=status_filter)

    records = query.order_by(KYCRecord.created_at.desc()).all()

    return jsonify({
        "status": "success",
        "count": len(records),
        "applications": [serialize_kyc_record(r, include_documents=True) for r in records],
    }), 200


# ==================================================
# 4. GET KYC Record by User UUID (with RBAC & Ownership)
# ==================================================

@kyc_bp.get("/<string:user_uuid>")
def get_kyc_record(user_uuid):
    """
    Retrieve KYC application details.
    Access Control:
    - HOLDER may ONLY retrieve their OWN KYC record.
    - ISSUER / ADMIN may retrieve any KYC record.
    """
    actor = get_authenticated_actor()
    if not actor:
        return jsonify({"status": "error", "message": "Bearer token is required"}), 401

    if actor.role == "HOLDER" and actor.user_uuid != user_uuid:
        return jsonify({
            "status": "error",
            "message": "Unauthorized access to another holder's KYC record",
        }), 403

    user = User.query.filter_by(user_uuid=user_uuid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    kyc_record = KYCRecord.query.filter_by(user_id=user.id).first()
    if not kyc_record:
        return jsonify({"status": "error", "message": "KYC record not found"}), 404

    return jsonify({
        "status": "success",
        "kyc": serialize_kyc_record(kyc_record, include_documents=True),
    }), 200


# ==================================================
# 5. Secure Document Streaming (Authenticated & RBAC)
# ==================================================

@kyc_bp.get("/documents/<int:document_id>")
def view_kyc_document(document_id):
    """
    Stream an uploaded identity document.
    Access Control:
    - HOLDER may ONLY access documents belonging to their own KYC application.
    - ISSUER / ADMIN may access documents for applications under review.
    - Public static access is completely blocked.
    """
    actor = get_authenticated_actor()
    if not actor:
        return jsonify({"status": "error", "message": "Bearer token is required"}), 401

    document = KYCDocument.query.get(document_id)
    if not document:
        return jsonify({"status": "error", "message": "Document not found"}), 404

    kyc_record = document.kyc_record
    if not kyc_record:
        return jsonify({"status": "error", "message": "Associated KYC record not found"}), 404

    # Ownership check for HOLDER
    if actor.role == "HOLDER" and kyc_record.user_id != actor.id:
        return jsonify({
            "status": "error",
            "message": "Unauthorized access to another holder's documents",
        }), 403

    if not os.path.exists(document.file_path):
        return jsonify({"status": "error", "message": "Stored document file missing from storage"}), 404

    response = send_file(
        document.file_path,
        mimetype=document.mime_type,
        as_attachment=False,
        download_name=document.file_name,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    return response


# ==================================================
# 6. ISSUER: Review Decision (Verify / Reject / Resubmit)
# ==================================================

@kyc_bp.patch("/<string:user_uuid>/review")
@require_role("ISSUER", "ADMIN")
def review_kyc_application(user_uuid):
    """
    Authorized Issuer review endpoint.
    Decisions:
    - 'VERIFY': requires confirmed_evidence_reviewed=True
    - 'REJECT': requires reason
    - 'REQUEST_RESUBMISSION': requires reason
    """
    actor = get_authenticated_actor()
    if not actor:
        return jsonify({"status": "error", "message": "Authenticated actor not found"}), 401

    try:
        data = request.get_json(silent=True) or {}
        decision = str(data.get("decision", "")).upper().strip()
        reason = str(data.get("reason", "")).strip()
        notes = str(data.get("notes", "")).strip()
        confirmed = bool(data.get("confirmed_evidence_reviewed", False))

        if decision not in ("VERIFY", "REJECT", "REQUEST_RESUBMISSION"):
            return jsonify({
                "status": "error",
                "message": "Invalid decision. Must be 'VERIFY', 'REJECT', or 'REQUEST_RESUBMISSION'",
            }), 400

        user = User.query.filter_by(user_uuid=user_uuid).first()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        kyc_record = KYCRecord.query.filter_by(user_id=user.id).first()
        if not kyc_record:
            return jsonify({"status": "error", "message": "KYC record not found"}), 404

        now = datetime.now(timezone.utc)

        if decision == "VERIFY":
            if kyc_record.verification_status == "VERIFIED":
                return jsonify({
                    "status": "error",
                    "message": "KYC record is already verified",
                }), 409

            if not confirmed:
                return jsonify({
                    "status": "error",
                    "message": "Explicit confirmation of evidence review is required to verify KYC",
                }), 400

            kyc_record.verification_status = "VERIFIED"
            kyc_record.verified_at = now
            kyc_record.reviewed_by_id = actor.id
            kyc_record.reviewed_at = now
            kyc_record.review_notes = notes or "Reviewed and approved by authorized officer"
            kyc_record.rejection_reason = None

            create_audit_event(
                event_type="KYC_VERIFIED",
                actor_id=actor.user_uuid,
                event_data=(
                    f"KYC record {kyc_record.id} for user {user.user_uuid} VERIFIED by {actor.user_uuid}. "
                    f"Notes: {kyc_record.review_notes}"
                ),
            )

        elif decision == "REJECT":
            if not reason:
                return jsonify({
                    "status": "error",
                    "message": "A rejection reason is required",
                }), 400

            kyc_record.verification_status = "REJECTED"
            kyc_record.reviewed_by_id = actor.id
            kyc_record.reviewed_at = now
            kyc_record.rejection_reason = reason
            kyc_record.review_notes = notes or None
            kyc_record.verified_at = None

            create_audit_event(
                event_type="KYC_REJECTED",
                actor_id=actor.user_uuid,
                event_data=(
                    f"KYC record {kyc_record.id} for user {user.user_uuid} REJECTED by {actor.user_uuid}. "
                    f"Reason: {reason}"
                ),
            )

        elif decision == "REQUEST_RESUBMISSION":
            if not reason:
                return jsonify({
                    "status": "error",
                    "message": "A resubmission reason or instructions is required",
                }), 400

            kyc_record.verification_status = "RESUBMISSION_REQUIRED"
            kyc_record.reviewed_by_id = actor.id
            kyc_record.reviewed_at = now
            kyc_record.rejection_reason = reason
            kyc_record.review_notes = notes or None
            kyc_record.verified_at = None

            create_audit_event(
                event_type="KYC_RESUBMISSION_REQUESTED",
                actor_id=actor.user_uuid,
                event_data=(
                    f"KYC record {kyc_record.id} for user {user.user_uuid} RESUBMISSION REQUESTED by {actor.user_uuid}. "
                    f"Instructions: {reason}"
                ),
            )

        db.session.commit()

        return jsonify({
            "status": "success",
            "message": f"KYC application successfully transitioned to {kyc_record.verification_status}",
            "kyc": serialize_kyc_record(kyc_record, include_documents=True),
        }), 200

    except Exception as error:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Failed to update KYC review decision",
            "error": str(error),
        }), 500


# ==================================================
# 7. Backward-Compatible Verify Endpoint
# ==================================================

@kyc_bp.patch("/<string:user_uuid>/verify")
@require_role("ISSUER", "ADMIN")
def verify_kyc_record(user_uuid):
    """
    Backward-compatible KYC verify endpoint.
    Maintains compatibility with existing scripts and test suites.
    """
    actor = get_authenticated_actor()
    if not actor:
        return jsonify({"status": "error", "message": "Authenticated user is not active"}), 403

    user = User.query.filter_by(user_uuid=user_uuid).first()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    kyc_record = KYCRecord.query.filter_by(user_id=user.id).first()
    if not kyc_record:
        return jsonify({"status": "error", "message": "KYC record not found"}), 404

    if kyc_record.verification_status == "VERIFIED":
        return jsonify({
            "status": "error",
            "message": "KYC record is already verified",
        }), 409

    now = datetime.now(timezone.utc)
    kyc_record.verification_status = "VERIFIED"
    kyc_record.verified_at = now
    kyc_record.reviewed_by_id = actor.id
    kyc_record.reviewed_at = now
    kyc_record.rejection_reason = None

    create_audit_event(
        event_type="KYC_VERIFIED",
        actor_id=actor.user_uuid,
        event_data=f"KYC record {kyc_record.id} verified",
    )

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "KYC verified successfully",
        "kyc": {
            "id": kyc_record.id,
            "user_uuid": user.user_uuid,
            "verification_status": kyc_record.verification_status,
            "verification_level": kyc_record.verification_level,
            "verified_at": kyc_record.verified_at.isoformat(),
        },
    }), 200
