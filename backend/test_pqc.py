from pqc_service import (
    generate_keypair,
    sign_message,
    verify_signature,
)


print("=" * 60)
print("QuantumSafeKYC - PQC TEST")
print("=" * 60)


# --------------------------------------------------
# 1. Generate PQC keys
# --------------------------------------------------

print("\n[1] Generating ML-DSA-65 key pair...")

public_key, secret_key = generate_keypair()

print("Public key generated :", len(public_key), "bytes")
print("Secret key generated :", len(secret_key), "bytes")


# --------------------------------------------------
# 2. Create credential data
# --------------------------------------------------

message = b"""
QuantumSafeKYC Credential
User: 48f81fe9-7bc0-4e9a-a251-58d9db2f0b3d
Status: VERIFIED
Credential Type: KYC
"""

print("\n[2] Credential data prepared.")


# --------------------------------------------------
# 3. Sign credential
# --------------------------------------------------

print("\n[3] Creating ML-DSA-65 signature...")

signature = sign_message(
    message,
    secret_key,
)

print("Signature generated :", len(signature), "bytes")


# --------------------------------------------------
# 4. Verify original credential
# --------------------------------------------------

print("\n[4] Verifying original credential...")

valid = verify_signature(
    message,
    signature,
    public_key,
)

print("Original credential:", "VALID" if valid else "INVALID")


# --------------------------------------------------
# 5. Tamper with credential
# --------------------------------------------------

tampered_message = message.replace(
    b"VERIFIED",
    b"REVOKED",
)

print("\n[5] Testing tampered credential...")

tampered_valid = verify_signature(
    tampered_message,
    signature,
    public_key,
)

print(
    "Tampered credential:",
    "VALID" if tampered_valid else "INVALID",
)


# --------------------------------------------------
# Final result
# --------------------------------------------------

print("\n" + "=" * 60)

if valid and not tampered_valid:
    print("PQC TEST PASSED")
    print("ML-DSA successfully protects the credential.")
else:
    print("PQC TEST FAILED")

print("=" * 60)