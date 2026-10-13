# QuantumSafeKYC

AI-Powered Quantum-Safe Privacy-Preserving Reusable KYC Framework for FinTech.

## Project Status

Phase 0 — Environment setup

## Architecture

The planned system combines:

- AI-based KYC verification
- Verifiable Credentials
- Post-quantum cryptography
- AES-256-GCM encryption
- SHA3-256 hashing
- Hyperledger Fabric
- MPC
- zk-STARK
- MCP
- User consent
- FinTech verification
- Audit and monitoring

## Current Implementation

### Backend

- Python 3.11
- Flask
- Flask-CORS

### Frontend

- React
- Vite
- Node.js

## Current Test

The Phase 0 health-check API is working.

Backend:

`http://127.0.0.1:5000/api/health`

Frontend:

`http://localhost:5173`

## Development Principle

The project is developed incrementally.

No production financial, government, Aadhaar, PAN, banking, or institutional integration is assumed unless an actual authorised API is available.

Sensitive KYC information must not be stored directly on the blockchain.

## Project Structure

```text
QuantumSafeKYC/
├── backend/
├── frontend/
├── blockchain/
├── crypto/
├── database/
├── zkproof/
├── ai/
├── scripts/
├── tests/
├── docs/
├── datasets/
└── logs/