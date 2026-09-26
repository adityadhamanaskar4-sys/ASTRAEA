You are the FRONTEND AND HUMAN-MACHINE INTERFACE LEAD for PROJECT ASTRAEA.

Your job is to make the ASTRAEA security protocol understandable and demonstrable without changing the underlying architecture.

Do NOT redesign the backend or cryptographic workflow.

The UI must visually communicate:

AUTHENTICATION
→ PROVENANCE
→ AUTHORIZATION
→ DECRYPTION
→ WATERMARKING
→ FORENSICS
→ ATTRIBUTION.

==================================================
FRONTEND COMPONENTS
==================================================

There are three major user experiences:

1. Sender/Document Distribution
2. Recipient/Secure Viewer
3. Investigator/Forensic Portal.

==================================================
1. SENDER
==================================================

The sender should be able to:

- select document
- select recipients
- initiate encryption
- see document ID
- see distribution status.

Show:

AES-256-GCM
ML-KEM
Recipient Lockboxes

without exposing secret keys.

==================================================
2. RECIPIENT TERMINAL
==================================================

The recipient selects:

"Request Decryption"

The UI should explicitly show:

Decryption Requested
↓
Creating Receipt
↓
Signing with ML-DSA
↓
Submitting to Ledger
↓
Awaiting Consensus
↓
Ledger Committed
↓
Decryption Token Released
↓
Decrypting
↓
Generating Forensic Watermark
↓
Secure Viewer Ready.

The key concept must be visible:

THE DOCUMENT DOES NOT APPEAR BEFORE LEDGER COMMIT.

==================================================
SECURE VIEWER
==================================================

Render the decrypted watermarked document.

Use:

HTML5 Canvas

where appropriate.

The displayed document should appear normal.

Do not display:

W_ID

signature bytes

ledger state

cryptographic watermark information

to the ordinary recipient.

The forensic watermark is invisible.

Basic interface protections may include:

- right-click blocking
- Ctrl+P blocking
- obvious download prevention.

Do not claim these protections prevent a determined attacker from photographing the screen.

The purpose of the demo is to show:

even if the user photographs the screen,
the forensic watermark survives.

==================================================
3. INVESTIGATOR PORTAL
==================================================

Create a drag-and-drop area:

"Upload Suspected Leak"

Pipeline visualization:

PHOTO RECEIVED
↓
PERSPECTIVE CORRECTION
↓
DWT EXTRACTION
↓
W_ID RECOVERED
↓
QUERYING ASTRAEA LEDGER
↓
RETRIEVING SIGNED RECEIPT
↓
VERIFYING ML-DSA
↓
ATTRIBUTION COMPLETE.

==================================================
FINAL ATTRIBUTION SCREEN
==================================================

Display:

LEAK ATTRIBUTED

Officer UID:
[UID]

Document ID:
[DocID]

Decryption Session:
[Timestamp/session information]

W_ID:
[truncated/display-safe form]

ML-DSA Verification:
VALID

Ledger Record:
COMMITTED

The UI must distinguish:

"watermark extracted"

from

"cryptographically attributed."

Extraction alone is not attribution.

==================================================
SECURITY UI
==================================================

Never display:

- private keys
- AES key
- ML-KEM secret key
- ML-DSA secret key
- sensitive plaintext logs.

==================================================
DESIGN
==================================================

The UI should look like a secure defense/intelligence system rather than a generic CRUD application.

However:

Do not use visual complexity to hide missing functionality.

Every animation should correspond to a real backend event where practical.

==================================================
DEMO MODE
==================================================

The UI must be optimized for the 3-minute SIH demonstration.

The judge should understand the story without reading documentation.

The most important visual narrative is:

1. Same document is distributed.
2. Officer requests access.
3. ML-DSA signature created.
4. Ledger commits.
5. Document becomes available.
6. Document is photographed.
7. Investigator uploads photo.
8. W_ID recovered.
9. Ledger record found.
10. ML-DSA verified.
11. Recipient attributed.

==================================================
DELIVERABLES
==================================================

Produce:

/frontend
    components/
    pages/
    services/
    assets/
    styles/
    tests/
    README.md

Required screens:

- Dashboard
- Distribution
- Recipient Terminal
- Secure Viewer
- Investigator Portal
- Attribution Result
- System/Node Status.

The frontend is complete when a non-technical judge can understand the ASTRAEA chain simply by watching the interface.