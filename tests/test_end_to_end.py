"""
QuantumSafeKYC - Phase 9 End-to-End System Integration Test Suite
Verifies the complete lifecycle across Backend, Database, Post-Quantum Cryptography,
Role-Based Access Control, KYC, Credentials, Blockchain Anchors, Audit Events, and MCP.
"""

import json
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:5000/api"
PASS = 0
FAIL = 0


def request(method, path, body=None, token=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as err:
        try:
            return err.code, json.loads(err.read().decode())
        except Exception:
            return err.code, {"error": err.reason}
    except Exception as exc:
        return 0, {"error": str(exc)}


def check(label, condition, detail=""):
    global PASS, FAIL
    status_str = "[PASS]" if condition else "[FAIL]"
    print(f"  {status_str} {label}")
    if not condition and detail:
        print(f"         Detail: {str(detail)[:140]}")
    if condition:
        PASS += 1
    else:
        FAIL += 1


def section(name):
    print("\n" + "=" * 65)
    print(f"  {name}")
    print("=" * 65)


def run_e2e_tests():
    global PASS, FAIL
    start_time = time.time()
    print("=" * 65)
    print("QuantumSafeKYC - Phase 9 End-to-End Integration Test Suite")
    print("=" * 65)

    # -------------------------------------------------------------
    # 1. System Health & Infrastructure
    # -------------------------------------------------------------
    section("1. System Health & Infrastructure")
    status, res = request("GET", "/health")
    check("API Health Endpoint -> 200 OK", status == 200 and res.get("status") == "ok", res)

    status, res = request("GET", "/db-health")
    check("PostgreSQL Database Connection -> 200 OK", status == 200 and res.get("connection") == "successful", res)

    status, res = request("GET", "/mcp/tools")
    tools = res.get("tools", [])
    check(f"MCP Tool Discovery -> 9 Standardized Tools Registered ({len(tools)} found)", status == 200 and len(tools) == 9, res)

    status, res = request("POST", "/mcp/execute", {"tool": "system_status"})
    check("MCP System Status Execution -> Success", status == 200 and res.get("result", {}).get("mcp") == "connected", res)

    # -------------------------------------------------------------
    # 2. Authentication & Role-Based Access Control
    # -------------------------------------------------------------
    section("2. Authentication & Role-Based Access Control")
    # Public registration blocked for ISSUER / ADMIN
    status, res = request("POST", "/auth/register", {"password": "TestPassword@2025!", "role": "ISSUER"})
    check("Public ISSUER Registration Blocked -> 403 Forbidden", status == 403, res)

    status, res = request("POST", "/auth/register", {"password": "TestPassword@2025!", "role": "ADMIN"})
    check("Public ADMIN Registration Blocked -> 403 Forbidden", status == 403, res)

    # Register new HOLDER
    holder_pw = "HolderPass@E2ETest2025!"
    status, res = request("POST", "/auth/register", {"password": holder_pw, "role": "HOLDER"})
    check("Register Fresh HOLDER -> 201 Created", status == 201 and "user" in res, res)
    holder_uuid = res.get("user", {}).get("user_uuid")

    # Login as new HOLDER
    status, res = request("POST", "/auth/login", {"user_uuid": holder_uuid, "password": holder_pw})
    check("HOLDER Login -> 200 OK & JWT Issued", status == 200 and "access_token" in res, res)
    holder_token = res.get("access_token")

    # Login as ISSUER
    issuer_uuid = "750bd462-f771-468f-9cf8-a5d27b02a665"
    status, res = request("POST", "/auth/login", {"user_uuid": issuer_uuid, "password": "IssuerPass@2025!"})
    check("ISSUER / ADMIN Login -> 200 OK & JWT Issued", status == 200 and "access_token" in res, res)
    issuer_token = res.get("access_token")

    # Verify Profile via /auth/me
    status, res = request("GET", "/auth/me", token=holder_token)
    check("HOLDER Identity Verification via /auth/me -> Role: HOLDER", status == 200 and res.get("user", {}).get("role") == "HOLDER", res)

    # -------------------------------------------------------------
    # 3. KYC Submission & Verification Lifecycle
    # -------------------------------------------------------------
    section("3. KYC Submission & Verification Lifecycle")
    # Holder submits KYC
    status, res = request("POST", "/kyc", {"user_uuid": holder_uuid, "verification_level": "ENHANCED"}, token=holder_token)
    check("HOLDER Submits KYC Record -> 201 Created (PENDING)", status == 201 and res.get("kyc", {}).get("verification_status") == "PENDING", res)

    # Duplicate KYC submission blocked
    status, res = request("POST", "/kyc", {"user_uuid": holder_uuid, "verification_level": "ENHANCED"}, token=holder_token)
    check("Duplicate KYC Submission -> 409 Conflict", status == 409, res)

    # Holder attempts to verify own KYC -> 403 Forbidden
    status, res = request("PATCH", f"/kyc/{holder_uuid}/verify", token=holder_token)
    check("HOLDER Unauthorized KYC Verification Attempt -> 403 Forbidden", status == 403, res)

    # Issuer verifies KYC
    status, res = request("PATCH", f"/kyc/{holder_uuid}/verify", token=issuer_token)
    check("ISSUER Verifies KYC Record -> 200 OK", status == 200 and res.get("status") == "success", res)

    # Inspect verified KYC record (requires authenticated token — issuer or holder)
    status, res = request("GET", f"/kyc/{holder_uuid}", token=issuer_token)
    check("Inspect KYC Status -> VERIFIED", status == 200 and res.get("kyc", {}).get("verification_status") == "VERIFIED", res)

    # -------------------------------------------------------------
    # 4. Post-Quantum Credential Issuance & Cryptographic Validation
    # -------------------------------------------------------------
    section("4. Post-Quantum Credential Issuance & Cryptographic Validation")
    # Holder attempts to issue credential -> 403
    status, res = request("POST", f"/credentials/{holder_uuid}/issue", token=holder_token)
    check("HOLDER Issuance Attempt -> 403 Forbidden", status == 403, res)

    # Issuer issues ML-DSA-65 credential
    status, res = request("POST", f"/credentials/{holder_uuid}/issue", token=issuer_token)
    check("ISSUER Signs & Issues ML-DSA-65 Credential -> 201 Created", status == 201 and res.get("credential", {}).get("status") == "ACTIVE", res)
    cred = res.get("credential", {})
    cred_uuid = cred.get("credential_uuid")

    algo = cred.get("pqc", {}).get("algorithm") or cred.get("pqc_algorithm")
    check("Credential uses NIST FIPS 204 ML-DSA-65", algo == "ML-DSA-65", cred)
    check("Credential contains Cryptographic Hash", bool(cred.get("credential_hash")), cred)

    # Verify PQC Signature Directly
    status, res = request("POST", f"/credentials/verify-pqc/{cred_uuid}")
    check("Post-Quantum ML-DSA-65 Signature Cryptographic Verification -> VALID", status == 200 and res.get("result") == "VALID", res)

    # Complete Credential Verification Endpoint
    status, res = request("POST", f"/credentials/verify/{cred_uuid}")
    check("Complete Credential Verification Endpoint -> VALID", status == 200 and res.get("result") == "VALID", res)

    # -------------------------------------------------------------
    # 5. Blockchain Anchoring & Immutable State
    # -------------------------------------------------------------
    section("5. Blockchain Anchoring & Immutable State")
    status, res = request("POST", f"/blockchain/anchor/{cred_uuid}")
    check("Anchor Credential Hash to Blockchain -> 201 Created", status == 201 and res.get("anchor", {}).get("anchor_status") == "ANCHORED", res)

    status, res = request("POST", f"/blockchain/verify/{cred_uuid}")
    check("Verify Credential Against Blockchain Anchor -> VALID", status == 200 and res.get("result") == "VALID", res)

    # -------------------------------------------------------------
    # 6. Verifier Consent & Zero-Trust Privacy Pipeline
    # -------------------------------------------------------------
    section("6. Verifier Consent & Zero-Trust Privacy Pipeline")
    verifier_id = "NATIONAL-BANK-AUDIT-001"
    purpose = "Automated Compliance Audit"

    # Verifier attempts to query without consent -> Access Denied
    status, res = request("POST", "/verification/credential", {
        "credential_uuid": cred_uuid,
        "verifier_id": verifier_id,
        "purpose": purpose
    })
    check("Verification Request Without Consent -> Access Denied", res.get("verification", {}).get("result") in ("DENIED", "INVALID") or res.get("result") in ("DENIED", "INVALID"), res)

    # Holder grants consent
    status, res = request("POST", "/consents", {
        "user_uuid": holder_uuid,
        "credential_uuid": cred_uuid,
        "verifier_id": verifier_id,
        "purpose": purpose
    }, token=holder_token)
    check("HOLDER Grants Consent for Verifier -> 201 Created", status == 201 and res.get("consent", {}).get("status") in ("GRANTED", "ACTIVE"), res)
    consent_uuid = res.get("consent", {}).get("consent_uuid")

    # Check consent status
    status, res = request("POST", f"/consents/{consent_uuid}/check")
    check("Consent Status Check -> Granted", status == 200 and (res.get("consent_status") == "GRANTED" or res.get("consent", {}).get("granted") is True), res)

    # Verifier performs verification with granted consent
    status, res = request("POST", "/verification/credential", {
        "credential_uuid": cred_uuid,
        "verifier_id": verifier_id,
        "purpose": purpose
    })
    check("Verifier Verification with Granted Consent -> VALID", status == 200 and res.get("verification", {}).get("result") == "VALID", res)

    # -------------------------------------------------------------
    # 7. Credential Revocation & Immutable Audit Trail
    # -------------------------------------------------------------
    section("7. Credential Revocation & Immutable Audit Trail")
    # Holder cannot revoke without permission
    status, res = request("PATCH", f"/credentials/{cred_uuid}/revoke", {"reason": "Test"}, token=holder_token)
    check("HOLDER Revocation Attempt -> 403 Forbidden", status == 403, res)

    # Issuer revokes credential
    status, res = request("PATCH", f"/credentials/{cred_uuid}/revoke", {"reason": "End-to-End Test Revocation"}, token=issuer_token)
    check("ISSUER Revokes Credential -> 200 OK (Status: REVOKED)", status == 200 and res.get("credential", {}).get("status") == "REVOKED", res)

    # Duplicate revocation check
    status, res = request("PATCH", f"/credentials/{cred_uuid}/revoke", {"reason": "Duplicate Test"}, token=issuer_token)
    check("Duplicate Credential Revocation -> 409 Conflict", status == 409, res)

    # Verifier re-queries revoked credential -> MUST BE INVALID
    status, res = request("POST", f"/credentials/verify/{cred_uuid}")
    check("Post-Revocation Verification -> INVALID & signature_valid=False", status == 200 and res.get("result") == "INVALID" and res.get("signature_valid") is False, res)

    # Check revocation registry
    status, res = request("GET", f"/revocations/{cred_uuid}")
    check("Revocation Registry Confirms Revocation Record", status == 200 and res.get("status") == "success" and res.get("revocation", {}).get("status") == "REVOKED", res)

    # -------------------------------------------------------------
    # 8. Model Context Protocol (MCP) Tools Pipeline
    # -------------------------------------------------------------
    section("8. Model Context Protocol (MCP) Tools Pipeline")
    # Test get_user_tool
    status, res = request("POST", "/mcp/execute", {"tool": "get_user_tool", "parameters": {"user_uuid": holder_uuid}})
    check("MCP Tool: get_user_tool -> Returns User Profile", status == 200 and res.get("result", {}).get("user", {}).get("user_uuid") == holder_uuid, res)

    # Test get_credential_tool
    status, res = request("POST", "/mcp/execute", {"tool": "get_credential_tool", "parameters": {"credential_uuid": cred_uuid}})
    check("MCP Tool: get_credential_tool -> Returns Credential Details", status == 200 and res.get("result", {}).get("credential", {}).get("credential_uuid") == cred_uuid, res)

    # Test check_revocation_tool
    status, res = request("POST", "/mcp/execute", {"tool": "check_revocation_tool", "parameters": {"credential_uuid": cred_uuid}})
    check("MCP Tool: check_revocation_tool -> Detects REVOKED status", status == 200 and res.get("result", {}).get("result") == "REVOKED", res)

    # Test get_verification_history_tool
    status, res = request("POST", "/mcp/execute", {"tool": "get_verification_history_tool", "parameters": {"credential_uuid": cred_uuid}})
    check("MCP Tool: get_verification_history_tool -> Returns History Records", status == 200 and isinstance(res.get("result", {}).get("verification_history"), list), res)

    # -------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------
    elapsed = time.time() - start_time
    total = PASS + FAIL
    print("\n" + "=" * 65)
    print("  PHASE 9 END-TO-END SYSTEM TEST RESULTS")
    print(f"  TOTAL TESTS : {total}")
    print(f"  PASSED      : {PASS}")
    print(f"  FAILED      : {FAIL}")
    print(f"  DURATION    : {elapsed:.2f}s")
    print("=" * 65)

    if FAIL == 0:
        print("\nALL END-TO-END TESTS PASSED SUCCESSFULLY! SYSTEM 100% OPERATIONAL.\n")
        return 0
    else:
        print(f"\n{FAIL} TESTS FAILED. PLEASE REVIEW ABOVE.\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_e2e_tests())
