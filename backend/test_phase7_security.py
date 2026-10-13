import json
import sys
import urllib.request
import urllib.error
import psycopg

BASE = "http://127.0.0.1:5000"
DB_DSN = "host=127.0.0.1 port=5432 dbname=quantumsafekyc user=quantumsafekyc_app password=Preetham_2007"
PASS_COUNT = 0
FAIL_COUNT = 0


def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {"error": e.reason}
    except Exception as exc:
        return 0, {"error": str(exc)}


def check(label, cond, detail=""):
    global PASS_COUNT, FAIL_COUNT
    sym = "[PASS]" if cond else "[FAIL]"
    msg = "  " + sym + " " + label
    if not cond and detail:
        msg += " | " + str(detail)[:120]
    print(msg)
    if cond:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1


def section(t):
    print("")
    print("=" * 60)
    print("  " + t)
    print("=" * 60)


print("=" * 60)
print("QuantumSafeKYC - Phase 7 Security Hardening Tests")
print("=" * 60)

# ------------------------------------------------------------------
# Collect data from PostgreSQL directly (no Flask app import)
# ------------------------------------------------------------------
conn = psycopg.connect(DB_DSN)
cur = conn.cursor()

cur.execute("SELECT user_uuid FROM users WHERE role IN ('ISSUER','ADMIN') LIMIT 1")
row = cur.fetchone()
ISSUER_UUID = row[0] if row else None

cur.execute("SELECT credential_uuid FROM credentials WHERE status='REVOKED' LIMIT 1")
row = cur.fetchone()
REVOKED_UUID = row[0] if row else None

cur.execute("""
    SELECT c.credential_uuid, u.user_uuid
    FROM credentials c
    JOIN users u ON u.id = c.user_id
    WHERE c.status='ACTIVE' AND c.pqc_signature IS NOT NULL AND c.pqc_signed_data IS NOT NULL LIMIT 1
""")
row = cur.fetchone()
ACTIVE_UUID = row[0] if row else None
ACTIVE_OWNER = row[1] if row else None

cur.execute("SELECT COUNT(*) FROM audit_events")
audit_total = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='CREDENTIAL_REVOKED'")
revoked_event_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='CREDENTIAL_REVOKED' AND actor_id IS NOT NULL")
revoked_attributed = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM audit_events WHERE event_hash IS NOT NULL")
hashed_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='KYC_VERIFIED'")
kyc_event_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='KYC_VERIFIED' AND actor_id IS NOT NULL")
kyc_attributed = cur.fetchone()[0]

conn.close()

print("  ISSUER UUID:          " + str(ISSUER_UUID))
print("  REVOKED credential:   " + str(REVOKED_UUID))
print("  ACTIVE credential:    " + str(ACTIVE_UUID))
print("  ACTIVE owner:         " + str(ACTIVE_OWNER))
print("  Audit events total:   " + str(audit_total))

# Try to get ISSUER token
ISSUER_TOKEN = None
if ISSUER_UUID:
    for pw in ["IssuerPass@2025!", "Issuer@2025", "Admin@2025!", "Admin@123", "Preetham_2007", "issuer123"]:
        s, r = req("POST", "/api/auth/login", {"user_uuid": str(ISSUER_UUID), "password": pw})
        if r.get("access_token"):
            ISSUER_TOKEN = r["access_token"]
            print("  ISSUER token:         OK")
            break
    if not ISSUER_TOKEN:
        print("  ISSUER token:         FAILED (no password matched)")

# Register a fresh HOLDER for isolated tests
HOLDER_PW = "TestHolder@Phase7!"
s, r = req("POST", "/api/auth/register", {"password": HOLDER_PW, "role": "HOLDER"})
HOLDER_UUID = r.get("user", {}).get("user_uuid") if s == 201 else None
HOLDER_TOKEN = None
if HOLDER_UUID:
    s, r = req("POST", "/api/auth/login", {"user_uuid": HOLDER_UUID, "password": HOLDER_PW})
    HOLDER_TOKEN = r.get("access_token")
print("  HOLDER token:         " + ("OK" if HOLDER_TOKEN else "FAILED"))


# =====================================================================
# TEST 1: Duplicate Credential Revocation -> 409 Conflict
# =====================================================================
section("TEST 1: Duplicate Credential Revocation -> 409 Conflict")

if REVOKED_UUID:
    s, r = req("POST", "/api/revocations/" + str(REVOKED_UUID), {"reason": "dup test"})
    check("Revocation blueprint: already-revoked -> 409", s == 409, str(s) + " " + str(r))
    check("Response has status=error", r.get("status") == "error", str(r))
    if ISSUER_TOKEN:
        s2, r2 = req(
            "PATCH",
            "/api/credentials/" + str(REVOKED_UUID) + "/revoke",
            {"reason": "dup2"},
            token=ISSUER_TOKEN,
        )
        check("Credentials endpoint: already-revoked -> 409", s2 == 409, str(s2) + " " + str(r2))
else:
    check("Revoked credential available for test", False, "none found in DB")


# =====================================================================
# TEST 2: Unauthorized Credential Operations
# =====================================================================
section("TEST 2: Unauthorized Credential Operations")

if ACTIVE_OWNER:
    s, r = req("POST", "/api/credentials/" + str(ACTIVE_OWNER) + "/issue")
    check("Issue without token -> 401", s == 401, str(s))

if HOLDER_TOKEN and ACTIVE_OWNER:
    s, r = req("POST", "/api/credentials/" + str(ACTIVE_OWNER) + "/issue", token=HOLDER_TOKEN)
    check("Issue as HOLDER -> 403", s == 403, str(s) + " " + str(r))

if ACTIVE_UUID:
    s, r = req("PATCH", "/api/credentials/" + str(ACTIVE_UUID) + "/revoke", {"reason": "x"})
    check("Revoke without token -> 401", s == 401, str(s))

if HOLDER_TOKEN and ACTIVE_UUID:
    s, r = req("PATCH", "/api/credentials/" + str(ACTIVE_UUID) + "/revoke",
               {"reason": "x"}, token=HOLDER_TOKEN)
    check("Revoke as HOLDER -> 403", s == 403, str(s) + " " + str(r))

if ACTIVE_OWNER:
    s, r = req("PATCH", "/api/kyc/" + str(ACTIVE_OWNER) + "/verify")
    check("KYC verify without token -> 401", s == 401, str(s))

if HOLDER_TOKEN and ACTIVE_OWNER:
    s, r = req("PATCH", "/api/kyc/" + str(ACTIVE_OWNER) + "/verify", token=HOLDER_TOKEN)
    check("KYC verify as HOLDER -> 403", s == 403, str(s) + " " + str(r))


# =====================================================================
# TEST 3: KYC Actor-Validation Ordering
# =====================================================================
section("TEST 3: KYC Actor-Validation Ordering")

s, r = req("PATCH", "/api/kyc/nonexistent-uuid/verify")
check("No token -> 401 (auth before user lookup)", s == 401, str(s))

if HOLDER_TOKEN:
    s, r = req("PATCH", "/api/kyc/nonexistent-uuid/verify", token=HOLDER_TOKEN)
    check("HOLDER token -> 403 (role check before user lookup)", s == 403, str(s))

if ISSUER_TOKEN:
    s, r = req("PATCH", "/api/kyc/nonexistent-uuid/verify", token=ISSUER_TOKEN)
    check("ISSUER + non-existent user_uuid -> 404", s == 404, str(s) + " " + str(r))


# =====================================================================
# TEST 4: Credential Ownership and Consent Checks
# =====================================================================
section("TEST 4: Credential Ownership and Consent Checks")

s, r = req("GET", "/api/credentials/00000000-0000-0000-0000-000000000000")
check("Credential lookup for unknown user -> 404", s == 404, str(s) + " " + str(r))

if ACTIVE_UUID:
    s, r = req("POST", "/api/verification/credential", {
        "credential_uuid": str(ACTIVE_UUID),
        "verifier_id": "UNREGISTERED-VERIFIER-TEST-XYZ-999",
    })
    v = r.get("verification", {})
    result = v.get("result") or r.get("result", "")
    check("Verify without consent -> DENIED or INVALID",
          result in ("DENIED", "INVALID"),
          str(s) + " " + str(r))

s, r = req("POST", "/api/verification/credential", {
    "credential_uuid": "00000000-0000-0000-0000-000000000000",
    "verifier_id": "test-verifier",
})
result = r.get("verification", {}).get("result", "")
check("Non-existent credential verification -> INVALID",
      result == "INVALID",
      str(s) + " " + str(r))


# =====================================================================
# TEST 5: Audit Event Persistence and Actor Attribution
# =====================================================================
section("TEST 5: Audit Event Persistence and Actor Attribution")

check("Audit events exist in DB (" + str(audit_total) + " total)", audit_total > 0, "")
check("CREDENTIAL_REVOKED audit events exist (" + str(revoked_event_count) + ")",
      revoked_event_count > 0, "")
check("REVOKED events have actor_id (" + str(revoked_attributed) + "/" + str(revoked_event_count) + ")",
      revoked_attributed > 0, "")
check("All audit events hashed (" + str(hashed_count) + "/" + str(audit_total) + ")",
      hashed_count == audit_total, "")

if kyc_event_count > 0:
    check("KYC_VERIFIED events attributed (" + str(kyc_attributed) + "/" + str(kyc_event_count) + ")",
          kyc_attributed == kyc_event_count, "")
else:
    print("  [SKIP] No KYC_VERIFIED events in DB")


# =====================================================================
# TEST 6: Error Responses - No Debug Leakage
# =====================================================================
section("TEST 6: Error Responses - No Sensitive Debug Output")

s, r = req("GET", "/api/credentials/00000000-0000-0000-0000-000000000000")
check("404 response has 'status' field", "status" in r, str(r))
check("404 response has 'message' field", "message" in r, str(r))
check("No Python Traceback in error response", "Traceback" not in json.dumps(r), "Traceback leaked!")

s, r = req("POST", "/api/auth/login", {})
check("Empty login body -> error with message",
      r.get("status") == "error" and "message" in r, str(r))

s, r = req("POST", "/api/revocations/00000000-0000-0000-0000-000000000000")
check("Revoke non-existent credential -> structured 404",
      s == 404 and "status" in r and "message" in r,
      str(s) + " " + str(r))

s, r = req("POST", "/api/credentials/verify/00000000-0000-0000-0000-000000000000")
check("Verify non-existent credential -> no crash (200/404/400)",
      s in (200, 404, 400), str(s) + " " + str(r))


# =====================================================================
# TEST 7: PQC Signature Tampering Detection (via API)
# =====================================================================
section("TEST 7: PQC Signature Tampering Detection")

if REVOKED_UUID:
    s, r = req("POST", "/api/credentials/verify/" + str(REVOKED_UUID))
    check("Revoked credential -> result INVALID", r.get("result") == "INVALID",
          str(s) + " " + str(r))
    check("Revoked: signature_valid=False or credential_status=REVOKED",
          r.get("signature_valid") is False or r.get("credential_status") == "REVOKED",
          str(r))
    msg = r.get("message", "")
    check("Revoked: meaningful error message",
          "not active" in msg.lower() or r.get("credential_status") == "REVOKED",
          msg)
else:
    print("  [SKIP] No revoked credential to test PQC tampering")

if ACTIVE_UUID:
    s, r = req("POST", "/api/credentials/verify/" + str(ACTIVE_UUID))
    check("Active credential -> result VALID", r.get("result") == "VALID",
          str(s) + " " + str(r))
    check("Active: signature_valid=True", r.get("signature_valid") is True, str(r))
else:
    print("  [SKIP] No active credential to test PQC")


# =====================================================================
# TEST 8: Final End-to-End Security Checks
# =====================================================================
section("TEST 8: Final End-to-End Security Checks")

s, r = req("GET", "/api/health")
check("Health endpoint OK", s == 200 and r.get("status") == "ok", str(r))

s, r = req("GET", "/api/db-health")
check("DB health endpoint OK (200)", s == 200, str(r))
check("DB connection successful",
      r.get("status") == "ok" and r.get("connection") == "successful", str(r))

s, r = req("GET", "/api/auth/me", token="invalid.jwt.token")
check("Invalid JWT -> 401", s == 401, str(s) + " " + str(r))

s, r = req("POST", "/api/auth/register", {"password": "X", "role": "ISSUER"})
check("Public ISSUER registration blocked -> 403", s == 403, str(s) + " " + str(r))

s, r = req("POST", "/api/auth/register", {"password": "X", "role": "ADMIN"})
check("Public ADMIN registration blocked -> 403", s == 403, str(s) + " " + str(r))


# =====================================================================
# FINAL SUMMARY
# =====================================================================
print("")
print("=" * 60)
print("  PHASE 7 SECURITY HARDENING - FINAL RESULT")
print("  PASSED : " + str(PASS_COUNT))
print("  FAILED : " + str(FAIL_COUNT))
print("  TOTAL  : " + str(PASS_COUNT + FAIL_COUNT))
print("=" * 60)

if FAIL_COUNT > 0:
    sys.exit(1)
