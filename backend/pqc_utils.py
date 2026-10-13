import base64
from pathlib import Path

import oqs


# --------------------------------------------------
# PQC Configuration
# --------------------------------------------------

ALGORITHM = "ML-DSA-65"

BASE_DIR = Path(__file__).resolve().parent
KEY_DIR = BASE_DIR / "keys"

PUBLIC_KEY_FILE = KEY_DIR / "ml_dsa_65_public.key"
SECRET_KEY_FILE = KEY_DIR / "ml_dsa_65_secret.key"


# --------------------------------------------------
# Ensure Key Directory Exists
# --------------------------------------------------

def ensure_key_directory():
    KEY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# --------------------------------------------------
# Generate / Load ML-DSA-65 Key Pair
# --------------------------------------------------

def load_or_create_keys():
    ensure_key_directory()

    if (
        PUBLIC_KEY_FILE.exists()
        and SECRET_KEY_FILE.exists()
    ):
        public_key = PUBLIC_KEY_FILE.read_bytes()
        secret_key = SECRET_KEY_FILE.read_bytes()

        return public_key, secret_key

    with oqs.Signature(ALGORITHM) as signer:
        public_key = signer.generate_keypair()
        secret_key = signer.export_secret_key()

    PUBLIC_KEY_FILE.write_bytes(public_key)
    SECRET_KEY_FILE.write_bytes(secret_key)

    return public_key, secret_key


# --------------------------------------------------
# Sign Credential
# --------------------------------------------------

def sign_credential(credential_data: str):
    public_key, secret_key = load_or_create_keys()

    with oqs.Signature(
        ALGORITHM,
        secret_key,
    ) as signer:

        signature = signer.sign(
            credential_data.encode("utf-8")
        )

    return public_key, signature


# --------------------------------------------------
# Verify Credential
# --------------------------------------------------

def verify_credential(
    credential_data: str,
    public_key: bytes,
    signature: bytes,
):
    with oqs.Signature(ALGORITHM) as verifier:

        return verifier.verify(
            credential_data.encode("utf-8"),
            signature,
            public_key,
        )


# --------------------------------------------------
# Base64 Helpers
# --------------------------------------------------

def encode_bytes(data: bytes):
    return base64.b64encode(data).decode("utf-8")


def decode_bytes(data: str):
    return base64.b64decode(data)