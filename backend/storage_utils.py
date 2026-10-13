"""
Storage and Document Security Utilities for QuantumSafeKYC.

Enforces:
- File size restrictions (max 10MB)
- Extension whitelisting (.pdf, .jpg, .jpeg, .png)
- MIME type and magic number / header byte validation
- Safe server-side randomized unique filenames
- Path traversal prevention
- SHA-256 integrity calculation
- Controlled document streaming (never public static files)
"""

import hashlib
import os
import uuid
from typing import Tuple, Dict, Any, Optional
from werkzeug.utils import secure_filename

# Maximum allowed file size: 10 Megabytes
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

# Allowed MIME types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/pjpeg",
    "image/png",
}

# Magic bytes (file signatures)
FILE_SIGNATURES = {
    "pdf": [b"%PDF"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
}

# Base upload directory
DEFAULT_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "kyc_documents")
UPLOAD_DIR = os.getenv("KYC_UPLOAD_DIR", DEFAULT_UPLOAD_DIR)


def ensure_upload_dir() -> str:
    """Ensure the secure storage directory exists."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR


def get_file_extension(filename: str) -> str:
    """Extract and lowercase file extension without leading dot."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower().strip()


def validate_file_signature(header_bytes: bytes, ext: str) -> bool:
    """Validate that the file header matches known magic bytes for the declared extension."""
    signatures = FILE_SIGNATURES.get(ext, [])
    if not signatures:
        return False
    return any(header_bytes.startswith(sig) for sig in signatures)


def sanitize_filename(filename: str) -> str:
    """Sanitize original filename to avoid illegal characters and path traversal."""
    cleaned = secure_filename(filename)
    if not cleaned:
        cleaned = "document"
    return cleaned


def save_kyc_document(
    file_storage,
    document_type: str = "IDENTITY_DOCUMENT",
) -> Tuple[bool, Dict[str, Any], Optional[str]]:
    """
    Validate, securely hash, and save an uploaded KYC document.

    Returns:
        (success, document_metadata, error_message)
    """
    if not file_storage or not file_storage.filename:
        return False, {}, "No file provided or empty filename"

    original_filename = file_storage.filename.strip()
    ext = get_file_extension(original_filename)

    if ext not in ALLOWED_EXTENSIONS:
        return False, {}, f"Unsupported file extension '.{ext}'. Accepted formats: PDF, JPG, PNG."

    # Read initial bytes to verify header signature
    header_bytes = file_storage.read(32)
    file_storage.seek(0)

    if not validate_file_signature(header_bytes, ext):
        return False, {}, f"File content does not match declared extension '.{ext}'. Upload rejected."

    # Validate declared MIME type if provided
    mime_type = getattr(file_storage, "mimetype", "").lower().strip()
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        return False, {}, f"Unsupported MIME type '{mime_type}'. Accepted types: PDF, JPG, PNG."

    if not mime_type:
        mime_map = {
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
        }
        mime_type = mime_map.get(ext, "application/octet-stream")

    upload_dir = ensure_upload_dir()
    clean_orig_name = sanitize_filename(original_filename)
    unique_prefix = uuid.uuid4().hex
    stored_file_name = f"{unique_prefix}_{clean_orig_name}"
    target_path = os.path.join(upload_dir, stored_file_name)

    # Path traversal check
    target_path_resolved = os.path.realpath(target_path)
    upload_dir_resolved = os.path.realpath(upload_dir)
    if not target_path_resolved.startswith(upload_dir_resolved + os.sep):
        return False, {}, "Invalid file path traversal detected."

    # Stream and hash to disk with strict size limit
    sha256 = hashlib.sha256()
    total_bytes = 0

    try:
        with open(target_path, "wb") as f_out:
            while True:
                chunk = file_storage.read(64 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_FILE_SIZE:
                    # Remove partial file
                    f_out.close()
                    if os.path.exists(target_path):
                        os.remove(target_path)
                    return False, {}, f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB."
                sha256.update(chunk)
                f_out.write(chunk)

        if total_bytes == 0:
            if os.path.exists(target_path):
                os.remove(target_path)
            return False, {}, "Empty file uploaded."

        file_hash = sha256.hexdigest()

        return True, {
            "document_type": document_type,
            "file_name": clean_orig_name,
            "stored_file_name": stored_file_name,
            "file_path": target_path,
            "file_size": total_bytes,
            "mime_type": mime_type,
            "file_hash": file_hash,
        }, None

    except Exception as exc:
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except OSError:
                pass
        return False, {}, f"Failed to save document: {str(exc)}"
