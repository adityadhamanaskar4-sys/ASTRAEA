# ASTRAEA — Cross-Team Technical Intelligence & Implementation Guide

> **Purpose:** This document gives every ASTRAEA team member the minimum technical knowledge required to correctly implement, integrate, debug, and explain their assigned module.
>
> **Important:** You do **not** need to become a cryptographer. You **do** need to understand what each object means, why it exists, what enters your module, what leaves it, and what must never be changed.

---

# 1. What ASTRAEA Actually Does

ASTRAEA solves one central problem:

> Multiple authorized recipients can decrypt the same document, but if one copy leaks, the system must be able to determine **which authorized decryption event produced that leaked copy** and provide cryptographically verifiable provenance.

The core chain is:

```text
DOCUMENT
    ↓
AES-256-GCM ENCRYPTION
    ↓
Recipient-specific ML-KEM access
    ↓
Recipient requests decryption
    ↓
Decryption receipt created
    ↓
ML-DSA signature
    ↓
Permissioned Ledger
    ↓
MFHC state update
    ↓
Consensus / Commit
    ↓
Decryption material released
    ↓
W_ID generated
    ↓
DWT watermark embedded
    ↓
Recipient views document
    ↓
DOCUMENT LEAKS
    ↓
Photo / Screenshot / Artifact
    ↓
DWT extraction
    ↓
W_ID*
    ↓
Ledger lookup
    ↓
ML-DSA verification
    ↓
CRYPTOGRAPHICALLY VERIFIABLE PROVENANCE
```

The most important rule in the entire project is:

> **The document is not released first and logged later. The decryption event is established in the ledger first, and only then is decryption material released.**

This is the **Ledger-First Decryption** principle. The project specification explicitly places signature verification, ledger state advancement, consensus, commit, and then token release in this order.

---

# 2. First: Do Not Confuse "Quantum" With "Post-Quantum"

ASTRAEA uses **Post-Quantum Cryptography (PQC)**.

It does **not** use a quantum computer to encrypt or decrypt the document.

The relevant algorithms are:

```text
ML-KEM  → Post-Quantum Key Encapsulation
ML-DSA  → Post-Quantum Digital Signature
```

They are designed to provide cryptographic protection against attackers with quantum-computing capabilities.

So when explaining ASTRAEA:

### Correct

> "ASTRAEA uses NIST-standardized post-quantum cryptography."

### Avoid

> "ASTRAEA uses quantum encryption."

> "The document is encrypted using quantum computing."

The first statement is technically accurate; the second statements are misleading.

---

# 3. The Most Important ASTRAEA Objects

Every teammate should know these.

| Symbol / Object | Meaning                                          |
| --------------- | ------------------------------------------------ |
| `D`             | Original plaintext document                      |
| `K_doc`         | Random 256-bit document encryption key           |
| `C_doc`         | AES-256-GCM encrypted document                   |
| `ML-KEM`        | Post-quantum key encapsulation mechanism         |
| `W_u`           | Recipient-specific wrapped document key/token    |
| `UID_u`         | Recipient's unique identity                      |
| `DocID`         | Document identifier                              |
| `Timestamp`     | Time associated with the decryption request      |
| `m_receipt`     | Decryption intent receipt                        |
| `sk_DSA`        | Recipient's ML-DSA private key                   |
| `pk_DSA`        | Recipient's ML-DSA public key                    |
| `σ_u`           | ML-DSA signature over the decryption receipt     |
| `y_(i-1)`       | Previous ledger state                            |
| `M_chain`       | MFHC chain mask                                  |
| `y_i`           | New committed ledger state                       |
| `W_ID`          | 256-bit forensic identifier                      |
| `W_ID*`         | W_ID recovered from a leaked artifact            |
| `DWT`           | Discrete Wavelet Transform used for watermarking |

---

# 4. UID ≠ Signature ≠ W_ID

This is one of the most important things everyone must understand.

These are **different objects**.

```text
UID
│
│ identifies the recipient
│
↓
Decryption Receipt
│
│ is signed
│
↓
ML-DSA Signature σu
│
│ participates in ledger state
│
↓
Ledger State yi
│
│ together with σu
│
↓
W_ID
│
│ embedded into document
│
↓
Watermarked Document
```

Therefore:

```text
UID       ≠ ML-DSA Signature
ML-DSA Signature ≠ MFHC State
MFHC State ≠ W_ID
W_ID      ≠ UID
W_ID      ≠ AES Key
W_ID      ≠ ML-KEM Key
```

### What is W_ID?

`W_ID` is a **forensic identifier for a specific committed decryption event**.

It is derived from:

```text
ML-DSA signature + committed ledger state
```

The current integration specification defines:

```text
W_ID = Truncate256(
          BLAKE3(
              σu || yi
          )
       )
```

The resulting 256-bit value is then used as the watermark payload.

---

# 5. AES-256-GCM

## What is it?

AES is a symmetric encryption algorithm.

ASTRAEA uses:

```text
AES-256-GCM
```

The document is encrypted using a randomly generated 256-bit document key:

```text
K_doc
```

Conceptually:

```text
D + K_doc
    ↓
AES-256-GCM
    ↓
C_doc
```

The architecture specifies:

```text
C_doc = AES-256-GCM(K_doc, D)
```

The important point for non-crypto teammates:

> AES-GCM protects the actual document contents.

It is **not responsible for identifying the recipient**.

It is **not responsible for watermark attribution**.

It is **not the ledger**.

---

# 6. AES-KW

AES-KW means **AES Key Wrap**.

ASTRAEA uses the ML-KEM-derived shared secret to protect/wrap the document key.

Conceptually:

```text
ML-KEM
   ↓
Shared Secret
   ↓
AES-KW
   ↓
Wrapped K_doc
```

Therefore:

```text
AES-GCM → encrypts the document

AES-KW → protects/wraps the document encryption key
```

Do not confuse these two.

---

# 7. ML-KEM

## What is ML-KEM?

ML-KEM is a **post-quantum Key Encapsulation Mechanism**.

Its job in ASTRAEA is related to **securely establishing access to the document encryption key for each authorized recipient**.

The architecture describes:

```text
Recipient ML-KEM public key
          ↓
      Encapsulation
          ↓
    Shared Secret
          ↓
     AES-KW wrapping
          ↓
Recipient-specific key package
```

The important concept:

> ML-KEM answers **"How can this recipient securely obtain the key needed to decrypt the document?"**

It does **not** answer:

> "Who decrypted the document?"

That is handled by the decryption receipt + ML-DSA signature + ledger.

---

# 8. ML-DSA

## What is ML-DSA?

ML-DSA is ASTRAEA's **post-quantum digital signature mechanism**.

Its job is to prove:

> A particular recipient possessing the corresponding private signing key authorized this particular decryption request.

The process is:

```text
UID
+
DocID
+
Timestamp
        ↓
m_receipt
        ↓
ML-DSA.Sign(
    recipient private key,
    m_receipt
)
        ↓
σu
```

The ASTRAEA specification defines:

```text
m_receipt = UIDu || DocID || Timestamp
```

and:

```text
σu = ML-DSA.Sign(
        sk_DSA_u,
        m_receipt
     )
```

The signed receipt is then sent to the ledger consortium.

---

# 9. Digital Signature — What It Actually Means

A digital signature is **not encryption**.

Think of it as:

```text
MESSAGE
   +
PRIVATE KEY
   ↓
SIGNATURE
```

Another party can use:

```text
MESSAGE
   +
SIGNATURE
   +
PUBLIC KEY
   ↓
VALID / INVALID
```

In ASTRAEA:

```text
m_receipt
   ↓
ML-DSA
   ↓
σu
```

The ledger verifies the signature before accepting the event.

Therefore the ledger does not simply trust:

> "User 8472 says they requested decryption."

It receives a cryptographically verifiable signed statement.

---

# 10. The Decryption Receipt

The receipt is the structured representation of the decryption intent.

Conceptually:

```text
m_receipt =
    UID
    ||
    DocID
    ||
    Timestamp
```

Where:

```text
UID       → Who
DocID     → Which document
Timestamp → When
```

This is then signed.

Therefore:

```text
Receipt
   ↓
Signature
   ↓
Ledger Event
```

### Backend teammates must understand:

The receipt must be treated as **structured security data**, not merely a UI message.

Do not randomly change:

* field names
* field ordering
* serialization
* timestamp format
* byte encoding

after cryptographic signing has been implemented.

A signature is calculated over exact bytes.

---

# 11. What Is MFHC?

MFHC = **Monotonic Feistel Hash-Chain**.

For ASTRAEA, MFHC is used to maintain a **tamper-evident chained provenance state** for decryption events.

The important idea is:

```text
Previous Ledger State
        ↓
New Decryption Event
        ↓
New Ledger State
```

Therefore:

```text
y0
 ↓
y1
 ↓
y2
 ↓
y3
 ↓
y4
```

Each state depends on the previous state.

If somebody modifies an earlier event, the expected subsequent state relationship no longer matches.

---

# 12. MFHC Is NOT the Document Encryption

This distinction is critical.

MFHC does:

```text
Ledger provenance
+
State chaining
+
Tamper evidence
```

MFHC does **not** replace:

```text
AES-256-GCM
ML-KEM
ML-DSA
```

Think of the architecture as:

```text
AES-GCM
    ↓
Protects DOCUMENT

ML-KEM
    ↓
Protects KEY ACCESS

ML-DSA
    ↓
Authenticates DECRYPTION REQUEST

MFHC
    ↓
Chains LEDGER PROVENANCE

DWT
    ↓
Embeds FORENSIC IDENTIFIER
```

Each technology has a different job.

---

# 13. MFHC State

The ledger maintains:

```text
y_(i-1)
```

for the previous event.

The new event contains:

```text
σu
m_receipt
```

and generates a new state:

```text
yi
```

The current implementation guide defines the state update as:

```text
yi =
BLAKE3(
    y_prev
    ||
    M_chain
    ||
    σu
    ||
    m_receipt
)
```

The chain mask is generated from the previous state and node key according to the current MFHC implementation specification.

### The important concept for everyone:

```text
Previous State
      +
Current Signed Event
      ↓
New State
```

The exact cryptographic implementation belongs to the Crypto/DLT side.

Other teammates should **not modify the MFHC formula independently**.

---

# 14. What Is BLAKE3?

BLAKE3 is a cryptographic hash function.

A hash converts input data into a fixed-size digest.

Conceptually:

```text
Input
  ↓
BLAKE3
  ↓
Digest
```

ASTRAEA uses BLAKE3 in multiple places.

For example:

```text
MFHC state generation
```

and:

```text
W_ID generation
```

### Important:

Hashing is not the same as encryption.

```text
Encryption:
data → encrypted data → decryptable with key

Hash:
data → digest
```

Do not call a BLAKE3 digest an encryption key.

---

# 15. What Is DLT?

DLT = **Distributed Ledger Technology**.

ASTRAEA uses a **permissioned local ledger**, rather than a public blockchain.

The purpose is to record:

```text
Who requested decryption
+
Which document
+
When
+
Their cryptographic signature
+
The resulting ledger state
```

The architecture describes a localized consortium of internal nodes.

---

# 16. Why Multiple Ledger Nodes?

The system uses multiple ledger replicas to demonstrate that one administrator/node should not be able to silently rewrite the complete provenance history.

For the prototype:

```text
        Backend
           │
     ┌─────┼─────┐
     ↓     ↓     ↓
   Node1 Node2 Node3
     │     │     │
     └─────┼─────┘
           ↓
      Agreement
           ↓
        Commit
```

The current implementation guide specifies:

```text
3 ledger replicas
```

and a strict majority:

```text
2 / 3
```

for the prototype's consensus simulation.

### Important terminology

Do not claim:

> "We implemented Ethereum."

Do not claim:

> "We implemented Hyperledger."

The project uses a **lightweight permissioned ledger prototype / consortium simulation** rather than a production public blockchain network.

---

# 17. What Is Consensus?

Consensus means the participating ledger nodes agree on the event/state that should be committed.

ASTRAEA's simplified prototype flow:

```text
Backend
   ↓
Node 1 ──┐
Node 2 ──┼──→ Compare results
Node 3 ──┘
             ↓
        Majority agreement
             ↓
           Commit
```

The current implementation guide specifies that Backend 1 broadcasts the commit request to the three nodes and only releases the AES decryption key after a strict majority returns the same `y_i`.

---

# 18. What Is "Ledger-First Decryption"?

This is one of ASTRAEA's most important security concepts.

### Incorrect sequence

```text
Decrypt
  ↓
Show document
  ↓
Log event
```

Problem:

The document has already been released before provenance is established.

### ASTRAEA sequence

```text
Request Decryption
       ↓
Create Receipt
       ↓
ML-DSA Sign
       ↓
Ledger Verification
       ↓
MFHC State Update
       ↓
Consensus
       ↓
Commit
       ↓
Release Decryption Material
       ↓
Decrypt
       ↓
Generate W_ID
       ↓
Watermark
       ↓
Display
```

The frontend, backend, crypto service, and DLT implementation must all preserve this order.

---

# 19. What Is W_ID?

`W_ID` = **Watermark / Forensic Identifier**.

It is derived after the decryption event has been committed.

The current implementation specification defines:

```text
W_ID =
Truncate256(
    BLAKE3(
        σu || yi
    )
)
```

Therefore:

```text
Recipient-specific signature
          +
Committed ledger state
          ↓
       BLAKE3
          ↓
        W_ID
```

The important security property is the dependency:

```text
W_ID
  depends on
σu + yi
```

So it is tied to the cryptographically recorded decryption event.

---

# 20. W_ID Is Not Random

Do **not** generate:

```text
UUID()
```

and call that the ASTRAEA watermark.

The watermark payload is derived from the cryptographic provenance information.

Conceptually:

```text
σu
+
yi
↓
BLAKE3
↓
256-bit W_ID
```

The CV/steganography module receives this value.

---

# 21. What Is DWT?

DWT = **Discrete Wavelet Transform**.

It transforms image information into frequency-related components.

ASTRAEA uses DWT for the image/PDF watermarking path.

Conceptually:

```text
Original Image
      ↓
     DWT
      ↓
Frequency Components
      ↓
Embed W_ID
      ↓
Inverse DWT
      ↓
Watermarked Image
```

The current integration guide specifically requires the 256-bit W_ID to be injected into the image frequency domain using 2D DWT.

---

# 22. Why DWT?

The purpose is to create a watermark that is:

* visually unobtrusive
* embedded into the document/image representation
* recoverable through forensic processing
* suitable for the physical leak demonstration

The CV teammate should understand:

> The CV system is **not identifying the officer using AI**.

It is recovering:

```text
W_ID*
```

from the leaked artifact.

The cryptographic ledger then performs the attribution.

---

# 23. DWT Extraction

The reverse process is:

```text
Leaked Photo / Image
       ↓
Pre-processing
       ↓
Perspective / Deskew correction
       ↓
DWT
       ↓
Extract embedded bits
       ↓
W_ID*
       ↓
/audit
       ↓
Ledger lookup
```

The CV module therefore produces:

```text
W_ID*
```

It does **not** directly produce:

```text
Officer UID
```

That information comes from the ledger lookup.

---

# 24. W_ID vs W_ID*

This distinction should be used consistently.

### `W_ID`

The original forensic identifier generated during the authorized decryption event.

```text
σu + yi
 ↓
W_ID
```

### `W_ID*`

The identifier recovered from the leaked artifact.

```text
Leaked artifact
 ↓
DWT extraction
 ↓
W_ID*
```

Then:

```text
W_ID* == expected W_ID
```

If a ledger entry produces the same value, the corresponding signed event can be retrieved.

---

# 25. Forensic Attribution

ASTRAEA does **not** work like:

```text
AI looks at photograph
        ↓
AI says Officer 8472
```

Instead:

```text
Leaked Photograph
       ↓
DWT Extraction
       ↓
W_ID*
       ↓
Ledger Search
       ↓
Find matching σu + yi
       ↓
Recover Receipt
       ↓
Recover UID
       ↓
Verify ML-DSA Signature
       ↓
Cryptographically Verifiable Provenance
```

This distinction is extremely important when explaining the project to judges.

---

# 26. PDF Text Watermarking

The ASTRAEA specification also describes a separate text steganography path using **Unicode zero-width characters** for raw text payloads.

Conceptually:

```text
Visible text:

CLASSIFIED DOCUMENT

Underlying character stream:

CLASSIFIED
[zero-width payload]
DOCUMENT
```

The visible appearance can remain unchanged.

However:

> The exact zero-width encoding/decoding scheme must be standardized by the team before implementation.

Do not have different teammates invent different mappings.

The same ASTRAEA `W_ID` should remain the source forensic identifier if this channel is implemented.

---

# 27. DWT vs Text Watermark

These are different technical channels.

| Channel                   | Technique          | Main purpose                                       |
| ------------------------- | ------------------ | -------------------------------------------------- |
| Image / rendered document | DWT                | Recover watermark from visual/photographic leakage |
| Raw/selectable text       | Zero-width Unicode | Carry invisible information in text representation |

Do not say:

> "DWT inserts characters into the PDF."

And do not say:

> "Zero-width Unicode is the same as DWT."

They are separate mechanisms.

---

# 28. Air-Gapped Architecture

ASTRAEA is designed for an offline / air-gapped environment.

That means:

```text
ASTRAEA
   ↓
Internal Network
   ↓
No Internet Dependency
```

The architecture specifically targets operation within a secure isolated environment.

For the prototype, the integration guide specifies an internal Docker network with:

```text
internal: true
```

to prevent outbound access from the Docker network.

### DevSecOps must understand:

Air-gapped does **not** mean:

> "The application cannot communicate."

It means:

> "The application communicates only through the controlled local infrastructure and has no external Internet dependency."

---

# 29. Volatile Memory

ASTRAEA's document decryption path is designed to avoid unnecessarily writing plaintext to persistent storage.

The architecture describes streaming decrypted content through memory, including `io.BytesIO`.

Conceptually:

```text
Encrypted Document
       ↓
Decrypt
       ↓
Memory
       ↓
Watermark
       ↓
Viewer
```

rather than:

```text
Decrypt
  ↓
Save plaintext.pdf
  ↓
Open plaintext.pdf
```

The reason is simple:

> Persistent plaintext files create an additional leakage surface.

---

# 30. Frontend Security Terminology

The frontend may show:

```text
Generating ML-DSA Signature...
Awaiting Ledger Consensus...
Ledger Commit Confirmed...
Generating Forensic W_ID...
Rendering Watermarked Document...
```

These messages must correspond to **real backend events**.

They must not merely be animations.

The integration guide explicitly calls for the UI to demonstrate the ledger-first constraint.

---

# 31. Right-Click / Ctrl+P Blocking

The frontend may block:

```text
Right click
Ctrl + P
```

This is useful as a **basic deterrence mechanism**.

But everyone must understand:

> This is NOT a cryptographic security boundary.

It cannot prevent:

```text
Phone camera
External camera
Second device
Operating-system-level capture
```

That is precisely why ASTRAEA needs the forensic watermark.

---

# 32. Complete ASTRAEA Dependency Chain

Every teammate should memorize this:

```text
                 ┌─────────────────┐
                 │  Plain Document │
                 └────────┬────────┘
                          ↓
                   AES-256-GCM
                          ↓
                 Encrypted Document
                          ↓
                    ML-KEM Access
                          ↓
              Recipient Requests Decrypt
                          ↓
                  Decryption Receipt
                          ↓
                      ML-DSA
                          ↓
                  Signature σu
                          ↓
              Permissioned DLT / MFHC
                          ↓
                    Consensus
                          ↓
                       Commit
                          ↓
                  Ledger State yi
                          ↓
              ┌───────────┴───────────┐
              ↓                       ↓
         Key Release              W_ID Derivation
                                      ↓
                         BLAKE3(σu || yi)
                                      ↓
                                     W_ID
                                      ↓
                                  DWT Embed
                                      ↓
                              Watermarked Artifact
                                      ↓
                                  LEAK
                                      ↓
                              Photo / Screenshot
                                      ↓
                                DWT Extraction
                                      ↓
                                     W_ID*
                                      ↓
                                 /audit
                                      ↓
                             Ledger Recalculation
                                      ↓
                              Matching Event
                                      ↓
                             ML-DSA Verification
                                      ↓
                             Provenance / Attribution
```

---

# 33. Team-Specific Knowledge Requirements

# A. Cybersecurity / Cryptography — You

You are responsible for the deepest cryptographic understanding.

You must understand:

* ML-KEM
* ML-DSA
* Public/private keys
* Digital signatures
* Signature verification
* AES-256-GCM
* AES-KW
* BLAKE3
* MFHC
* Ledger state
* `σu`
* `yi`
* `W_ID`
* Byte-level serialization
* Cryptographic input/output dependencies
* Key handling
* Memory-only decryption flow

Your most important responsibility:

> **Prevent other modules from breaking the cryptographic dependency chain.**

---

# B. DLT / Backend Ledger Developer

You must understand:

### Inputs

```text
m_receipt
σu
previous ledger state
node configuration
```

### Processing

```text
Verify ML-DSA
      ↓
Generate MFHC state
      ↓
Create ledger entry
      ↓
Return yi
```

### Outputs

```text
Committed ledger event
yi
Audit information
```

You must understand:

* What a signature is
* Why the signature must be verified
* Why `m_receipt` matters
* Why `y_prev` matters
* Why changing an old ledger event affects the chain
* What consensus means
* Why three nodes exist
* Why `W_ID` is derived later
* Why `/audit` must be able to reproduce the expected W_ID

### You must NOT:

* invent a different hash formula
* remove the previous state dependency
* store only the UID and call it provenance
* bypass signature verification
* release the key before commit
* silently modify serialization

---

# C. Backend API / Orchestration Developer

You are the **traffic controller**.

You need to understand the exact sequence:

```text
Frontend
   ↓
Decryption Request
   ↓
Receipt Generation
   ↓
Signature
   ↓
Ledger
   ↓
Consensus
   ↓
Commit
   ↓
Key Release
   ↓
Watermark Generation
   ↓
Viewer
```

Your biggest responsibility is **ordering**.

The backend must not accidentally implement:

```text
Key Release → Ledger
```

when ASTRAEA requires:

```text
Ledger Commit → Key Release
```

You also need to understand what each API payload represents.

---

# D. CV / Steganography Developer

You do not need to become a cryptographer.

But you MUST understand:

```text
W_ID = forensic payload
```

and:

```text
W_ID* = extracted forensic payload
```

Your input:

```text
W_ID
```

Your output:

```text
W_ID*
```

You do NOT directly determine the recipient.

Your pipeline is:

```text
Image / PDF
     ↓
DWT Embedding
     ↓
Watermarked Artifact
```

and later:

```text
Leaked Photo
     ↓
Pre-processing
     ↓
DWT Extraction
     ↓
W_ID*
```

Then send `W_ID*` to the ledger audit service.

### You must understand:

* DWT
* Frequency-domain embedding
* 256-bit payload
* Image preprocessing
* Perspective correction
* Deskew
* Extraction reliability
* Why photographed screens are difficult
* Difference between embedding and extraction

---

# E. Frontend Developer

You need to understand the **security state machine**, not the cryptographic mathematics.

Your UI must represent:

```text
REQUESTED
    ↓
SIGNING
    ↓
LEDGER VERIFICATION
    ↓
CONSENSUS
    ↓
COMMITTED
    ↓
KEY RELEASED
    ↓
DECRYPTING
    ↓
WATERMARKING
    ↓
VIEWING
```

You should know:

> The UI must never imply that decryption has happened before the ledger has committed the event.

The secure viewer may use Canvas and basic browser-level controls, but those are supplementary controls—not the main security mechanism.

---

# F. DevSecOps

You need to understand the deployment security model:

```text
Frontend
Backend
Crypto Service
DLT Nodes
CV Service
       ↓
Internal Docker Network
       ↓
No External Internet
```

You must understand:

* Docker
* Docker Compose
* isolated services
* internal network
* persistent ledger volumes
* independent ledger nodes
* environment configuration
* service-to-service communication
* reproducible deployment

You should be able to demonstrate:

```text
docker compose up
```

and explain what every container is doing.

---

# 34. Integration Contracts

Each team should treat these as fixed contracts.

## Contract 1 — Crypto → Backend

Crypto provides:

```text
m_receipt
σu
```

Backend must preserve them exactly.

---

## Contract 2 — Ledger → Backend

Ledger returns:

```text
status
yi
commit confirmation
```

Backend uses this to determine whether key release is allowed.

---

## Contract 3 — Crypto → Watermark Module

Crypto provides:

```text
σu
yi
```

The watermark module derives/receives:

```text
W_ID
```

---

## Contract 4 — CV → Ledger

CV provides:

```text
W_ID*
```

Ledger performs:

```text
W_ID* lookup / recalculation
```

---

## Contract 5 — Ledger → Investigator

Ledger returns the matching:

```text
m_receipt
σu
UID / recipient information
ledger provenance
```

The signature is then verified.

---

# 35. What Must NEVER Be Changed Casually

The following are architecture-sensitive:

```text
ML-KEM
ML-DSA
AES-256-GCM
AES-KW
BLAKE3
m_receipt structure
σu
MFHC state dependency
W_ID derivation
DWT payload
Ledger-first ordering
Consensus-before-key-release
```

If someone wants to change one of these:

> **Stop integration and discuss it with the Cyber/Crypto lead first.**

A "small" change in cryptographic serialization can invalidate signatures or make `W_ID` impossible to reproduce.

---

# 36. Common Misunderstandings to Avoid

### ❌ "W_ID is the officer ID."

No.

```text
UID = identity
W_ID = forensic event identifier
```

---

### ❌ "ML-DSA encrypts the document."

No.

```text
ML-DSA = signature
AES-GCM = document encryption
```

---

### ❌ "ML-KEM signs the request."

No.

```text
ML-KEM = key encapsulation
ML-DSA = digital signature
```

---

### ❌ "BLAKE3 encrypts the document."

No.

```text
BLAKE3 = cryptographic hashing
```

---

### ❌ "MFHC is the encryption algorithm."

No.

```text
MFHC = ledger provenance/state chaining
```

---

### ❌ "CV identifies the officer."

Not directly.

```text
CV → W_ID*
Ledger → matching event
ML-DSA → cryptographic verification
```

---

### ❌ "The watermark is a random UUID."

No.

It is derived from cryptographic provenance:

```text
σu + yi → W_ID
```

---

### ❌ "Consensus means all three servers must be identical blockchain nodes."

For this prototype, the implementation uses three local ledger replicas and a majority-based consensus simulation. Do not describe this as a production blockchain consensus protocol.

---

### ❌ "Blocking Ctrl+P prevents screenshots."

No.

It only provides basic browser-level deterrence.

The forensic watermark exists because the system assumes that a physical or external capture can still occur.

---

# 37. The One-Minute Explanation Every Teammate Should Be Able to Give

If a judge asks:

> **"Explain ASTRAEA in simple technical terms."**

Every team member should be able to say approximately:

> "ASTRAEA encrypts the document once using AES-256-GCM and provides authorized recipients with recipient-specific post-quantum access using ML-KEM. Before a recipient can decrypt, the client creates a decryption receipt containing the recipient identity, document ID, and timestamp, and signs it using ML-DSA. The signed event is verified and committed to our permissioned ledger using an MFHC-based chained state and majority consensus. Only after the event is committed is the decryption material released. The system then derives a 256-bit forensic identifier from the ML-DSA signature and committed ledger state, embeds it into the document using DWT, and presents the watermarked document. If a copy leaks, the identifier can be extracted from the leaked artifact and matched against the ledger. The corresponding signed event is then retrieved and its ML-DSA signature verified, providing cryptographically verifiable provenance."

If they understand that paragraph, they understand the **ASTRAEA system**.

---

# 38. The Golden Rule

Everyone on the team should remember this:

```text
                    ASTRAEA
                       │
                       ↓
              TRUST THE EVENT FIRST
                       │
                       ↓
              RECORD THE EVENT
                       │
                       ↓
             RELEASE DECRYPTION
                       │
                       ↓
              WATERMARK THE COPY
                       │
                       ↓
              RECOVER THE WATERMARK
                       │
                       ↓
             VERIFY THE PROVENANCE
```

Or, even shorter:

> **Sign → Verify → Chain → Commit → Release → Watermark → Extract → Verify**

That is the operational backbone of ASTRAEA.

---

# 39. Final Team Rule

Nobody needs to know every implementation detail of every other module.

But everyone must know:

### 1. What am I receiving?

### 2. What does that data actually mean?

### 3. What am I producing?

### 4. Who consumes my output?

### 5. What security property does my module provide?

### 6. What happens if my module fails?

### 7. Which values are cryptographically sensitive?

### 8. Which architecture rules am I not allowed to change?

If every teammate can answer those eight questions, the project stops being:

```text
6 people → 6 independent modules
```

and becomes:

```text
             ONE ASTRAEA SYSTEM

Crypto ──┐
DLT ─────┤
Backend ─┤
CV ──────┤──→ Integrated Provenance Pipeline
Frontend ┤
DevSecOps┘
```

**ASTRAEA is only correct when the complete chain is correct.**
