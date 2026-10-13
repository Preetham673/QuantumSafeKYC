"""
test_kyc_auth_rendering.py
---------------------------
Validates backend enforcement of KYC authentication and RBAC requirements.
These tests mirror the 5 frontend bugs that were fixed and verify that the
backend independently enforces access regardless of frontend state.

Run: python tests/test_kyc_auth_rendering.py
"""

import json
import sys
import time
import uuid
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
    marker = "PASS" if condition else "FAIL"
    print(f"  [{marker}]  {label}")
    if not condition and detail:
        print(f"           Detail: {str(detail)[:160]}")
    if condition:
        PASS += 1
    else:
        FAIL += 1


def section(name):
    print("\n" + "=" * 70)
    print(f"  {name}")
    print("=" * 70)


def run():
    global PASS, FAIL

    print("=" * 70)
    print("  KYC Auth Rendering - Backend Enforcement Test Suite")
    print("  Mirrors the 5 frontend bugs fixed in App.jsx")
    print("=" * 70)

    # ------------------------------------------------------------------ #
    # SETUP: Create a fresh HOLDER for this test run                       #
    # ------------------------------------------------------------------ #
    section("SETUP: Register & login a fresh test HOLDER")

    password = "TestHolder@9999!"
    status, reg = request("POST", "/auth/register", {"password": password, "role": "HOLDER"})
    check("Register new HOLDER returns 201", status == 201, reg)

    holder_uuid = reg.get("user", {}).get("user_uuid", "")
    check("Registration response contains user_uuid", bool(holder_uuid), reg)

    status, login = request("POST", "/auth/login", {"user_uuid": holder_uuid, "password": password})
    check("HOLDER login returns 200", status == 200, login)

    holder_token = login.get("access_token", "")
    holder_role  = login.get("user", {}).get("role", "")
    check("Login response contains access_token", bool(holder_token), login)
    check("Login response role == HOLDER", holder_role == "HOLDER", holder_role)

    # Known ISSUER from earlier setup
    issuer_uuid = "813502d0-5aed-4e60-a2bc-371316a63c1d"
    issuer_pw   = "Issuer@1234!"
    status, issuer_login = request("POST", "/auth/login", {"user_uuid": issuer_uuid, "password": issuer_pw})
    check("ISSUER login returns 200", status == 200, issuer_login)
    issuer_token = issuer_login.get("access_token", "")
    check("ISSUER access_token obtained", bool(issuer_token), issuer_login)

    # ------------------------------------------------------------------ #
    # BUG 2 FIX: KYC submit must reject unauthenticated requests          #
    # ------------------------------------------------------------------ #
    section("BUG 2 FIX: KYC submit must require authentication (no token)")

    status, data = request("POST", "/kyc/submit", {
        "verification_level": "BASIC",
        "full_name": "Ghost User",
        "date_of_birth": "1990-01-01",
        "nationality": "Unknown",
        "document_type": "PASSPORT",
        "document_number": "GHOST999",
    })
    check("POST /kyc/submit with NO token -> 401 or 403", status in (401, 403), data)

    status, data = request("GET", "/kyc/me")
    check("GET /kyc/me with NO token -> 401 or 403", status in (401, 403), data)

    # ------------------------------------------------------------------ #
    # BUG 3 FIX: Issuer-only endpoints must reject HOLDER tokens          #
    # ------------------------------------------------------------------ #
    section("BUG 3 FIX: ISSUER review endpoints must reject HOLDER token")

    status, data = request("GET", "/kyc/pending", token=holder_token)
    check("GET /kyc/pending with HOLDER token -> 403", status == 403, data)

    random_uuid = str(uuid.uuid4())
    status, data = request("PATCH", f"/kyc/{random_uuid}/review",
                           {"decision": "VERIFY", "confirmed_evidence_reviewed": True},
                           token=holder_token)
    check("PATCH /kyc/<uuid>/review with HOLDER token -> 403", status == 403, data)

    # ------------------------------------------------------------------ #
    # Additional RBAC: ISSUER cannot submit a KYC as a HOLDER             #
    # ------------------------------------------------------------------ #
    section("Additional RBAC: ISSUER cannot self-submit as a HOLDER")

    status, data = request("POST", "/kyc/submit", {
        "verification_level": "BASIC",
        "full_name": "Rogue Issuer",
        "date_of_birth": "1985-06-15",
        "nationality": "Unknown",
        "document_type": "NATIONAL_ID",
        "document_number": "ROGUE001",
    }, token=issuer_token)
    check("POST /kyc/submit with ISSUER token -> 403", status == 403, data)

    # ------------------------------------------------------------------ #
    # BUG 4 FIX: Tampered/stale token must not grant access               #
    # ------------------------------------------------------------------ #
    section("BUG 4 FIX: Stale/tampered token must not grant access")

    stale_token = holder_token + "TAMPERED"
    status, data = request("GET", "/kyc/me", token=stale_token)
    check("GET /kyc/me with tampered token -> 401 or 403", status in (401, 403), data)

    status, data = request("GET", "/kyc/pending", token=stale_token)
    check("GET /kyc/pending with tampered token -> 401 or 403", status in (401, 403), data)

    # ------------------------------------------------------------------ #
    # VALID FLOW: HOLDER submits, ISSUER reviews                          #
    # ------------------------------------------------------------------ #
    section("VALID FLOW: HOLDER submits KYC, ISSUER lists and reviews")

    status, data = request("POST", "/kyc/submit", {
        "verification_level": "BASIC",
        "full_name": "Test Holder Name",
        "date_of_birth": "1992-07-22",
        "nationality": "United Kingdom",
        "document_type": "PASSPORT",
        "document_number": f"TH{holder_uuid[:6].upper()}",
    }, token=holder_token)
    check("HOLDER POST /kyc/submit -> 201 success", status == 201, data)
    check("Submitted KYC status is PENDING", data.get("kyc", {}).get("verification_status") == "PENDING", data)

    status, data = request("GET", "/kyc/me", token=holder_token)
    check("HOLDER GET /kyc/me -> 200 shows PENDING record", status == 200, data)
    check("GET /kyc/me has_record == True", data.get("has_record") is True, data)
    check("GET /kyc/me full_name matches submitted value",
          data.get("kyc", {}).get("full_name") == "Test Holder Name", data)

    status, data = request("GET", "/kyc/pending", token=issuer_token)
    check("ISSUER GET /kyc/pending -> 200", status == 200, data)
    count = data.get("count", 0)
    check("Pending queue count >= 1", count >= 1, f"count={count}")

    status, data = request("PATCH", f"/kyc/{holder_uuid}/review", {
        "decision": "VERIFY",
        "notes": "Auth test: documents verified.",
        "confirmed_evidence_reviewed": True,
    }, token=issuer_token)
    check("ISSUER PATCH /kyc/<uuid>/review -> 200", status == 200, data)
    check("Review sets status to VERIFIED",
          data.get("kyc", {}).get("verification_status") == "VERIFIED", data)

    status, data = request("GET", "/kyc/me", token=holder_token)
    check("HOLDER GET /kyc/me after review -> VERIFIED",
          data.get("kyc", {}).get("verification_status") == "VERIFIED", data)

    # ------------------------------------------------------------------ #
    # BUG 5 FIX: No KYC data exposed without token on any path            #
    # ------------------------------------------------------------------ #
    section("BUG 5 FIX: No KYC data exposed without token on any path")

    status, data = request("GET", f"/kyc/{holder_uuid}")
    check("GET /kyc/<uuid> (no token) -> 401/403", status in (401, 403), data)

    status, data = request("GET", "/kyc/pending")
    check("GET /kyc/pending (no token) -> 401/403", status in (401, 403), data)

    status, data = request("PATCH", f"/kyc/{holder_uuid}/review",
                           {"decision": "REJECT", "reason": "Unauthenticated attempt"})
    check("PATCH /kyc/<uuid>/review (no token) -> 401/403", status in (401, 403), data)

    # ------------------------------------------------------------------ #
    # SUMMARY                                                             #
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 70)
    total = PASS + FAIL
    print(f"  Results: {PASS}/{total} passed  |  {FAIL} failed")
    print("=" * 70)
    return FAIL == 0


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
