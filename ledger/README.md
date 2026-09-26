# ASTRAEA: Monotonic Feistel Hash-Chain (MFHC) Ledger

This directory contains the permissioned Distributed Ledger Technology (DLT) subsystem for **Project ASTRAEA** (SIH26237). 

It implements an immutable, append-only provenance ledger that replaces standard, resource-heavy blockchains (Ethereum / Hyperledger) with a lightweight, localized **Monotonic Feistel Hash-Chain (MFHC)**.

---

## 🔒 The Core Security Invariant

> **Ledger-Gated Decryption Principle:**
> Decryption keys ($K_{doc}$) are **never** released simply because an officer is authenticated. 
> The decryption key is released **only after**:
> 1. The recipient cryptographically signs an intent receipt ($m_{receipt}$) with NIST FIPS 204 ML-DSA.
> 2. The event is mathematically fused into the MFHC state ($y_i$).
> 3. The 3-node consortium consensus confirms the commit.
> 4. The 256-bit steganographic watermark identifier ($W_{ID}$) is derived from the committed state.

---

## 📐 Mathematical Formulation

### 1. The Monotonic Feistel Mask
When a block is committed, the node scrambles algebraic linearity using a discrete quadratic transform:

$$\text{xor\_val} = y_{\text{prev}} \oplus \text{NODE\_KEY}$$

$$f_{\text{val}} = (\text{xor\_val}^2 + \text{xor\_val} + 1) \pmod{2^{256}}$$

$$M_{\text{chain}} = \text{BLAKE3}(f_{\text{val}})$$

### 2. State Avalanche (Block Committal)
The new block hash fuses the previous state, the Feistel mask, the client signature, and the receipt:

$$y_i = \text{BLAKE3}(y_{\text{prev}} \parallel M_{\text{chain}} \parallel \sigma_u \parallel m_{\text{receipt}})$$

### 3. Forensic Watermark ID ($W_{ID}$)
Derived strictly from the cryptographically verified signature and the committed state:

$$W_{ID} = \text{BLAKE3}(\sigma_u \parallel y_i) \quad \text{(256 bits / 32 bytes)}$$

---

## 📦 Database Schema & Genesis Block

The ledger uses **SQLite** in WAL (Write-Ahead Logging) mode, requiring zero external database installations (`sqlite3` is built into Python).

```sql
CREATE TABLE blocks (
    block_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    y_prev TEXT NOT NULL,
    mask TEXT NOT NULL,
    client_signature TEXT NOT NULL,
    client_receipt TEXT NOT NULL,
    y_current TEXT NOT NULL
);
```

- **Genesis Block (#1)**:
  - `y_prev`: `"0000000000000000000000000000000000000000000000000000000000000000"` (64 zeros)
  - `mask`: `"0000000000000000000000000000000000000000000000000000000000000000"`
  - `client_signature`: `"GENESIS"`
  - `client_receipt`: `"GENESIS"`
  - `y_current`: `BLAKE3("ASTRAEA_GENESIS_BLOCK")`

---

## 🚀 Quickstart & Usage

### 1. Installation & Prerequisites
Ensure dependencies are installed:
```bash
pip install blake3 fastapi uvicorn pydantic httpx
```

---

### 2. Python API Usage

#### A. Initialize Engine & Add a Block
```python
from ledger import LedgerEngine, LedgerConfig

# Initialize ledger (uses data/ledger.db by default)
engine = LedgerEngine()

# Intent receipt format: UID || DocID || Timestamp
receipt = "OFFICER_MALHOTRA || DOC_TOPSECRET_PQC || 2026-09-25T17:30:00Z"
signature = "aa" * 32  # 32-byte client signature

# Request to add a block
response = engine.commit_block(
    client_receipt=receipt,
    client_signature=signature
)

print(f"Block ID   : #{response.block_id}")
print(f"State Hash : {response.y_current}")
print(f"W_ID       : {response.w_id}")
```

#### B. Traverse the Ledger Blocks
```python
# Traverse from Genesis -> Head (Ascending)
traversal_asc = engine.traverse_blocks(reverse=False)
for block in traversal_asc.blocks:
    print(f"Block #{block.block_id} | Receipt: {block.client_receipt} | Hash: {block.y_current[:16]}...")

# Traverse from Head -> Genesis (Descending)
traversal_desc = engine.traverse_blocks(reverse=True)

# Paginated Traversal (e.g. page 2 with limit 10)
page = engine.traverse_blocks(offset=10, limit=10)

# Direct Lookup
block = engine.get_block_by_id(2)
```

#### C. Audit Cryptographic Chain Integrity (Tamper Detection)
Traverses the chain from Genesis to Head, re-computing all Feistel masks and avalanche hashes:
```python
report = engine.verify_chain_integrity()

if report.is_valid:
    print(f"Ledger intact! Total blocks: {report.total_blocks}")
else:
    print(f"Tamper detected at Block #{report.broken_at_block_id}!")
    print(f"Reason: {report.error_reason}")
```

#### D. Reverse Forensic Watermark Audit (`/ledger/audit`)
When an investigator extracts a watermark ($W_{ID}^*$) from a leaked smartphone photograph:
```python
extracted_wid = "7c09eec63917263e12734926b6f47320df223b0a7270bc6ca5cf27b2ec6fc112"

audit_res = engine.audit_forensic_wid(extracted_wid)

if audit_res.attribution_status == "FOUND":
    print(f"Leak Attributed to: {audit_res.parsed_receipt['uid']}")
    print(f"Document ID       : {audit_res.parsed_receipt['doc_id']}")
    print(f"Timestamp         : {audit_res.parsed_receipt['timestamp']}")
    print(f"Signature Valid   : {audit_res.signature_verified}")
```

#### E. 3-Node Consortium Consensus Simulation
Simulates a permissioned consortium of 3 air-gapped nodes requiring a strict 2-of-3 majority:
```python
import asyncio
from ledger.consensus import ConsensusCoordinator

coordinator = ConsensusCoordinator.create_in_memory_or_local_cluster("data/cluster")

result = asyncio.run(coordinator.commit_distributed(
    client_receipt="OFFICER_COMMANDER || WAR_PLAN || 2026-09-25T21:00:00Z",
    client_signature="bb" * 32
))

print(f"Consensus Achieved: {result.consensus_achieved}")
print(f"Quorum: {result.quorum_fraction}")
print(f"Key Release Authorized: {result.authorization_granted}")
```

---

## 🌐 REST API Service

### Starting the Server
```bash
uvicorn ledger.api:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger documentation is available at: **`http://127.0.0.1:8000/docs`**

### API Endpoints Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/ledger/commit` | Request to add a block (state avalanche + $W_{ID}$ derivation) |
| `GET` | `/ledger/blocks` | Traverse blocks with pagination (`offset`, `limit`, `reverse`) |
| `GET` | `/ledger/blocks/{block_id}` | Retrieve individual block by sequence index |
| `GET` | `/ledger/blocks/hash/{y_hash}` | Retrieve individual block by committed state hash |
| `GET` | `/ledger/verify` | Traverse and verify full cryptographic chain integrity |
| `POST` | `/ledger/audit` | Forensic reverse lookup using extracted $W_{ID}^*$ |
| `GET` | `/ledger/status` | Node health, head hash, and block height |

---

### cURL Examples

#### 1. Commit a Block
```bash
curl -X POST "http://127.0.0.1:8000/ledger/commit" \
     -H "Content-Type: application/json" \
     -d '{
       "client_receipt": "OFFICER_VERMA || TOPSECRET_DOC_01 || 2026-09-25T18:00:00Z",
       "client_signature": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
     }'
```

#### 2. Traverse Blocks
```bash
curl "http://127.0.0.1:8000/ledger/blocks?offset=0&limit=10&reverse=false"
```

#### 3. Audit Forensic Watermark
```bash
curl -X POST "http://127.0.0.1:8000/ledger/audit" \
     -H "Content-Type: application/json" \
     -d '{
       "extracted_wid": "7c09eec63917263e12734926b6f47320df223b0a7270bc6ca5cf27b2ec6fc112"
     }'
```

#### 4. Verify Chain Integrity
```bash
curl "http://127.0.0.1:8000/ledger/verify"
```

---

## 🧪 Testing & Verification

### Run the Interactive Demo
```bash
python run_ledger_demo.py
```
*Executes an end-to-end demonstration showing Genesis creation, adding 3 decryption blocks, displaying formatted traversal tables, simulating an insider tamper in SQLite to demonstrate immediate avalanche failure, performing a forensic leak attribution, and running a 3-node consensus simulation.*

### Run the Automated Unit & Integration Tests
```bash
python -m unittest tests/test_ledger.py -v
```
*(Runs 13 comprehensive tests covering all edge cases, hash chaining, pagination, tamper resistance, and REST endpoints).*
