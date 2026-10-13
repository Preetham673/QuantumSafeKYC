import oqs


# --------------------------------------------------
# ML-DSA PQC Signature Service
# --------------------------------------------------

SIGNATURE_ALGORITHM = "ML-DSA-65"


def generate_keypair():
    """
    Generate an ML-DSA-65 post-quantum key pair.

    Returns:
        public_key: bytes
        secret_key: bytes
    """

    signer = oqs.Signature(SIGNATURE_ALGORITHM)

    public_key = signer.generate_keypair()
    secret_key = signer.export_secret_key()

    return public_key, secret_key


def sign_message(message: bytes, secret_key: bytes) -> bytes:
    """
    Create a post-quantum digital signature.
    """

    signer = oqs.Signature(
        SIGNATURE_ALGORITHM,
        secret_key=secret_key,
    )

    signature = signer.sign(message)

    return signature


def verify_signature(
    message: bytes,
    signature: bytes,
    public_key: bytes,
) -> bool:
    """
    Verify an ML-DSA-65 signature.
    """

    verifier = oqs.Signature(SIGNATURE_ALGORITHM)

    return verifier.verify(
        message,
        signature,
        public_key,
    )