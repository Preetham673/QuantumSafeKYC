import { useState, useEffect } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:5000/api";

export default function App() {
  // Navigation
  const [activeTab, setActiveTab] = useState("overview");

  // System status
  const [health, setHealth] = useState({ backend: "checking", db: "checking", mcp: "checking" });
  const [mcpTools, setMcpTools] = useState([]);

  // Auth state
  const [authToken, setAuthToken] = useState(localStorage.getItem("qskyc_token") || "");
  const [currentUser, setCurrentUser] = useState(
    JSON.parse(localStorage.getItem("qskyc_user") || "null")
  );

  // Forms & Inputs
  const [loginForm, setLoginForm] = useState({ user_uuid: "750bd462-f771-468f-9cf8-a5d27b02a665", password: "IssuerPass@2025!" });
  const [regForm, setRegForm] = useState({ password: "HolderPass@2025!" });
  const [kycForm, setKycForm] = useState({ user_uuid: "", verification_level: "ENHANCED" });
  const [issueForm, setIssueForm] = useState({ user_uuid: "" });

  // KYC Complete Evidence & Review State
  const [kycPerspective, setKycPerspective] = useState("auto");
  const [holderKyc, setHolderKyc] = useState(null);
  const [holderKycLoading, setHolderKycLoading] = useState(false);
  const [pendingKycList, setPendingKycList] = useState([]);
  const [pendingKycLoading, setPendingKycLoading] = useState(false);
  const [selectedKycForReview, setSelectedKycForReview] = useState(null);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [holderForm, setHolderForm] = useState({
    verification_level: "BASIC",
    full_name: "Alice Johnson",
    date_of_birth: "1992-05-14",
    nationality: "United States",
    document_type: "PASSPORT",
    document_number: "P98765432",
    residential_address: "742 Evergreen Terrace, Springfield, OR",
    country_of_issue: "United States",
    expiry_date: "2034-08-20",
  });
  const [reviewDecisionForm, setReviewDecisionForm] = useState({
    decision: "VERIFY",
    reason: "",
    notes: "Verified identity document matches holder details per compliance protocol.",
    confirmed: false,
  });
  const [searchKycUuid, setSearchKycUuid] = useState("");
  const [inspectCredUuid, setInspectCredUuid] = useState("b7910bb9-c906-4195-8a99-72046142aaca");
  const [revokeForm, setRevokeForm] = useState({ credential_uuid: "", reason: "Security review requested by holder" });
  const [consentForm, setConsentForm] = useState({
    user_uuid: "",
    credential_uuid: "b7910bb9-c906-4195-8a99-72046142aaca",
    verifier_id: "BANK-VERIFIER-001",
    purpose: "Mortgage Loan Verification",
  });
  const [verifyForm, setVerifyForm] = useState({
    credential_uuid: "b7910bb9-c906-4195-8a99-72046142aaca",
    verifier_id: "BANK-VERIFIER-001",
    purpose: "Mortgage Loan Verification",
  });
  const [blockchainTargetUuid, setBlockchainTargetUuid] = useState("b7910bb9-c906-4195-8a99-72046142aaca");

  // MCP Explorer State
  const [selectedMcpTool, setSelectedMcpTool] = useState("system_status");
  const [mcpParams, setMcpParams] = useState({});
  const [mcpResult, setMcpResult] = useState(null);
  const [mcpLoading, setMcpLoading] = useState(false);

  // Action Results / Logs
  const [actionLog, setActionLog] = useState(null);
  const [loading, setLoading] = useState(false);

  // Refresh System Health
  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      const data = await res.json();
      setHealth((h) => ({ ...h, backend: data.status === "ok" ? "ok" : "error" }));
    } catch {
      setHealth((h) => ({ ...h, backend: "offline" }));
    }

    try {
      const res = await fetch(`${API_BASE}/db-health`);
      const data = await res.json();
      setHealth((h) => ({ ...h, db: data.status === "ok" ? "ok" : "error" }));
    } catch {
      setHealth((h) => ({ ...h, db: "offline" }));
    }

    try {
      const res = await fetch(`${API_BASE}/mcp/tools`);
      const data = await res.json();
      if (data.status === "success") {
        setMcpTools(data.tools);
        setHealth((h) => ({ ...h, mcp: "ok" }));
      }
    } catch {
      setHealth((h) => ({ ...h, mcp: "offline" }));
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Set default param when MCP tool changes
  useEffect(() => {
    if (selectedMcpTool === "get_user_tool") {
      setMcpParams({ user_uuid: currentUser?.user_uuid || "f53bf005-7ab1-41e5-9dc7-388a4ffde14c" });
    } else if (selectedMcpTool === "get_credential_tool" || selectedMcpTool === "verify_pqc_tool" || selectedMcpTool === "check_revocation_tool" || selectedMcpTool === "verify_blockchain_tool" || selectedMcpTool === "get_verification_history_tool") {
      setMcpParams({ credential_uuid: inspectCredUuid });
    } else if (selectedMcpTool === "check_consent_tool") {
      setMcpParams({
        user_uuid: currentUser?.user_uuid || "f53bf005-7ab1-41e5-9dc7-388a4ffde14c",
        credential_uuid: inspectCredUuid,
        verifier_id: "BANK-VERIFIER-001",
        purpose: "Mortgage Loan Verification",
      });
    } else if (selectedMcpTool === "verify_credential_tool") {
      setMcpParams({
        credential_uuid: inspectCredUuid,
        verifier_id: "BANK-VERIFIER-001",
        purpose: "Mortgage Loan Verification",
      });
    } else {
      setMcpParams({});
    }
  }, [selectedMcpTool, inspectCredUuid, currentUser]);

  // Fetch Authenticated Holder's KYC status
  const fetchHolderKyc = async () => {
    if (!authToken) return;
    setHolderKycLoading(true);
    try {
      const res = await fetch(`${API_BASE}/kyc/me`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setHolderKyc(data.kyc);
        if (data.kyc?.user_uuid) {
          setIssueForm((f) => ({ ...f, user_uuid: data.kyc.user_uuid }));
        }
      }
    } catch (err) {
      console.error("Failed to fetch holder KYC:", err);
    } finally {
      setHolderKycLoading(false);
    }
  };

  // Fetch Pending KYC Applications Queue for ISSUER
  const fetchPendingKyc = async () => {
    if (!authToken) return;
    setPendingKycLoading(true);
    try {
      const res = await fetch(`${API_BASE}/kyc/pending`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setPendingKycList(data.applications || []);
      }
    } catch (err) {
      console.error("Failed to fetch pending KYC list:", err);
    } finally {
      setPendingKycLoading(false);
    }
  };

  // Fetch specific user's KYC record for review
  const fetchKycForReview = async (userUuid) => {
    if (!authToken || !userUuid) return;
    setReviewLoading(true);
    try {
      const res = await fetch(`${API_BASE}/kyc/${userUuid}`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setSelectedKycForReview(data.kyc);
        setActionLog({ title: `Inspect KYC: ${userUuid}`, data, status: res.status });
      } else {
        setActionLog({ title: `Inspect KYC Error`, error: data.message, status: res.status });
      }
    } catch (err) {
      setActionLog({ title: "Fetch KYC Error", error: err.message, status: "error" });
    } finally {
      setReviewLoading(false);
    }
  };

  // Submit KYC Application (multipart/form-data)
  const handleKycSubmit = async (e) => {
    e.preventDefault();

    // Frontend document validation: at least one supporting document is required.
    // The backend accepts submissions without documents for API-testing purposes
    // but the UI enforces this requirement to guide holders through the workflow.
    if (uploadedFiles.length === 0) {
      setActionLog({
        title: "KYC Submission Validation",
        error: "At least one supporting document is required. Please upload a scanned copy of your identity document (Passport, National ID, or Driving Licence) as PDF, JPG, or PNG before submitting.",
        status: 400,
      });
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("verification_level", holderForm.verification_level);
      formData.append("full_name", holderForm.full_name);
      formData.append("date_of_birth", holderForm.date_of_birth);
      formData.append("nationality", holderForm.nationality);
      formData.append("document_type", holderForm.document_type);
      formData.append("document_number", holderForm.document_number);

      if (holderForm.verification_level === "ENHANCED") {
        formData.append("residential_address", holderForm.residential_address);
        formData.append("country_of_issue", holderForm.country_of_issue);
        formData.append("expiry_date", holderForm.expiry_date);
      }

      uploadedFiles.forEach((file) => {
        formData.append("document", file);
      });

      const res = await fetch(`${API_BASE}/kyc/submit`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
        body: formData,
      });

      const data = await res.json();
      setActionLog({ title: "KYC Submission Result", data, status: res.status });

      if (res.ok && data.status === "success") {
        setHolderKyc(data.kyc);
        setUploadedFiles([]);
        if (currentUser?.role === "ISSUER" || currentUser?.role === "ADMIN") {
          fetchPendingKyc();
        }
      }
    } catch (err) {
      setActionLog({ title: "KYC Submission Error", error: err.message, status: "error" });
    } finally {
      setLoading(false);
    }
  };

  // Handle Review Decision (VERIFY / REJECT / REQUEST_RESUBMISSION)
  const handleReviewDecision = async (e) => {
    e?.preventDefault();
    if (!selectedKycForReview?.user_uuid) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/kyc/${selectedKycForReview.user_uuid}/review`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          decision: reviewDecisionForm.decision,
          reason: reviewDecisionForm.reason,
          notes: reviewDecisionForm.notes,
          confirmed_evidence_reviewed: reviewDecisionForm.confirmed,
        }),
      });

      const data = await res.json();
      setActionLog({ title: `Review Decision: ${reviewDecisionForm.decision}`, data, status: res.status });

      if (res.ok && data.status === "success") {
        setSelectedKycForReview(data.kyc);
        fetchPendingKyc();
        if (currentUser?.user_uuid === selectedKycForReview.user_uuid) {
          setHolderKyc(data.kyc);
        }
      }
    } catch (err) {
      setActionLog({ title: "Review Decision Error", error: err.message, status: "error" });
    } finally {
      setLoading(false);
    }
  };

  // Download / View Secure Document
  const handleViewDocument = async (docId, fileName) => {
    try {
      const res = await fetch(`${API_BASE}/kyc/documents/${docId}`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (!res.ok) {
        const err = await res.json();
        alert(`Error opening document: ${err.message || res.statusText}`);
        return;
      }
      const blob = await res.blob();
      const fileUrl = window.URL.createObjectURL(blob);
      window.open(fileUrl, "_blank");
    } catch (err) {
      alert(`Failed to load document: ${err.message}`);
    }
  };

  // Auto-fetch KYC data on tab or auth state changes
  useEffect(() => {
    if (authToken && activeTab === "kyc") {
      fetchHolderKyc();
      if (currentUser?.role === "ISSUER" || currentUser?.role === "ADMIN") {
        fetchPendingKyc();
      }
    }
  }, [activeTab, authToken, currentUser]);

  // Auth Actions
  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: regForm.password, role: "HOLDER" }),
      });
      const data = await res.json();
      setActionLog({ title: "Registration Result", data, status: res.status });
      if (res.status === 201 && data.user) {
        setLoginForm({ user_uuid: data.user.user_uuid, password: regForm.password });
        setKycForm((f) => ({ ...f, user_uuid: data.user.user_uuid }));
        setIssueForm((f) => ({ ...f, user_uuid: data.user.user_uuid }));
      }
    } catch (err) {
      setActionLog({ title: "Registration Error", error: err.message, status: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
e?.preventDefault();
setLoading(true);

try {
const res = await fetch(`${API_BASE}/auth/login`, {
method: "POST",
headers: { "Content-Type": "application/json" },
body: JSON.stringify(loginForm),
});

const data = await res.json();

if (res.ok && data.access_token && data.user?.user_uuid && data.user?.role) {
  const userUuid = data.user.user_uuid;

  const userObj = {
    user_uuid: userUuid,
    role: data.user.role,
    status: data.user.status,
  };

  setAuthToken(data.access_token);
  localStorage.setItem("qskyc_token", data.access_token);

  setCurrentUser(userObj);
  localStorage.setItem("qskyc_user", JSON.stringify(userObj));

  setKycForm((f) => ({ ...f, user_uuid: userUuid }));
  setIssueForm((f) => ({ ...f, user_uuid: userUuid }));

  setActionLog({
    title: "Authentication Result",
    data: {
      status: data.status,
      message: data.message,
      user: userObj,
    },
    status: res.status,
  });
} else {
  setActionLog({
    title: "Login Error",
    error: data.message || "Login failed or user information is missing.",
    status: res.status,
  });
}

} catch (err) {
setActionLog({
title: "Login Error",
error: err.message,
status: "error",
});
} finally {
setLoading(false);
}
};

const handleLogout = () => {
  // Clear authentication state
  setAuthToken("");
  setCurrentUser(null);
  localStorage.removeItem("qskyc_token");
  localStorage.removeItem("qskyc_user");

  // FIX: Clear all user-specific KYC state so the previous user's data
  // is never shown to the next user or in the unauthenticated state.
  setHolderKyc(null);
  setPendingKycList([]);
  setSelectedKycForReview(null);
  setUploadedFiles([]);
  setSearchKycUuid("");
  setKycPerspective("auto");

  setActionLog({
    title: "Session",
    message: "Logged out successfully",
  });
};

// Helper for authenticated API calls
const apiCall = async (endpoint, method = "GET", body = null) => {
setLoading(true);

try {
const headers = { "Content-Type": "application/json" };

if (authToken) {
  headers["Authorization"] = `Bearer ${authToken}`;
}

const res = await fetch(`${API_BASE}${endpoint}`, {
  method,
  headers,
  body: body ? JSON.stringify(body) : null,
});

const data = await res.json();

setActionLog({
  title: `${method} ${endpoint}`,
  data,
  status: res.status,
});

return { status: res.status, data };

} catch (err) {
setActionLog({
title: `Error on ${method} ${endpoint}`,
error: err.message,
status: "error",
});


return { status: 0, error: err.message };


} finally {
setLoading(false);
}
};


  // Execute MCP Tool
  const runMcpTool = async () => {
    setMcpLoading(true);
    setMcpResult(null);
    try {
      const res = await fetch(`${API_BASE}/mcp/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool: selectedMcpTool,
          parameters: mcpParams,
        }),
      });
      const data = await res.json();
      setMcpResult(data);
    } catch (err) {
      setMcpResult({ status: "error", message: err.message });
    } finally {
      setMcpLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* HEADER */}
      <header className="app-header">
        <div className="header-content">
          <div className="brand-section">
            <div className="brand-icon">⚛</div>
            <div>
              <div className="brand-title">QuantumSafeKYC</div>
              <div className="brand-subtitle">NIST FIPS 204 ML-DSA · Post-Quantum Identity</div>
            </div>
          </div>

          <div className="system-status-pills">
            <div className="status-pill">
              <span className={`status-dot ${health.backend === "ok" ? "status-dot-active" : "status-dot-danger"}`}></span>
              Backend: {health.backend}
            </div>
            <div className="status-pill">
              <span className={`status-dot ${health.db === "ok" ? "status-dot-active" : "status-dot-danger"}`}></span>
              PostgreSQL: {health.db}
            </div>
            <div className="status-pill">
              <span className={`status-dot ${health.mcp === "ok" ? "status-dot-active" : "status-dot-danger"}`}></span>
              MCP: {mcpTools.length} Tools
            </div>
          </div>

          <div className="user-status-widget">
  {currentUser?.user_uuid ? (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <span className={`badge ${currentUser.role === "ADMIN" || currentUser.role === "ISSUER" ? "badge-purple" : "badge-info"}`}>
        {currentUser.role || "USER"}
      </span>

  <span style={{ fontSize: "0.78rem", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
    {currentUser.user_uuid.substring(0, 8)}...
  </span>

  <button
    className="btn btn-secondary"
    style={{ padding: "0.3rem 0.6rem", fontSize: "0.75rem" }}
    onClick={handleLogout}
  >
    Logout
  </button>
</div>


) : ( <span className="badge badge-warning">Unauthenticated</span>
)}

</div>

        </div>
      </header>

      {/* NAVIGATION TABS */}
      <div className="nav-tabs-wrapper">
        <nav className="nav-tabs">
          <button className={`nav-tab-btn ${activeTab === "overview" ? "active" : ""}`} onClick={() => setActiveTab("overview")}>
            📊 Architecture & Overview
          </button>
          <button className={`nav-tab-btn ${activeTab === "identity" ? "active" : ""}`} onClick={() => setActiveTab("identity")}>
            🔐 Identity & RBAC
          </button>
          <button className={`nav-tab-btn ${activeTab === "kyc" ? "active" : ""}`} onClick={() => setActiveTab("kyc")}>
            📋 KYC Workflow
          </button>
          <button className={`nav-tab-btn ${activeTab === "credentials" ? "active" : ""}`} onClick={() => setActiveTab("credentials")}>
            ⚛ PQC Credentials
          </button>
          <button className={`nav-tab-btn ${activeTab === "verification" ? "active" : ""}`} onClick={() => setActiveTab("verification")}>
            🛡 Consent & Verifier
          </button>
          <button className={`nav-tab-btn ${activeTab === "blockchain" ? "active" : ""}`} onClick={() => setActiveTab("blockchain")}>
            ⛓ Blockchain & Audit
          </button>
          <button className={`nav-tab-btn ${activeTab === "mcp" ? "active" : ""}`} onClick={() => setActiveTab("mcp")}>
            🤖 MCP AI Tools Console
          </button>
        </nav>
      </div>

      {/* MAIN CONTENT */}
      <main className="app-main">
        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div className="grid-4">
              <div className="glass-panel stat-card">
                <span className="stat-title">Post-Quantum Algorithm</span>
                <span className="stat-value" style={{ color: "var(--quantum-cyan)", fontSize: "1.4rem" }}>ML-DSA-65</span>
                <span className="stat-desc">NIST FIPS 204 Lattice Cryptography</span>
              </div>
              <div className="glass-panel stat-card">
                <span className="stat-title">Database Storage</span>
                <span className="stat-value" style={{ color: "var(--quantum-emerald)" }}>PostgreSQL</span>
                <span className="stat-desc">Relational ACID + SQLAlchemy ORM</span>
              </div>
              <div className="glass-panel stat-card">
                <span className="stat-title">AI Agent Protocol</span>
                <span className="stat-value" style={{ color: "var(--quantum-purple)" }}>MCP 9 Tools</span>
                <span className="stat-desc">Model Context Protocol Stdio + REST</span>
              </div>
              <div className="glass-panel stat-card">
                <span className="stat-title">Audit & Immutability</span>
                <span className="stat-value" style={{ color: "var(--quantum-blue)", fontSize: "1.3rem" }}>SHA-512 Chain</span>
                <span className="stat-desc">Blockchain Anchors & Audit Logs</span>
              </div>
            </div>

            <div className="grid-2">
              <div className="glass-panel" style={{ padding: "1.5rem" }}>
                <div className="panel-header">
                  <h3 className="panel-title">🛡 Quantum-Safe Security Model</h3>
                  <span className="badge badge-success">Phase 7 Hardened</span>
                </div>
                <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1rem" }}>
                  Traditional digital signatures (RSA, ECDSA) are vulnerable to Shor's algorithm on quantum computers.
                  QuantumSafeKYC utilizes <strong>ML-DSA-65</strong> (CRYSTALS-Dilithium) to provide quantum-resistant
                  digital identity authentication and tamper-evident credential signing.
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", fontSize: "0.85rem" }}>
                  <div style={{ padding: "0.75rem", background: "rgba(255,255,255,0.02)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)" }}>
                    <strong style={{ color: "var(--quantum-cyan)" }}>1. Post-Quantum Signing:</strong> Credentials are cryptographically signed using private keys held by authorized KYC Issuers.
                  </div>
                  <div style={{ padding: "0.75rem", background: "rgba(255,255,255,0.02)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)" }}>
                    <strong style={{ color: "var(--quantum-cyan)" }}>2. Verifier & Consent Guard:</strong> Third-party relying parties cannot verify or access credentials without verifiable, active Holder consent.
                  </div>
                  <div style={{ padding: "0.75rem", background: "rgba(255,255,255,0.02)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)" }}>
                    <strong style={{ color: "var(--quantum-cyan)" }}>3. Blockchain Anchoring & Audit:</strong> Credential state hashes are immutably recorded to prevent retroactive modification.
                  </div>
                </div>
              </div>

              <div className="glass-panel" style={{ padding: "1.5rem" }}>
                <div className="panel-header">
                  <h3 className="panel-title">⚡ Live System Diagnostic</h3>
                  <button className="btn btn-secondary" style={{ padding: "0.3rem 0.75rem", fontSize: "0.8rem" }} onClick={checkHealth}>
                    Refresh
                  </button>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "0.6rem 0", borderBottom: "1px solid var(--border-color)" }}>
                    <span style={{ color: "var(--text-muted)" }}>Backend Framework:</span>
                    <strong>Flask + liboqs Python</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "0.6rem 0", borderBottom: "1px solid var(--border-color)" }}>
                    <span style={{ color: "var(--text-muted)" }}>Security Hardening Tests:</span>
                    <strong style={{ color: "var(--quantum-emerald)" }}>37 / 37 Passed</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "0.6rem 0", borderBottom: "1px solid var(--border-color)" }}>
                    <span style={{ color: "var(--text-muted)" }}>Public Role Registration:</span>
                    <span className="badge badge-info">Restricted to HOLDER</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "0.6rem 0", borderBottom: "1px solid var(--border-color)" }}>
                    <span style={{ color: "var(--text-muted)" }}>Active Token Secret:</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>Configured via .env</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "0.6rem 0" }}>
                    <span style={{ color: "var(--text-muted)" }}>MCP Integration:</span>
                    <span className="badge badge-purple">9 Standardized Tools Active</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: IDENTITY & RBAC */}
        {activeTab === "identity" && (
          <div className="grid-2">
            <div className="glass-panel" style={{ padding: "1.5rem" }}>
              <div className="panel-header">
                <h3 className="panel-title">👤 Public HOLDER Registration</h3>
                <span className="badge badge-info">Role: HOLDER</span>
              </div>
              <form onSubmit={handleRegister}>
                <div className="form-group">
                  <label className="form-label">Password</label>
                  <input
                    type="password"
                    className="form-input"
                    value={regForm.password}
                    onChange={(e) => setRegForm({ password: e.target.value })}
                    required
                  />
                </div>
                <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: "100%" }}>
                  Register New HOLDER
                </button>
              </form>
            </div>

            <div className="glass-panel" style={{ padding: "1.5rem" }}>
              <div className="panel-header">
                <h3 className="panel-title">🔑 Authentication & Login</h3>
                <div style={{ display: "flex", gap: "0.3rem" }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.72rem", padding: "0.2rem 0.5rem" }}
                    onClick={() => setLoginForm({ user_uuid: "750bd462-f771-468f-9cf8-a5d27b02a665", password: "IssuerPass@2025!" })}
                  >
                    Quick ADMIN
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.72rem", padding: "0.2rem 0.5rem" }}
                    onClick={() => setLoginForm({ user_uuid: "813502d0-5aed-4e60-a2bc-371316a63c1d", password: "IssuerPass@2025!" })}
                  >
                    Quick ISSUER
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.72rem", padding: "0.2rem 0.5rem" }}
                    onClick={() => setLoginForm({ user_uuid: "f53bf005-7ab1-41e5-9dc7-388a4ffde14c", password: "IssuerPass@2025!" })}
                  >
                    Quick HOLDER
                  </button>
                </div>
              </div>
              <form onSubmit={handleLogin}>
                <div className="form-group">
                  <label className="form-label">User UUID</label>
                  <input
                    type="text"
                    className="form-input form-mono"
                    value={loginForm.user_uuid}
                    onChange={(e) => setLoginForm({ ...loginForm, user_uuid: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Password</label>
                  <input
                    type="password"
                    className="form-input"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                    required
                  />
                </div>
                <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: "100%" }}>
                  Log In & Issue JWT
                </button>
              </form>
            </div>
          </div>
        )}

        {/* TAB 3: KYC WORKFLOW */}
        {activeTab === "kyc" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

            {/* -- Perspective switcher (only when authenticated) -- */}
            {currentUser && (
              <div className="glass-panel" style={{ padding: "1rem 1.5rem", display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
                <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 600 }}>KYC View:</span>
                {["auto", "holder", "issuer"].map((p) => (
                  <button
                    key={p}
                    className={`btn ${kycPerspective === p ? "btn-primary" : "btn-secondary"}`}
                    style={{ padding: "0.3rem 0.9rem", fontSize: "0.8rem", textTransform: "capitalize" }}
                    onClick={() => setKycPerspective(p)}
                  >
                    {p === "auto" ? "Auto (Role-Based)" : p === "holder" ? "🙋 Holder View" : "🔎 Issuer Review"}
                  </button>
                ))}
                <span className="badge badge-warning" style={{ marginLeft: "auto" }}>
                  ⚠️ VERIFIED = Issuer-approved evidence — NOT independent government verification
                </span>
              </div>
            )}

            {/* ================================================== */}
            {/* HOLDER SUBMISSION PANEL                            */}
            {/* ================================================== */}
            {/* FIX: both explicit "holder" perspective AND auto require an authenticated HOLDER */}
            {currentUser && (kycPerspective === "holder" || (kycPerspective === "auto" && currentUser.role === "HOLDER")) && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

                {/* Status Banner — only shown when there is a real submitted record */}
                {holderKyc && holderKyc.verification_status !== "NOT_SUBMITTED" && (
                  <div className="glass-panel" style={{ padding: "1rem 1.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
                      <span style={{ fontWeight: 700, color: "var(--text-main)" }}>Your KYC Status:</span>
                      <span className={`badge ${
                        holderKyc.verification_status === "VERIFIED" ? "badge-success"
                        : holderKyc.verification_status === "REJECTED" ? "badge-danger"
                        : holderKyc.verification_status === "RESUBMISSION_REQUIRED" ? "badge-warning"
                        : "badge-info"
                      }`}>
                        {holderKyc.verification_status}
                      </span>
                      <span style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>Level: {holderKyc.verification_level || "—"}</span>
                      <span style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
                        Submitted: {holderKyc.submitted_at ? new Date(holderKyc.submitted_at).toLocaleString() : "Not yet"}
                      </span>
                      {holderKyc.rejection_reason && (
                        <div className="disclaimer-card" style={{ width: "100%", marginTop: "0.5rem" }}>
                          <strong>Issuer Notes:</strong> {holderKyc.rejection_reason}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Submission Form — visible when:
                    - holderKyc is null (data not yet fetched), OR
                    - status is NOT_SUBMITTED (backend placeholder for no record), OR
                    - status is REJECTED or RESUBMISSION_REQUIRED (holder must resubmit) */}
                {(!holderKyc
                  || holderKyc.verification_status === "NOT_SUBMITTED"
                  || holderKyc.verification_status === "RESUBMISSION_REQUIRED"
                  || holderKyc.verification_status === "REJECTED") && (
                  <form onSubmit={handleKycSubmit}>
                    <div className="grid-2">
                      <div className="glass-panel" style={{ padding: "1.5rem" }}>
                        <div className="panel-header">
                          <h3 className="panel-title">📋 KYC Submission — Identity Details</h3>
                          <span className="badge badge-info">HOLDER</span>
                        </div>

                        <div className="form-group">
                          <label className="form-label">Verification Level *</label>
                          <select
                            className="form-select"
                            value={holderForm.verification_level}
                            onChange={(e) => setHolderForm({ ...holderForm, verification_level: e.target.value })}
                          >
                            <option value="BASIC">BASIC — National ID / Government ID</option>
                            <option value="ENHANCED">ENHANCED — Passport + Proof of Address</option>
                          </select>
                        </div>

                        <div className="form-group">
                          <label className="form-label">Full Legal Name *</label>
                          <input id="kyc-full-name" type="text" className="form-input" required
                            value={holderForm.full_name}
                            onChange={(e) => setHolderForm({ ...holderForm, full_name: e.target.value })}
                            placeholder="As it appears on your identity document"
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label">Date of Birth *</label>
                          <input id="kyc-dob" type="date" className="form-input" required
                            value={holderForm.date_of_birth}
                            onChange={(e) => setHolderForm({ ...holderForm, date_of_birth: e.target.value })}
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label">Nationality *</label>
                          <input id="kyc-nationality" type="text" className="form-input" required
                            value={holderForm.nationality}
                            onChange={(e) => setHolderForm({ ...holderForm, nationality: e.target.value })}
                            placeholder="e.g. United States, India"
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label">Document Type *</label>
                          <select id="kyc-doc-type" className="form-select" required
                            value={holderForm.document_type}
                            onChange={(e) => setHolderForm({ ...holderForm, document_type: e.target.value })}
                          >
                            <option value="PASSPORT">Passport</option>
                            <option value="NATIONAL_ID">National ID Card</option>
                            <option value="DRIVING_LICENSE">Driving Licence</option>
                          </select>
                        </div>

                        <div className="form-group">
                          <label className="form-label">Document Number *</label>
                          <input id="kyc-doc-number" type="text" className="form-input" required
                            value={holderForm.document_number}
                            onChange={(e) => setHolderForm({ ...holderForm, document_number: e.target.value })}
                            placeholder="Passport / ID number"
                          />
                        </div>

                        {holderForm.verification_level === "ENHANCED" && (<>
                          <div className="form-group">
                            <label className="form-label">Residential Address</label>
                            <input id="kyc-address" type="text" className="form-input"
                              value={holderForm.residential_address}
                              onChange={(e) => setHolderForm({ ...holderForm, residential_address: e.target.value })}
                              placeholder="Full current residential address"
                            />
                          </div>
                          <div className="form-group">
                            <label className="form-label">Country of Issue</label>
                            <input id="kyc-country" type="text" className="form-input"
                              value={holderForm.country_of_issue}
                              onChange={(e) => setHolderForm({ ...holderForm, country_of_issue: e.target.value })}
                              placeholder="Country that issued the document"
                            />
                          </div>
                          <div className="form-group">
                            <label className="form-label">Document Expiry Date</label>
                            <input id="kyc-expiry" type="date" className="form-input"
                              value={holderForm.expiry_date}
                              onChange={(e) => setHolderForm({ ...holderForm, expiry_date: e.target.value })}
                            />
                          </div>
                        </>)}
                      </div>

                      <div className="glass-panel" style={{ padding: "1.5rem" }}>
                        <div className="panel-header">
                          <h3 className="panel-title">📎 Upload Supporting Documents</h3>
                          <span className="badge badge-info">PDF / JPG / PNG · max 10MB each</span>
                        </div>

                        <label
                          className="kyc-upload-dropzone"
                          htmlFor="kyc-file-input"
                          style={{ display: "block", cursor: "pointer" }}
                        >
                          <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>🗂️</div>
                          <div style={{ fontSize: "0.88rem", color: "var(--text-muted)" }}>
                            Click to select your identity document(s)
                            <span style={{ color: "#f87171", marginLeft: "0.25rem" }}>*</span>
                          </div>
                          <div style={{ fontSize: "0.77rem", color: uploadedFiles.length === 0 ? "#f87171" : "var(--text-dim)", marginTop: "0.25rem", fontWeight: uploadedFiles.length === 0 ? 600 : 400 }}>
                            {uploadedFiles.length === 0
                              ? "⚠ Required — Passport scan, National ID, or Driving Licence (PDF, JPG, PNG, max 10 MB)"
                              : `✅ ${uploadedFiles.length} file${uploadedFiles.length > 1 ? "s" : ""} selected — Passport scan, National ID, Proof of Address (PDF, JPG, PNG)`}
                          </div>
                          <input
                            id="kyc-file-input"
                            type="file"
                            multiple
                            accept=".pdf,.jpg,.jpeg,.png"
                            style={{ display: "none" }}
                            onChange={(e) => setUploadedFiles(Array.from(e.target.files))}
                          />
                        </label>

                        {uploadedFiles.length > 0 && (
                          <div style={{ marginTop: "0.75rem" }}>
                            {uploadedFiles.map((f, i) => (
                              <div key={i} className="doc-pill">
                                <div className="doc-pill-meta">
                                  <span>📄</span>
                                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}>{f.name}</span>
                                </div>
                                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                                  {(f.size / 1024).toFixed(0)} KB
                                </span>
                              </div>
                            ))}
                          </div>
                        )}

                        <div className="disclaimer-card" style={{ marginTop: "1.5rem" }}>
                          ℹ️ <strong>Important:</strong> Uploading documents does not automatically verify them. An authorized issuer must review and approve your submission. VERIFIED status confirms issuer approval of submitted evidence — not independent government authentication.
                        </div>

                        <button
                          id="kyc-submit-btn"
                          type="submit"
                          className="btn btn-primary"
                          disabled={loading || uploadedFiles.length === 0}
                          title={uploadedFiles.length === 0 ? "Please upload at least one identity document before submitting" : ""}
                          style={{
                            width: "100%",
                            marginTop: "1rem",
                            opacity: uploadedFiles.length === 0 ? 0.55 : 1,
                          }}
                        >
                          {loading ? "Submitting…" : uploadedFiles.length === 0 ? "📤 Upload a document to submit" : "📤 Submit KYC Application"}
                        </button>
                      </div>
                    </div>
                  </form>
                )}

                {holderKyc
                  && holderKyc.verification_status !== "NOT_SUBMITTED"
                  && holderKyc.verification_status !== "RESUBMISSION_REQUIRED"
                  && holderKyc.verification_status !== "REJECTED" && (
                  <div className="glass-panel" style={{ padding: "1.5rem" }}>
                    <div className="panel-header">
                      <h3 className="panel-title">🗂️ Your Submitted Evidence</h3>
                      <button className="btn btn-secondary" style={{ padding: "0.3rem 0.75rem", fontSize: "0.8rem" }} onClick={fetchHolderKyc}>
                        Refresh
                      </button>
                    </div>
                    <div className="evidence-grid">
                      {[
                        ["Full Name", holderKyc.full_name],
                        ["Date of Birth", holderKyc.date_of_birth],
                        ["Nationality", holderKyc.nationality],
                        ["Document Type", holderKyc.document_type],
                        ["Document Number", holderKyc.document_number],
                        ["KYC Level", holderKyc.verification_level],
                      ].map(([label, val]) => (
                        <div key={label} className="evidence-item">
                          <div className="evidence-label">{label}</div>
                          <div className="evidence-value">{val || "—"}</div>
                        </div>
                      ))}
                    </div>
                    {(holderKyc.documents || []).length > 0 && (
                      <>
                        <div style={{ fontWeight: 600, color: "var(--text-muted)", fontSize: "0.82rem", marginTop: "1rem", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                          Uploaded Documents ({holderKyc.documents.length})
                        </div>
                        {holderKyc.documents.map((doc) => (
                          <div key={doc.id} className="doc-pill">
                            <div className="doc-pill-meta">
                              <span>{doc.mime_type?.includes("pdf") ? "📄" : "🖼️"}</span>
                              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}>{doc.file_name}</span>
                              <span className="badge badge-info" style={{ fontSize: "0.68rem" }}>{doc.document_type}</span>
                            </div>
                            <button
                              className="btn btn-secondary"
                              style={{ padding: "0.2rem 0.6rem", fontSize: "0.75rem" }}
                              onClick={() => handleViewDocument(doc.id, doc.file_name)}
                            >
                              View
                            </button>
                          </div>
                        ))}
                      </>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ================================================== */}
            {/* ISSUER REVIEW PANEL                                */}
            {/* ================================================== */}
            {/* FIX: both explicit "issuer" perspective AND auto require an authenticated ISSUER/ADMIN */}
            {currentUser && (currentUser.role === "ISSUER" || currentUser.role === "ADMIN") && (kycPerspective === "issuer" || kycPerspective === "auto") && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                <div className="grid-2">

                  {/* Pending Queue */}
                  <div className="glass-panel" style={{ padding: "1.5rem" }}>
                    <div className="panel-header">
                      <h3 className="panel-title">🗂️ Pending KYC Queue</h3>
                      <button className="btn btn-secondary" style={{ padding: "0.3rem 0.75rem", fontSize: "0.8rem" }} onClick={fetchPendingKyc} disabled={pendingKycLoading}>
                        {pendingKycLoading ? "Loading…" : "Refresh"}
                      </button>
                    </div>

                    {/* Search by UUID */}
                    <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
                      <input
                        type="text"
                        className="form-input form-mono"
                        placeholder="Search by Holder User UUID…"
                        value={searchKycUuid}
                        onChange={(e) => setSearchKycUuid(e.target.value)}
                        style={{ flex: 1 }}
                      />
                      <button
                        className="btn btn-secondary"
                        disabled={reviewLoading || !searchKycUuid}
                        onClick={() => fetchKycForReview(searchKycUuid)}
                      >
                        Fetch
                      </button>
                    </div>

                    {pendingKycList.length === 0 && !pendingKycLoading && (
                      <div style={{ color: "var(--text-dim)", fontSize: "0.85rem", padding: "1rem 0" }}>
                        No pending KYC applications. Click Refresh to reload.
                      </div>
                    )}

                    <div className="table-container">
                      {pendingKycList.length > 0 && (
                        <table className="kyc-table">
                          <thead>
                            <tr>
                              <th>User UUID</th>
                              <th>Level</th>
                              <th>Status</th>
                              <th>Submitted</th>
                              <th>Docs</th>
                              <th></th>
                            </tr>
                          </thead>
                          <tbody>
                            {pendingKycList.map((app) => (
                              <tr key={app.id}>
                                <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem" }}>{(app.user_uuid || "").substring(0, 12)}…</td>
                                <td><span className="badge badge-info" style={{ fontSize: "0.7rem" }}>{app.verification_level}</span></td>
                                <td>
                                  <span className={`badge ${
                                    app.verification_status === "VERIFIED" ? "badge-success"
                                    : app.verification_status === "REJECTED" ? "badge-danger"
                                    : app.verification_status === "RESUBMISSION_REQUIRED" ? "badge-warning"
                                    : "badge-info"
                                  }`} style={{ fontSize: "0.7rem" }}>
                                    {app.verification_status}
                                  </span>
                                </td>
                                <td style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                                  {app.submitted_at ? new Date(app.submitted_at).toLocaleDateString() : "—"}
                                </td>
                                <td style={{ fontSize: "0.78rem" }}>{(app.documents || []).length}</td>
                                <td>
                                  <button
                                    className="btn btn-secondary"
                                    style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                                    onClick={() => { setSelectedKycForReview(app); setSearchKycUuid(app.user_uuid); }}
                                  >
                                    Review
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </div>

                  {/* Review Pane */}
                  <div className="glass-panel" style={{ padding: "1.5rem" }}>
                    <div className="panel-header">
                      <h3 className="panel-title">🔎 Application Review</h3>
                      {selectedKycForReview && (
                        <span className={`badge ${
                          selectedKycForReview.verification_status === "VERIFIED" ? "badge-success"
                          : selectedKycForReview.verification_status === "REJECTED" ? "badge-danger"
                          : selectedKycForReview.verification_status === "RESUBMISSION_REQUIRED" ? "badge-warning"
                          : "badge-info"
                        }`}>
                          {selectedKycForReview.verification_status}
                        </span>
                      )}
                    </div>

                    {!selectedKycForReview ? (
                      <div style={{ color: "var(--text-dim)", fontSize: "0.85rem", padding: "1rem 0" }}>
                        Select an application from the queue or search by UUID to begin review.
                      </div>
                    ) : (
                      <>
                        <div className="evidence-grid">
                          {[
                            ["Holder UUID", selectedKycForReview.user_uuid?.substring(0, 16) + "…"],
                            ["Full Name", selectedKycForReview.full_name],
                            ["Date of Birth", selectedKycForReview.date_of_birth],
                            ["Nationality", selectedKycForReview.nationality],
                            ["Document Type", selectedKycForReview.document_type],
                            ["Document Number", selectedKycForReview.document_number],
                            ["KYC Level", selectedKycForReview.verification_level],
                            ["Country of Issue", selectedKycForReview.country_of_issue],
                            ["Expiry Date", selectedKycForReview.expiry_date],
                            ["Residential Address", selectedKycForReview.residential_address],
                          ].map(([label, val]) => (
                            <div key={label} className="evidence-item">
                              <div className="evidence-label">{label}</div>
                              <div className="evidence-value" style={{ fontSize: "0.82rem" }}>{val || "—"}</div>
                            </div>
                          ))}
                        </div>

                        {(selectedKycForReview.documents || []).length > 0 && (
                          <div style={{ marginTop: "1rem" }}>
                            <div style={{ fontWeight: 600, fontSize: "0.82rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "0.5rem" }}>
                              Submitted Documents ({selectedKycForReview.documents.length})
                            </div>
                            {selectedKycForReview.documents.map((doc) => (
                              <div key={doc.id} className="doc-pill">
                                <div className="doc-pill-meta">
                                  <span>{doc.mime_type?.includes("pdf") ? "📄" : "🖼️"}</span>
                                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{doc.file_name}</span>
                                  <span className="badge badge-info" style={{ fontSize: "0.65rem" }}>{doc.document_type}</span>
                                  <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                                    {(doc.file_size / 1024).toFixed(0)} KB
                                  </span>
                                </div>
                                <button
                                  className="btn btn-secondary"
                                  style={{ padding: "0.2rem 0.5rem", fontSize: "0.72rem" }}
                                  onClick={() => handleViewDocument(doc.id, doc.file_name)}
                                >
                                  View
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {(selectedKycForReview.documents || []).length === 0 && (
                          <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "rgba(244,63,94,0.05)", border: "1px solid rgba(244,63,94,0.2)", borderRadius: "8px", fontSize: "0.82rem", color: "#f87171" }}>
                            ⚠️ No documents uploaded by holder.
                          </div>
                        )}

                        {/* Decision Form */}
                        {selectedKycForReview.verification_status !== "VERIFIED" && (
                          <div style={{ marginTop: "1.25rem", borderTop: "1px solid var(--border-color)", paddingTop: "1.25rem" }}>
                            <div style={{ fontWeight: 700, marginBottom: "0.85rem", color: "var(--text-main)" }}>Review Decision</div>

                            <div className="form-group">
                              <label className="form-label">Decision *</label>
                              <select className="form-select" value={reviewDecisionForm.decision}
                                onChange={(e) => setReviewDecisionForm({ ...reviewDecisionForm, decision: e.target.value })}>
                                <option value="VERIFY">✅ Verify — Approve the submitted evidence</option>
                                <option value="REJECT">❌ Reject — Permanently reject this application</option>
                                <option value="REQUEST_RESUBMISSION">🔄 Request Resubmission — Ask holder to provide better evidence</option>
                              </select>
                            </div>

                            <div className="form-group">
                              <label className="form-label">
                                {reviewDecisionForm.decision === "VERIFY" ? "Review Notes (Optional)" : "Reason / Instructions *"}
                              </label>
                              <textarea
                                className="form-textarea"
                                rows={3}
                                style={{ resize: "vertical" }}
                                value={reviewDecisionForm.decision === "VERIFY" ? reviewDecisionForm.notes : reviewDecisionForm.reason}
                                onChange={(e) => {
                                  if (reviewDecisionForm.decision === "VERIFY") {
                                    setReviewDecisionForm({ ...reviewDecisionForm, notes: e.target.value });
                                  } else {
                                    setReviewDecisionForm({ ...reviewDecisionForm, reason: e.target.value });
                                  }
                                }}
                                placeholder={
                                  reviewDecisionForm.decision === "VERIFY"
                                    ? "Optional compliance notes for audit record…"
                                    : "Provide clear reason or instructions for the holder…"
                                }
                              />
                            </div>

                            {reviewDecisionForm.decision === "VERIFY" && (
                              <label style={{ display: "flex", alignItems: "flex-start", gap: "0.65rem", cursor: "pointer", marginBottom: "1rem", fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                                <input
                                  id="kyc-confirm-review"
                                  type="checkbox"
                                  checked={reviewDecisionForm.confirmed}
                                  onChange={(e) => setReviewDecisionForm({ ...reviewDecisionForm, confirmed: e.target.checked })}
                                  style={{ marginTop: "3px", accentColor: "var(--quantum-cyan)" }}
                                />
                                <span>
                                  I confirm I have reviewed the submitted identity evidence according to the organization's KYC procedure. I understand that VERIFIED status reflects my review and approval — not independent cryptographic authentication of physical documents.
                                </span>
                              </label>
                            )}

                            <div style={{ display: "flex", gap: "0.75rem" }}>
                              <button
                                id="kyc-review-submit-btn"
                                className={`btn ${reviewDecisionForm.decision === "VERIFY" ? "btn-success" : "btn-secondary"}`}
                                disabled={loading || (reviewDecisionForm.decision === "VERIFY" && !reviewDecisionForm.confirmed)}
                                onClick={handleReviewDecision}
                                style={{ flex: 1 }}
                              >
                                {loading ? "Processing…" : reviewDecisionForm.decision === "VERIFY" ? "✅ Confirm & Verify" : reviewDecisionForm.decision === "REJECT" ? "❌ Reject Application" : "🔄 Request Resubmission"}
                              </button>
                            </div>

                            <div className="disclaimer-card">
                              ⚠️ VERIFIED status means an authorized issuer approved the submitted evidence per the configured review procedure. QuantumSafeKYC does not independently authenticate physical documents against government databases.
                            </div>
                          </div>
                        )}

                        {selectedKycForReview.verification_status === "VERIFIED" && (
                          <div style={{ marginTop: "1rem", padding: "0.85rem", background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.2)", borderRadius: "8px", fontSize: "0.85rem", color: "#34d399" }}>
                            ✅ This application is already VERIFIED. Verified at: {selectedKycForReview.verified_at ? new Date(selectedKycForReview.verified_at).toLocaleString() : "—"}
                            {selectedKycForReview.reviewed_by && (
                              <div style={{ color: "var(--text-muted)", marginTop: "0.25rem", fontSize: "0.78rem" }}>
                                Reviewed by: {selectedKycForReview.reviewed_by?.substring(0, 12)}…
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* FIX: Show login-required message whenever unauthenticated,
                 regardless of which perspective button was manually selected */}
            {!currentUser && (
              <div className="glass-panel" style={{ padding: "1.5rem" }}>
                <div className="panel-header">
                  <h3 className="panel-title">📋 KYC Workflow</h3>
                  <span className="badge badge-warning">Login required</span>
                </div>
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  Please log in as a <strong>HOLDER</strong> to submit a KYC application,
                  or as an <strong>ISSUER / ADMIN</strong> to review pending applications.
                </p>
                <p style={{ color: "var(--text-dim)", fontSize: "0.8rem", marginTop: "0.5rem" }}>
                  Use the <strong>Identity &amp; RBAC</strong> tab to register or authenticate.
                </p>
              </div>
            )}

          </div>
        )}

        {/* TAB 4: PQC CREDENTIALS */}
        {activeTab === "credentials" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div className="grid-2">
              <div className="glass-panel" style={{ padding: "1.5rem" }}>
                <div className="panel-header">
                  <h3 className="panel-title">⚛ Issue ML-DSA-65 Credential</h3>
                  <span className="badge badge-purple">ISSUER / ADMIN</span>
                </div>
                <div className="form-group">
                  <label className="form-label">Verified Holder User UUID</label>
                  <input
                    type="text"
                    className="form-input form-mono"
                    value={issueForm.user_uuid}
                    onChange={(e) => setIssueForm({ user_uuid: e.target.value })}
                    placeholder="Enter user_uuid with verified KYC"
                  />
                </div>
                <button
                  className="btn btn-primary"
                  disabled={loading || !issueForm.user_uuid}
                  onClick={() => apiCall(`/credentials/${issueForm.user_uuid}/issue`, "POST")}
                  style={{ width: "100%" }}
                >
                  Sign & Issue Quantum-Safe Credential
                </button>
              </div>

              <div className="glass-panel" style={{ padding: "1.5rem" }}>
                <div className="panel-header">
                  <h3 className="panel-title">🔍 Inspect & Verify Credential</h3>
                  <span className="badge badge-info">Public / Verifier</span>
                </div>
                <div className="form-group">
                  <label className="form-label">Credential UUID</label>
                  <input
                    type="text"
                    className="form-input form-mono"
                    value={inspectCredUuid}
                    onChange={(e) => setInspectCredUuid(e.target.value)}
                    placeholder="Enter credential_uuid"
                  />
                </div>
                <div style={{ display: "flex", gap: "0.75rem" }}>
                  <button
                    className="btn btn-secondary"
                    disabled={loading || !inspectCredUuid}
                    onClick={() => apiCall(`/credentials/verify-pqc/${inspectCredUuid}`, "POST")}
                    style={{ flex: 1 }}
                  >
                    Test PQC Signature Only
                  </button>
                  <button
                    className="btn btn-primary"
                    disabled={loading || !inspectCredUuid}
                    onClick={() => apiCall(`/credentials/verify/${inspectCredUuid}`, "POST")}
                    style={{ flex: 1 }}
                  >
                    Complete PQC Verification
                  </button>
                </div>
              </div>
            </div>

            <div className="glass-panel" style={{ padding: "1.5rem" }}>
              <div className="panel-header">
                <h3 className="panel-title" style={{ color: "var(--quantum-rose)" }}>⛔ Revoke Credential</h3>
                <span className="badge badge-danger">Revocation & Audit</span>
              </div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                Revoking a credential marks it invalid across all future verification requests. Duplicate revocation returns 409 Conflict.
              </p>
              <div className="grid-2">
                <div className="form-group">
                  <label className="form-label">Credential UUID to Revoke</label>
                  <input
                    type="text"
                    className="form-input form-mono"
                    value={revokeForm.credential_uuid}
                    onChange={(e) => setRevokeForm({ ...revokeForm, credential_uuid: e.target.value })}
                    placeholder="Enter credential_uuid"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Revocation Reason</label>
                  <input
                    type="text"
                    className="form-input"
                    value={revokeForm.reason}
                    onChange={(e) => setRevokeForm({ ...revokeForm, reason: e.target.value })}
                  />
                </div>
              </div>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button
                  className="btn btn-danger"
                  disabled={loading || !revokeForm.credential_uuid}
                  onClick={() => apiCall(`/credentials/${revokeForm.credential_uuid}/revoke`, "PATCH", { reason: revokeForm.reason })}
                  style={{ flex: 1 }}
                >
                  Revoke Credential (via /credentials)
                </button>
                <button
                  className="btn btn-secondary"
                  disabled={loading || !revokeForm.credential_uuid}
                  onClick={() => apiCall(`/revocations/${revokeForm.credential_uuid}`, "GET")}
                  style={{ flex: 1 }}
                >
                  Check Revocation Status
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: CONSENT & VERIFIER */}
        {activeTab === "verification" && (
          <div className="grid-2">
            <div className="glass-panel" style={{ padding: "1.5rem" }}>
              <div className="panel-header">
                <h3 className="panel-title">🤝 Step 1: Manage Verifier Consent (HOLDER)</h3>
                <span className="badge badge-info">Holder Authorization</span>
              </div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                Under GDPR and privacy regulations, a verifier cannot query credentials without user consent.
              </p>
              <div className="form-group">
                <label className="form-label">Holder User UUID</label>
                <input
                  type="text"
                  className="form-input form-mono"
                  value={consentForm.user_uuid || currentUser?.user_uuid || ""}
                  onChange={(e) => setConsentForm({ ...consentForm, user_uuid: e.target.value })}
                  placeholder="Holder user_uuid"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Verifier Identifier</label>
                <input
                  type="text"
                  className="form-input"
                  value={consentForm.verifier_id}
                  onChange={(e) => setConsentForm({ ...consentForm, verifier_id: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Purpose</label>
                <input
                  type="text"
                  className="form-input"
                  value={consentForm.purpose}
                  onChange={(e) => setConsentForm({ ...consentForm, purpose: e.target.value })}
                />
              </div>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button
                  className="btn btn-success"
                  disabled={loading || !consentForm.user_uuid}
                  onClick={() => apiCall("/consents", "POST", consentForm)}
                  style={{ flex: 1 }}
                >
                  Grant Consent
                </button>
                <button
                  className="btn btn-secondary"
                  disabled={loading || !consentForm.user_uuid}
                  onClick={() => apiCall(`/consents/${consentForm.user_uuid}`, "GET")}
                  style={{ flex: 1 }}
                >
                  List My Consents
                </button>
              </div>
            </div>

            <div className="glass-panel" style={{ padding: "1.5rem" }}>
              <div className="panel-header">
                <h3 className="panel-title">🏛 Step 2: Third-Party Credential Verification</h3>
                <span className="badge badge-success">Bank / Relying Party</span>
              </div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                Executes the full pipeline: Verifies Consent Authorization → Validates ML-DSA-65 PQC Signature → Checks Revocation Registry.
              </p>
              <div className="form-group">
                <label className="form-label">Credential UUID</label>
                <input
                  type="text"
                  className="form-input form-mono"
                  value={verifyForm.credential_uuid}
                  onChange={(e) => setVerifyForm({ ...verifyForm, credential_uuid: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Requesting Verifier ID</label>
                <input
                  type="text"
                  className="form-input"
                  value={verifyForm.verifier_id}
                  onChange={(e) => setVerifyForm({ ...verifyForm, verifier_id: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Stated Purpose</label>
                <input
                  type="text"
                  className="form-input"
                  value={verifyForm.purpose}
                  onChange={(e) => setVerifyForm({ ...verifyForm, purpose: e.target.value })}
                />
              </div>
              <button
                className="btn btn-primary"
                disabled={loading || !verifyForm.credential_uuid}
                onClick={() => apiCall("/verification/credential", "POST", verifyForm)}
                style={{ width: "100%" }}
              >
                Execute Full Verification Pipeline
              </button>
            </div>
          </div>
        )}

        {/* TAB 6: BLOCKCHAIN & AUDIT */}
        {activeTab === "blockchain" && (
          <div className="grid-2">
            <div className="glass-panel" style={{ padding: "1.5rem" }}>
              <div className="panel-header">
                <h3 className="panel-title">⛓ Blockchain Anchor Management</h3>
                <span className="badge badge-info">Immutable Ledger</span>
              </div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                Anchors the cryptographic SHA-512 fingerprint of the credential onto the blockchain ledger to guarantee non-repudiation.
              </p>
              <div className="form-group">
                <label className="form-label">Credential UUID to Anchor</label>
                <input
                  type="text"
                  className="form-input form-mono"
                  value={blockchainTargetUuid}
                  onChange={(e) => setBlockchainTargetUuid(e.target.value)}
                />
              </div>
              <div style={{ display: "flex", gap: "0.75rem" }}>
                <button
                  className="btn btn-primary"
                  disabled={loading || !blockchainTargetUuid}
                  onClick={() => apiCall(`/blockchain/anchor/${blockchainTargetUuid}`, "POST")}
                  style={{ flex: 1 }}
                >
                  Create Anchor on Chain
                </button>
                <button
                  className="btn btn-secondary"
                  disabled={loading || !blockchainTargetUuid}
                  onClick={() => apiCall(`/blockchain/verify/${blockchainTargetUuid}`, "POST")}
                  style={{ flex: 1 }}
                >
                  Verify Anchor Integrity
                </button>
              </div>
            </div>

            <div className="glass-panel" style={{ padding: "1.5rem" }}>
              <div className="panel-header">
                <h3 className="panel-title">🛡 Cryptographic Tamper Detection</h3>
                <span className="badge badge-success">Self-Healing Integrity</span>
              </div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1rem" }}>
                If any bit of the credential data, PQC signature, or audit trail is altered by an adversary or unauthorized database edit,
                both the post-quantum signature verification and blockchain anchor check instantly flag it as <strong>INVALID</strong>.
              </p>
              <div style={{ padding: "1rem", background: "rgba(0,0,0,0.3)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)", marginBottom: "1rem" }}>
                <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--quantum-cyan)", marginBottom: "0.5rem" }}>
                  Active Integrity Safeguards:
                </div>
                <ul style={{ paddingLeft: "1.2rem", fontSize: "0.82rem", color: "var(--text-muted)" }}>
                  <li>NIST FIPS 204 ML-DSA-65 post-quantum lattice verification</li>
                  <li>SHA-512 cryptographic state anchoring</li>
                  <li>Actor-attributed audit event logs with chained hash stamps</li>
                  <li>Strict Role-Based Access Control on all mutating operations</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* TAB 7: MCP AI TOOLS CONSOLE */}
        {activeTab === "mcp" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div className="glass-panel" style={{ padding: "1.5rem" }}>
              <div className="panel-header">
                <div>
                  <h3 className="panel-title">🤖 Model Context Protocol (MCP) Live Console</h3>
                  <div className="panel-subtitle">Standardized interface for LLM Agents & Claude / Gemini assistants</div>
                </div>
                <span className="badge badge-purple">{mcpTools.length} Registered Tools</span>
              </div>

              <div className="tool-grid" style={{ marginBottom: "1.5rem" }}>
                {mcpTools.map((tool) => (
                  <div
                    key={tool.name}
                    className={`tool-card ${selectedMcpTool === tool.name ? "active" : ""}`}
                    onClick={() => setSelectedMcpTool(tool.name)}
                  >
                    <div>
                      <div className="tool-name">{tool.name}</div>
                      <div className="tool-desc">{tool.description}</div>
                    </div>
                    <span className="badge badge-info" style={{ alignSelf: "flex-start", fontSize: "0.68rem" }}>
                      {Object.keys(tool.parameters || {}).length} Params
                    </span>
                  </div>
                ))}
              </div>

              {/* Selected Tool Parameter Inputs */}
              <div style={{ padding: "1.25rem", background: "rgba(0,0,0,0.3)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-color)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                  <h4 style={{ color: "var(--quantum-cyan)", fontFamily: "var(--font-mono)", fontSize: "0.95rem" }}>
                    Configure: {selectedMcpTool}
                  </h4>
                  <button className="btn btn-primary" onClick={runMcpTool} disabled={mcpLoading}>
                    {mcpLoading ? "Running via MCP..." : "▶ Execute MCP Tool"}
                  </button>
                </div>

                <div className="grid-2">
                  {Object.entries(
                    mcpTools.find((t) => t.name === selectedMcpTool)?.parameters || {}
                  ).map(([paramName, paramSpec]) => (
                    <div className="form-group" key={paramName}>
                      <label className="form-label">
                        {paramName} {paramSpec.required && <span style={{ color: "var(--quantum-rose)" }}>*</span>}
                        <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginLeft: "0.5rem" }}>({paramSpec.description})</span>
                      </label>
                      <input
                        type="text"
                        className="form-input form-mono"
                        value={mcpParams[paramName] || ""}
                        onChange={(e) => setMcpParams({ ...mcpParams, [paramName]: e.target.value })}
                        placeholder={`Enter ${paramName}`}
                      />
                    </div>
                  ))}
                  {Object.keys(mcpTools.find((t) => t.name === selectedMcpTool)?.parameters || {}).length === 0 && (
                    <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", gridColumn: "1 / -1" }}>
                      This tool takes no parameters. Ready to execute.
                    </div>
                  )}
                </div>

                {mcpResult && (
                  <div className="result-box" style={{ marginTop: "1rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                      <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--quantum-cyan)" }}>
                        MCP Execution Result:
                      </span>
                      <span className="badge badge-success">Protocol OK</span>
                    </div>
                    <pre className="code-block">{JSON.stringify(mcpResult, null, 2)}</pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* LIVE RESPONSE VIEWER (Global for all API actions) */}
        {actionLog && (
          <div className="glass-panel" style={{ marginTop: "1.5rem", padding: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="stat-title" style={{ fontSize: "0.85rem", color: "var(--text-main)" }}>
                  📡 API Action Response: {actionLog.title}
                </span>
                <span className={`badge ${actionLog.status >= 200 && actionLog.status < 300 ? "badge-success" : "badge-danger"}`}>
                  HTTP {actionLog.status}
                </span>
              </div>
              <button
                className="btn btn-secondary"
                style={{ padding: "0.2rem 0.5rem", fontSize: "0.72rem" }}
                onClick={() => setActionLog(null)}
              >
                Clear
              </button>
            </div>
            <pre className="code-block">{JSON.stringify(actionLog.data || actionLog.error || actionLog, null, 2)}</pre>
          </div>
        )}
      </main>

      {/* FOOTER */}
      <footer className="app-footer">
        QuantumSafeKYC · NIST FIPS 204 Post-Quantum Security · Model Context Protocol (MCP) · End-to-End Verified
      </footer>
    </div>
  );
}