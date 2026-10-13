from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy


# --------------------------------------------------
# SQLAlchemy Instance
# --------------------------------------------------

db = SQLAlchemy()


# ==================================================
# USER
# ==================================================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_uuid = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
    )


    password_hash = db.Column(
        db.String(255),
        nullable=True,
    )

    role = db.Column(
        db.String(30),
        nullable=False,
        default="HOLDER",
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="ACTIVE",
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    kyc_records = db.relationship(
        "KYCRecord",
        back_populates="user",
        foreign_keys="KYCRecord.user_id",
        cascade="all, delete-orphan",
    )

    credentials = db.relationship(
        "Credential",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    consents = db.relationship(
        "Consent",
        back_populates="user",
        cascade="all, delete-orphan",
    )


# ==================================================
# KYC RECORD
# ==================================================

class KYCRecord(db.Model):
    __tablename__ = "kyc_records"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    verification_status = db.Column(
        db.String(30),
        nullable=False,
        default="PENDING",
    )

    verification_level = db.Column(
        db.String(30),
        nullable=True,
    )

    # Identity details submitted by holder
    full_name = db.Column(
        db.String(150),
        nullable=True,
    )

    date_of_birth = db.Column(
        db.String(20),
        nullable=True,
    )

    nationality = db.Column(
        db.String(100),
        nullable=True,
    )

    document_type = db.Column(
        db.String(50),
        nullable=True,
    )

    document_number = db.Column(
        db.String(100),
        nullable=True,
    )

    residential_address = db.Column(
        db.String(255),
        nullable=True,
    )

    country_of_issue = db.Column(
        db.String(100),
        nullable=True,
    )

    expiry_date = db.Column(
        db.String(20),
        nullable=True,
    )

    submitted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    # Review metadata
    reviewed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True,
    )

    reviewed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    rejection_reason = db.Column(
        db.String(500),
        nullable=True,
    )

    review_notes = db.Column(
        db.String(500),
        nullable=True,
    )

    verified_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="kyc_records",
    )

    reviewer = db.relationship(
        "User",
        foreign_keys=[reviewed_by_id],
    )

    documents = db.relationship(
        "KYCDocument",
        back_populates="kyc_record",
        cascade="all, delete-orphan",
    )


# ==================================================
# KYC DOCUMENT
# ==================================================

class KYCDocument(db.Model):
    __tablename__ = "kyc_documents"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    kyc_record_id = db.Column(
        db.Integer,
        db.ForeignKey("kyc_records.id"),
        nullable=False,
        index=True,
    )

    document_type = db.Column(
        db.String(50),
        nullable=False,
        default="IDENTITY_DOCUMENT",
    )

    file_name = db.Column(
        db.String(255),
        nullable=False,
    )

    stored_file_name = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
    )

    file_path = db.Column(
        db.String(500),
        nullable=False,
    )

    file_size = db.Column(
        db.Integer,
        nullable=False,
    )

    mime_type = db.Column(
        db.String(100),
        nullable=False,
    )

    file_hash = db.Column(
        db.String(128),
        nullable=False,
    )

    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    kyc_record = db.relationship(
        "KYCRecord",
        back_populates="documents",
    )



# ==================================================
# CREDENTIAL
# ==================================================

class Credential(db.Model):
    __tablename__ = "credentials"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    credential_uuid = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    credential_type = db.Column(
        db.String(50),
        nullable=False,
        default="KYC",
    )

    credential_hash = db.Column(
        db.String(128),
        unique=True,
        nullable=False,
        index=True,
    )

    pqc_algorithm = db.Column(
        db.String(50),
        nullable=True,
        default="ML-DSA-65",
    )

    pqc_public_key = db.Column(
        db.LargeBinary,
        nullable=True,
    )

    pqc_signature = db.Column(
        db.LargeBinary,
        nullable=True,
    )

    pqc_signed_data = db.Column(db.Text, nullable=True)

    issuer_id = db.Column(
        db.String(100),
        nullable=False,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="ACTIVE",
    )

    issued_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user = db.relationship(
        "User",
        back_populates="credentials",
    )

    consents = db.relationship(
        "Consent",
        back_populates="credential",
        cascade="all, delete-orphan",
    )

    verifications = db.relationship(
        "Verification",
        back_populates="credential",
        cascade="all, delete-orphan",
    )

    revocations = db.relationship(
        "Revocation",
        back_populates="credential",
        cascade="all, delete-orphan",
    )


    blockchain_anchor = db.relationship(
        "BlockchainAnchor",
        back_populates="credential",
        uselist=False,
        cascade="all, delete-orphan",
    )

    audit_events = db.relationship(
        "AuditEvent",
        back_populates="credential",
        cascade="all, delete-orphan",
    )


# ==================================================
# CONSENT
# ==================================================

class Consent(db.Model):
    __tablename__ = "consents"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    consent_uuid = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    credential_id = db.Column(
        db.Integer,
        db.ForeignKey("credentials.id"),
        nullable=False,
        index=True,
    )

    verifier_id = db.Column(
        db.String(100),
        nullable=False,
    )

    purpose = db.Column(
        db.String(255),
        nullable=False,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="GRANTED",
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user = db.relationship(
        "User",
        back_populates="consents",
    )

    credential = db.relationship(
        "Credential",
        back_populates="consents",
    )


# ==================================================
# VERIFICATION
# ==================================================

class Verification(db.Model):
    __tablename__ = "verifications"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    verification_uuid = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
    )

    credential_id = db.Column(
        db.Integer,
        db.ForeignKey("credentials.id"),
        nullable=False,
        index=True,
    )

    verifier_id = db.Column(
        db.String(100),
        nullable=False,
    )

    result = db.Column(
        db.String(30),
        nullable=False,
    )

    verified_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    credential = db.relationship(
        "Credential",
        back_populates="verifications",
    )


# ==================================================
# REVOCATION
# ==================================================

class Revocation(db.Model):
    __tablename__ = "revocations"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    revocation_uuid = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
    )

    credential_id = db.Column(
        db.Integer,
        db.ForeignKey("credentials.id"),
        nullable=False,
        index=True,
    )

    reason = db.Column(
        db.String(255),
        nullable=False,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="REVOKED",
    )

    revoked_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    credential = db.relationship(
        "Credential",
        back_populates="revocations",
    )


# ==================================================
# AUDIT EVENT
# ==================================================

class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    event_uuid = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
    )

    event_type = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    actor_id = db.Column(
        db.String(100),
        nullable=True,
    )

    credential_id = db.Column(
        db.Integer,
        db.ForeignKey("credentials.id"),
        nullable=True,
        index=True,
    )

    event_hash = db.Column(
        db.String(128),
        nullable=True,
        index=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    credential = db.relationship(
        "Credential",
        back_populates="audit_events",
    )


# --------------------------------------------------
# Blockchain Anchor
# --------------------------------------------------

class BlockchainAnchor(db.Model):
    __tablename__ = "blockchain_anchors"

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    anchor_uuid = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
    )

    credential_id = db.Column(
        db.Integer,
        db.ForeignKey("credentials.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    credential_hash = db.Column(
        db.String(128),
        nullable=False,
        index=True,
    )

    blockchain_network = db.Column(
        db.String(100),
        nullable=False,
    )

    transaction_id = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    block_number = db.Column(
        db.BigInteger,
        nullable=True,
    )

    anchor_status = db.Column(
        db.String(30),
        nullable=False,
        default="ANCHORED",
    )

    anchored_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    credential = db.relationship(
        "Credential",
        back_populates="blockchain_anchor",
    )