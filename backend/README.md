# Project ASTRAEA — Backend 1: API & Data Flow System

## Overview
**Backend 1** is the core API, Data Flow, and Integration Engine for **Project ASTRAEA**. It seamlessly orchestrates data flow across all system subsystems:

`Frontend` ↔ `API & Data Flow` ↔ `Cryptography` ↔ `DLT Ledger (Backend 2)` ↔ `Watermarking` ↔ `Forensic Audit`

---

## 🏗️ Architecture & Pipeline Sequence

Backend 1 strictly preserves the ASTRAEA 10-phase operational chain:

1. **Broadcast (`POST /broadcast`)**:
   - Plaintext document encrypted via **AES-256-GCM**.
   - Content key $K_{doc}$ encapsulated into per-recipient **ML-KEM-768** lockboxes ($c_u, W_u$).
2. **Decryption Request (`POST /request_decryption`)**:
   - Recipient submits signed receipt $m_{receipt} = \text{UID} \parallel \text{DocID} \parallel \text{Timestamp}$ with **ML-DSA-65** signature ($\sigma_u$).
3. **Ledger-Gated Key Release**:
   - Receipt $\sigma_u$ and $m_{receipt}$ submitted to DLT 3-Node Consensus Cluster.
   - Key release is **STRICTLY BLOCKED** until DLT consensus & block committal succeeds.
4. **In-Memory Decryption**:
   - $K_{doc}$ recovered via ML-KEM decapsulation.
   - Document decrypted in-memory using `io.BytesIO` (no unencrypted disk writes).
5. **2D Haar DWT Watermarking**:
   - Deterministic 256-bit Watermark ID $W_{ID} = \text{BLAKE3}(\sigma_u \parallel y_i)$ generated.
   - Protected via Reed-Solomon Forward Error Correction (FEC) and embedded into document canvas via 2D Haar DWT.
6. **Forensic Audit (`POST /audit`)**:
   - Accepts $W_{ID}^*$ or uploaded leaked photo (processed via OpenCV deskew/perspective correction).
   - Queries DLT ledger and verifies ML-DSA signature for cryptographically validated attribution (`FOUND`, `FOUND_BUT_INVALID`, `NOT_FOUND`).

---

## 📂 Backend 1 Directory Structure

```
backend/
├── main.py                     # FastAPI server entrypoint
├── config.py                   # Configuration & settings
├── API.md                      # Complete API Specification
├── README.md                   # System Architecture & Documentation
├── models/                     # Request, Response & State models
│   ├── state.py                # PipelineStage & AuditStatus enums
│   ├── requests.py             # Pydantic request models
│   └── responses.py            # Pydantic response models
├── crypto_interface/           # Unified wrapper for QuantumCrypto (AES-GCM, ML-KEM, ML-DSA)
│   └── wrapper.py
├── ledger_interface/           # Interface connecting to DLT Backend 2 (ledger & 3-node consensus)
│   └── service.py
├── watermark_interface/        # W_ID derivation & 2D Haar DWT steganography
│   ├── wid.py
│   └── dwt.py
├── services/                   # Business logic & Pipeline Orchestrator
│   ├── state_machine.py        # Dynamic state transition guards
│   └── pipeline.py             # End-to-end Master Pipeline orchestrator
├── api/                        # FastAPI endpoint routes
│   ├── broadcast.py            # POST /broadcast
│   ├── decryption.py           # POST /request_decryption
│   ├── audit.py                # POST /audit & POST /audit/upload
│   ├── document.py             # GET /documents & GET /document/{id}
│   └── status.py               # GET /status & GET /ledger/status
└── tests/                      # Automated test suite
    └── test_backend1.py
```

---

## 🚀 Running the Server

### Prerequisites
Ensure Python 3.10+ is installed along with dependencies:
```bash
python -m pip install fastapi uvicorn pydantic pycryptodome reedsolo opencv-python pytest
```

### Start Backend 1 API Server
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI Swagger Documentation will be accessible at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🧪 Running Tests

To run the full unit and integration test suite:
```bash
python -m pytest backend/tests/test_backend1.py -v
```
