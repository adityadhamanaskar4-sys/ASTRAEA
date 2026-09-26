# Project ASTRAEA — Backend 1 API Specification

## Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/broadcast` | Encrypt document & encapsulate ML-KEM recipient lockboxes |
| `POST` | `/request_decryption` | Process decryption request, run DLT consensus, release key & embed DWT watermark |
| `POST` | `/audit` | Perform forensic leak audit by $W_{ID}^*$ or base64 image |
| `POST` | `/audit/upload` | Form-data file upload for leaked screen photo attribution |
| `GET` | `/documents` | List all distributed documents and recipient lockbox statuses |
| `GET` | `/document/{id}` | Fetch single document metadata and lockbox status |
| `GET` | `/status` | Overall system status, connected modules & crypto engine health |
| `GET` | `/ledger/status` | DLT 3-Node consensus height, head hashes & integrity report |

---

## 1. POST /broadcast

### Request Body (`application/json`)
```json
{
  "title": "OP ORDER — ALPHA",
  "classification": "RESTRICTED",
  "body": "Section 4.2 — Movement Schedule\nSector clearance pending final authorization from command.",
  "recipient_uids": ["OFC-2291", "OFC-1187"]
}
```

### Response (`200 OK`)
```json
{
  "doc_id": "DOC-8F32A1B0",
  "title": "OP ORDER — ALPHA",
  "classification": "RESTRICTED",
  "ciphertext_fp": "0x4F92A1C8E73B90D2",
  "created_at": 1774880000000.0,
  "recipients": [
    {
      "uid": "OFC-2291",
      "name": "Officer OFC-2291",
      "lockbox_ref": "LB-C38A19",
      "c_u_hex": "a1f8...",
      "status": "delivered"
    },
    {
      "uid": "OFC-1187",
      "name": "Officer OFC-1187",
      "lockbox_ref": "LB-E72F01",
      "c_u_hex": "b9c7...",
      "status": "delivered"
    }
  ],
  "message": "Document encrypted with AES-256-GCM and lockboxes created via ML-KEM."
}
```

---

## 2. POST /request_decryption

### Request Body (`application/json`)
```json
{
  "uid": "OFC-2291",
  "doc_id": "DOC-8F32A1B0",
  "timestamp": "1774880010",
  "signature": "3f8b01c9...",
  "recipient_pk": "a79c02e1..."
}
```

### Response (`200 OK`)
```json
{
  "doc_id": "DOC-8F32A1B0",
  "uid": "OFC-2291",
  "session_id": "SES-19C48E",
  "current_stage": "DELIVERED",
  "w_id": "e84f2910a3c9b740e512d90fa8b21c4309e1f2a34b5c6d7e8f90a1b2c3d4e5f6",
  "ledger_record": {
    "ledgerId": "LR-1",
    "docId": "DOC-8F32A1B0",
    "officerUid": "OFC-2291",
    "sessionId": "SES-19C48E",
    "receipt": "OFC-2291 || DOC-8F32A1B0 || 1774880010",
    "signature": "3f8b01c9...",
    "wId": "e84f2910a3c9b740e512d90fa8b21c4309e1f2a34b5c6d7e8f90a1b2c3d4e5f6",
    "y_current": "a9c2b4...",
    "timestamp": 1774880011000.0,
    "status": "committed",
    "consensusNodes": ["node_1", "node_2", "node_3"]
  },
  "decrypted_content": "Section 4.2 — Movement Schedule\nSector clearance pending final authorization from command.",
  "watermarked_image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
  "pipeline_log": [
    { "stage": "REQUESTED", "status": "SUCCESS", "timestamp": 1774880010.1, "detail": "Decryption request initiated." },
    { "stage": "SIGNATURE_VERIFIED", "status": "SUCCESS", "timestamp": 1774880010.3, "detail": "ML-DSA-65 signature verified over m_receipt" },
    { "stage": "LEDGER_PENDING", "status": "SUCCESS", "timestamp": 1774880010.5, "detail": "Submitting transaction to DLT 3-Node Consensus Cluster..." },
    { "stage": "LEDGER_COMMITTED", "status": "SUCCESS", "timestamp": 1774880010.8, "detail": "DLT Consensus Achieved (3/3). Block #1 committed" },
    { "stage": "TOKEN_RELEASED", "status": "SUCCESS", "timestamp": 1774880011.0, "detail": "Ledger commit verified. Releasing AES-256 payload key." },
    { "stage": "DECRYPTED", "status": "SUCCESS", "timestamp": 1774880011.2, "detail": "In-memory payload decryption complete." },
    { "stage": "WATERMARKED", "status": "SUCCESS", "timestamp": 1774880011.5, "detail": "2D Haar DWT W_ID embedded" },
    { "stage": "DELIVERED", "status": "SUCCESS", "timestamp": 1774880011.7, "detail": "Secure viewer package assembled and ready for delivery." }
  ],
  "message": "Key released after DLT consensus & watermark embedded."
}
```

---

## 3. POST /audit

### Request Body (`application/json`)
```json
{
  "w_id": "e84f2910a3c9b740e512d90fa8b21c4309e1f2a34b5c6d7e8f90a1b2c3d4e5f6"
}
```

### Response (`200 OK`)
```json
{
  "attribution_status": "FOUND",
  "extracted_wid": "e84f2910a3c9b740e512d90fa8b21c4309e1f2a34b5c6d7e8f90a1b2c3d4e5f6",
  "block_id": 1,
  "client_receipt": "OFC-2291 || DOC-8F32A1B0 || 1774880010",
  "client_signature": "3f8b01c9...",
  "y_current": "a9c2b4...",
  "parsed_receipt": {
    "uid": "OFC-2291",
    "doc_id": "DOC-8F32A1B0",
    "timestamp": "1774880010"
  },
  "signature_verified": true,
  "message": "Leak successfully attributed to Officer OFC-2291 for Document DOC-8F32A1B0 committed at Block #1."
}
```

---

## 4. GET /status

### Response (`200 OK`)
```json
{
  "app_name": "ASTRAEA API & Data Flow Backend",
  "status": "ONLINE",
  "version": "1.0.0",
  "ledger_status": {
    "node_id": "NODE-ALPHA",
    "head_block_id": 1,
    "head_hash": "a9c2b4...",
    "genesis_hash": "c001...",
    "total_blocks": 1,
    "status": "ONLINE"
  },
  "crypto_status": {
    "provider": "Post-Quantum Simulator (Development Mode)",
    "kem_algo": "ML-KEM-768",
    "dsa_algo": "ML-DSA-65",
    "symmetric_algo": "AES-256-GCM",
    "hash_chain_algo": "Monotonic Feistel Hash-Chain (MFHC) + BLAKE3",
    "watermark_algo": "2D Haar DWT + Reed-Solomon FEC"
  }
}
```
