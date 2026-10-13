# QuantumSafeKYC — Post-Quantum Secure Digital KYC Platform

![Post-Quantum Cryptography](https://img.shields.io/badge/Security-NIST%20FIPS%20204%20ML--DSA--65-cyan)
![Python Flask](https://img.shields.io/badge/Backend-Python%20Flask%20%2B%20SQLAlchemy-blue)
![Database](https://img.shields.io/badge/Database-PostgreSQL-336791)
![MCP](https://img.shields.io/badge/AI%20Protocol-Model%20Context%20Protocol%20(9%20Tools)-purple)
![Tests](https://img.shields.io/badge/Tests-100%25%20Passing%20(36%2F36%20E2E%2C%2037%2F37%20Hardened)-emerald)

**QuantumSafeKYC** is a production-grade digital identity and Know-Your-Customer (KYC) platform engineered with **post-quantum cryptography (PQC)** to withstand future cryptanalytic attacks from quantum computers. It implements **NIST FIPS 204 ML-DSA-65** (Module-Lattice Digital Signature Algorithm) for verifiable credential issuance, cryptographic zero-trust consent enforcement, immutable blockchain anchoring, and **Model Context Protocol (MCP)** integration for AI agent workflows.

---

## 1. Project Architecture & System Overview

```
                      +---------------------------------------+
                      |   Modern Frontend (React 19 + Vite)   |
                      |   Cyber Dashboard & MCP Live Console  |
                      +-------------------+-------------------+
                                          | HTTP / REST
                                          v
                      +---------------------------------------+
                      |      Python Flask Backend Engine      |
                      |     JWT RBAC Auth + PQC Integration   |
                      +---+---------------+---------------+---+
                          |               |               |
             +------------+       +-------+-------+       +------------+
             |                    |               |                    |
             v                    v               v                    v
     +---------------+    +---------------+ +-----------+    +---------------+
     |  PostgreSQL   |    |    liboqs     | |Blockchain |    |   MCP Server  |
     | Relational DB |    |   ML-DSA-65   | |  Anchors  |    |  Stdio + REST |
     |  SQLAlchemy   |    | NIST FIPS 204 | |  SHA-512  |    |    9 Tools    |
     +---------------+    +---------------+ +-----------+    +---------------+
```

### Key Pillars
1. **Post-Quantum Cryptography (ML-DSA-65)**:
   - Uses `liboqs-python` binding to native Open Quantum Safe C libraries.
   - Signs KYC credentials using lattice-based digital signatures immune to Shor's algorithm.
2. **Strict Role-Based Access Control (RBAC)**:
   - Three discrete roles: `HOLDER`, `ISSUER`, `ADMIN`.
   - Public registration restricted strictly to the `HOLDER` role.
   - Issuance, verification, and revocation strictly guarded by `@require_role`.
3. **Zero-Trust Consent Enforcement**:
   - Third-party verifiers (e.g., Banks, Credit Bureaus) cannot inspect or verify a credential without an active, explicit consent authorization granted by the Holder.
4. **Blockchain Anchoring & Audit Trail**:
   - SHA-512 state fingerprint of every credential anchored to an immutable blockchain ledger.
   - SHA-512 chained audit events recording authenticated actors, timestamps, and actions.
5. **Model Context Protocol (MCP) Integration**:
   - 9 standardized MCP tools discoverable by Claude, Gemini, and AI Agents.
   - Operates both as a native CLI stdio JSON-RPC server and an authenticated web REST bridge.

---

## 2. Directory Structure

```
D:\QuantumSafeKYC\
├── backend/
│   ├── .venv/                      # Python virtual environment
│   ├── .env                        # Configuration (DB URL, JWT Secret, Port)
│   ├── app.py                      # Flask main entrypoint & Blueprint registry
│   ├── models.py                   # SQLAlchemy schema (User, KYCRecord, Credential, etc.)
│   ├── auth_utils.py               # Password hashing (Werkzeug) & JWT encoding
│   ├── pqc_utils.py                # ML-DSA-65 keygen, signing & verification
│   ├── pqc_service.py              # Cryptographic service layer
│   ├── blockchain_utils.py         # SHA-512 blockchain anchoring & verification
│   ├── audit_utils.py              # Cryptographic audit logging with SHA-512 hashes
│   ├── routes/
│   │   ├── auth_routes.py          # /api/auth (register, login, me)
│   │   ├── user_routes.py          # /api/users
│   │   ├── kyc_routes.py           # /api/kyc
│   │   ├── credential_routes.py    # /api/credentials (issue, verify, revoke)
│   │   ├── consent_routes.py       # /api/consents (grant, check, revoke)
│   │   ├── verification_routes.py  # /api/verification (verifier pipeline)
│   │   ├── revocation_routes.py    # /api/revocations (registry & status)
│   │   ├── blockchain_routes.py    # /api/blockchain (anchor, verify)
│   │   └── mcp_routes.py           # /api/mcp (tools discovery & execute bridge)
│   ├── mcp_server/
│   │   ├── server.py               # Standalone MCP stdio server
│   │   ├── tools.py                # 9 Core MCP tool implementations
│   │   ├── test_e2e.py             # MCP stdio client end-to-end test
│   │   └── test_client.py          # MCP test client
│   ├── test_phase7_security.py     # 37 Phase 7 Security Hardening tests
│   ├── test_pqc.py                 # PQC ML-DSA-65 unit test
│   ├── test_audit_integrity.py     # Audit tamper-detection test
│   └── test_blockchain_integrity.py# Blockchain tamper-detection test
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Modern Cyber Dashboard & MCP Console
│   │   ├── App.css                 # Layout and interactive panels
│   │   ├── index.css               # Design system, glassmorphism & utilities
│   │   └── main.jsx
│   ├── index.html                  # Cyber typography & metadata
│   ├── vite.config.js              # Vite configuration
│   └── package.json
└── tests/
    └── test_end_to_end.py          # 36 Phase 9 Complete E2E Integration tests
```

---

## 3. Getting Started & Running the Platform

### Prerequisites
- **OS**: Windows 11 / Linux / macOS
- **Python**: 3.11+
- **PostgreSQL**: 16+ or 18+ (Default port 5432)
- **Node.js**: v18+ & npm

---

### Step 1: Database Setup
Ensure PostgreSQL is running and the database `quantumsafekyc` is created:
```sql
CREATE DATABASE quantumsafekyc;
CREATE USER quantumsafekyc_app WITH ENCRYPTED PASSWORD 'Preetham_2007';
GRANT ALL PRIVILEGES ON DATABASE quantumsafekyc TO quantumsafekyc_app;
```

---

### Step 2: Start the Backend Server
In PowerShell:
```powershell
cd D:\QuantumSafeKYC\backend
.\.venv\Scripts\Activate.ps1
python app.py
```
The Flask backend will start on: **`http://127.0.0.1:5000`**

Verify health:
```powershell
curl http://127.0.0.1:5000/api/health
```

---

### Step 3: Start the Frontend UI
In a separate terminal:
```powershell
cd D:\QuantumSafeKYC\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```
Open **`http://127.0.0.1:5173/`** in your browser.

---

### Step 4: Standalone MCP Stdio Server (for AI Agents)
To run the MCP server for Claude Desktop, Gemini, or custom LLM agents:
```powershell
cd D:\QuantumSafeKYC\backend
.\.venv\Scripts\python.exe -m mcp_server.server
```

Claude Desktop configuration snippet (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "quantumsafekyc": {
      "command": "D:\\QuantumSafeKYC\\backend\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "D:\\QuantumSafeKYC\\backend"
    }
  }
}
```

---

## 4. Test Suite Execution & Verification

Run all test suites using the virtual environment Python:

| Test Suite | File | Coverage | Result |
| :--- | :--- | :--- | :--- |
| **Phase 9 End-to-End** | `tests/test_end_to_end.py` | Complete KYC, PQC, Consent, Blockchain & MCP flow | **36 / 36 PASS** |
| **Phase 7 Security Hardening** | `backend/test_phase7_security.py` | RBAC, 409 duplicates, Auth order, Debug leaks | **37 / 37 PASS** |
| **PQC Algorithm Integrity** | `backend/test_pqc.py` | ML-DSA-65 keygen, signing & tamper rejection | **PASS** |
| **Blockchain Anchor Integrity** | `backend/test_blockchain_integrity.py` | SHA-512 state anchoring & tamper detection | **PASS** |
| **Audit Log Integrity** | `backend/test_audit_integrity.py` | SHA-512 hash chain tamper detection | **PASS** |
| **MCP stdio Integration** | `backend/mcp_server/test_e2e.py` | Stdio client handshake & 9 tools execution | **PASS** |

Run tests command:
```powershell
# Run complete End-to-End test suite
.\.venv\Scripts\python.exe tests\test_end_to_end.py

# Run Phase 7 security tests
.\.venv\Scripts\python.exe backend\test_phase7_security.py
```

---

## 5. Standardized MCP Tool Catalog (9 Tools)

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `system_status` | none | Checks health and connection of the MCP server |
| `get_user_tool` | `user_uuid` | Fetches user identity, role, and status |
| `get_credential_tool` | `credential_uuid` | Retrieves PQC credential metadata and hash |
| `check_consent_tool` | `user_uuid`, `credential_uuid`, `verifier_id`, `purpose` | Verifies active consent authorization |
| `verify_pqc_tool` | `credential_uuid` | Validates NIST FIPS 204 ML-DSA-65 signature |
| `verify_credential_tool` | `credential_uuid`, `verifier_id`, `purpose` | Complete pipeline (Consent + PQC + Revocation) |
| `check_revocation_tool` | `credential_uuid` | Checks revocation status and reason |
| `verify_blockchain_tool` | `credential_uuid` | Verifies integrity against blockchain anchor |
| `get_verification_history_tool` | `credential_uuid` | Returns complete audit verification history |

---

## 6. End-to-End Workflow Demonstration

1. **Register**: New user registers with `role: "HOLDER"`.
2. **KYC Submit**: Holder submits KYC profile (`verification_level: "ENHANCED"`).
3. **KYC Verify**: Authorized Issuer reviews and verifies KYC record.
4. **Issue PQC Credential**: Issuer signs credential using **ML-DSA-65**.
5. **Blockchain Anchor**: Credential hash anchored to immutable blockchain ledger.
6. **Consent**: Holder explicitly grants consent for `BANK-VERIFIER-001`.
7. **Verification**: Verifier validates credential against consent, PQC signature, and blockchain anchor.
8. **Revocation**: Issuer revokes credential; all future verifications return `409` or `INVALID`.
9. **MCP Agent Inspection**: AI Agent queries status and verification history via MCP tools.
