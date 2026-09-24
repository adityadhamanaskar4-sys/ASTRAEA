# ASTRAEA Integration Guide: Monotonic Feistel Hash-Chain (MFHC)

## 1. Core Concept (Cross-Team Context)

The Monotonic Feistel Hash-Chain (MFHC) replaces standard, heavy blockchain networks (Ethereum/Hyperledger) with a lightweight, localized Directed Acyclic Graph (DAG).

For this prototype, the MFHC is built as an append-only SQLite database wrapped in a FastAPI application. Every new decryption log is mathematically fused to the hash of the previous log using a discrete monotonic transform. If a rogue administrator deletes or modifies a row, the hashes of all subsequent rows shatter instantly, triggering a system failure.

To satisfy the MoD's decentralized ledger requirement, DevSecOps will spin up 3 identical replicas of this API container to simulate a permissioned consortium network.

---

## 2. Backend (Ledger/DLT Node) Implementation Guide

### A. SQLite Schema & Genesis Block

On server startup, check if `ledger.db` exists. If empty, create the schema and insert a Genesis Block.

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

**Genesis Row:** `y_prev = "0000...00"`, `client_signature = "GENESIS"`, `client_receipt = "GENESIS"`, `y_current = BLAKE3("ASTRAEA_GENESIS_BLOCK")`.

### B. The Monotonic Mask Generator

When `POST /ledger/commit` is called, generate the Feistel mask before hashing the block.

1. Read `y_prev` (hex string) from the last row and convert to an integer.
2. Read `NODE_KEY` from the `.env` file and convert to an integer.
3. Compute XOR: $\text{xor\_val} = \text{y\_prev}_{int} \oplus \text{NODE\_KEY}_{int}$
4. Apply discrete monotonic transform $f(x)$ to scramble algebraic linearity:

$$f_{val} = (\text{xor\_val}^2 + \text{xor\_val} + 1) \pmod{2^{256}}$$


5. Hash the result to generate the mask:

$$\mathbf{M}_{chain} = \text{BLAKE3}(f_{val})$$



### C. The State Avalanche (Block Committal)

1. Verify the incoming ML-DSA Dilithium signature (`sigma_u`).
2. Generate $\mathbf{M}_{chain}$ (from Step B).
3. Compute the new block hash:

$$\mathbf{y}_i = \text{BLAKE3}(\text{y\_prev} \parallel \mathbf{M}_{chain} \parallel \sigma_u \parallel m_{receipt})$$


4. Insert the new block into `blocks`.
5. Return `{"status": "authorized", "y_i": y_i}` to Backend 1.

### D. Forensic Lookup (`/ledger/audit`)

The ledger does not store the watermark ID directly. It recalculates it dynamically to find a leak.

1. Receive `extracted_W_ID` from the ML module.
2. Query all `client_signature` ($\sigma_u$) and `y_current` ($\mathbf{y}_i$) combinations from the database.
3. For each block, calculate:

$$W_{expected} = \text{BLAKE3}(\sigma_u \parallel \mathbf{y}_i)$$


4. If $W_{expected} == W_{extracted\_W\_ID}$, return the matching `client_receipt` and `client_signature` as cryptographic proof.

---

## 3. DevSecOps Integration Guide

### A. Permissioned Consortium Simulation

Do not build complex P2P consensus. Simulate it using Docker networking.

1. Write a `docker-compose.yml` that defines 3 identical replicas of the Backend Ledger container (`ledger_node_1`, `ledger_node_2`, `ledger_node_3`).
2. Map each container to its own isolated SQLite volume to prove independent state storage.
3. **Air-Gap Enforcement:** Define a custom Docker bridge network with `internal: true`. This disables all outbound internet access, strictly meeting the MoD SCIF requirement.

### B. Async Broadcast Consensus

Backend 1 must be configured to broadcast the `POST /ledger/commit` payload to all 3 nodes simultaneously using Python's `asyncio.gather()`. Backend 1 will only release the AES decryption key to the Frontend if a strict majority (2 out of 3 nodes) return an identical `y_i` hash.

---

## 4. ML (Steganography) Integration Guide

### A. Watermark Derivation Dependency

The 256-bit payload embedded into the document is not a random UUID. It is strictly derived from the MFHC output.

1. Wait for Backend 1 to provide the ML-DSA signature ($\sigma_u$) and the authorized ledger block state ($\mathbf{y}_i$).
2. The Crypto Lead's module will calculate the exact watermark ID:

$$W_{ID} = \text{Truncate}_{256}(\text{BLAKE3}(\sigma_u \parallel \mathbf{y}_i))$$


3. Inject this specific $W_{ID}$ binary sequence into the image frequency domain using 2D Discrete Wavelet Transform (DWT).

---

## 5. Frontend Integration Guide

### A. Zero-Trust Interaction Flow

The UI must visually prove the Ledger-First constraint.

1. When the user clicks "Decrypt," do not show a generic spinner.
2. Display a modal: `[SYSTEM] Generating local ML-DSA Signature...`
3. Display: `[SYSTEM] Awaiting Permissioned Ledger Consensus...`
4. Transmit the JSON intent receipt and the signature to Backend 1.
5. Upon 200 OK, initialize the HTML5 Canvas and stream the watermarked bytes into memory. Add JavaScript event listeners intercepting `contextmenu` and `Ctrl+P` to mitigate basic digital exfiltration.