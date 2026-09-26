# ASTRAEA — Frontend / Human-Machine Interface

A React + Vite console that makes the ASTRAEA secure-document chain
visible and demonstrable, end to end, without changing or reimplementing
its cryptographic architecture:

```
AUTHENTICATION → PROVENANCE → AUTHORIZATION → DECRYPTION →
WATERMARKING → FORENSICS → ATTRIBUTION
```

This repo is the **frontend only**. It simulates the backend (ledger,
consensus, encryption, signing) in-browser so the full story can be
demoed with no server, but every stage of the UI narrates a specific,
named backend event — nothing is animation for its own sake.

## Quick start

```bash
npm install
npm run dev      # starts Vite on http://localhost:5173
npm run test     # runs the unit tests (vitest)
npm run build    # production build to /dist
```

No environment variables or backend are required — state lives in
`localStorage` under the key `astraea_state_v1`. Clear that key (or your
browser storage) to reset the demo to a clean slate.

## The three experiences

1. **Sender / Distribution** (`/distribution`) — pick a document and
   recipients, initiate encryption, see the document ID and per-recipient
   lockbox status. Shows the AES-256-GCM / ML-KEM / ML-DSA primitives in
   use without ever exposing key material.
2. **Recipient Terminal** (`/recipient`) — request decryption as one of
   the demo officers and watch the full chain: receipt creation, ML-DSA
   signing, ledger submission, consensus, commit, token release,
   decryption, watermark generation, viewer ready. **The document does
   not render until the ledger commit step completes** — the Secure
   Viewer has nothing to show before that.
3. **Investigator Portal** (`/investigator`) — drag in a suspected leak
   image. The pipeline recovers the forensic mark, queries the ledger,
   retrieves the signed receipt, and verifies the ML-DSA signature. The
   UI is deliberately explicit that **extraction is not attribution**:
   a mark can be recovered from an image with no matching ledger record,
   and that case is shown distinctly from a verified match.

Supporting screens: **Dashboard** (overview + demo narrative map),
**Secure Viewer** (`/viewer`, the watermarked render + basic
right-click/print deterrents), **Attribution Result** (`/attribution`,
the final case file), and **System/Node Status** (`/system`, consensus
node health + ledger log).

## Project layout

```
src/
  components/       shared UI: stepper, step log, canvas viewer, chips, etc.
  components/layout sidebar + console shell
  context/          AstraeaContext — acting officer, active viewer session,
                     investigation result
  pages/            the seven required screens
  services/
    cryptoSim.js     display-safe SHA-256 fingerprints standing in for
                     AES-256-GCM / ML-KEM / ML-DSA references — never
                     generates or exposes real secret key material
    watermark.js     canvas rendering + a simplified LSB watermark
                     embed/extract standing in for the real DWT-domain mark
    astraeaLedger.js the mock append-only ledger, consensus nodes, and
                     document/lockbox store (persisted to localStorage)
  styles/           design tokens + shared ops-console visual language
  tests/            vitest unit tests for the simulation services
```

## Important simplifications (read before wiring to a real backend)

This is a **frontend demo**, and the services above are intentionally
simplified so the UI has something real to react to without a backend:

- `cryptoSim.js` never performs real AES/ML-KEM/ML-DSA operations. It
  hashes public strings (document ids, officer ids, timestamps) with
  `crypto.subtle.digest` to produce realistic-looking, display-safe
  reference numbers. **No secret key material is ever generated, stored,
  or displayed.**
- `watermark.js` embeds W_ID in the least-significant bits of the
  rendered canvas rather than in the wavelet (DWT) domain. This is
  sufficient to demo the full pipeline (embed → export → re-upload →
  recover → look up on the ledger) but will **not** survive an actual
  camera photograph the way a real DWT watermark is designed to. The
  Secure Viewer's copy is careful to say this correctly — it does not
  claim camera-robustness for this simulated mark.
- The "ledger" and "consensus nodes" are a `localStorage`-backed mock,
  not a real distributed ledger. Swap `astraeaLedger.js`'s internals for
  real API calls to wire this UI to the actual ASTRAEA backend; the
  page components only depend on the exported function signatures.

When integrating with the real backend, replace the bodies of
`services/*.js` and keep the same exported function names — no page or
component should need to change.

## 3-minute demo script

1. **Dashboard** — orient the judge with the seven-stage chain.
2. **Distribution** — send `OP ORDER — ALPHA` to Officer K. Rao.
3. **Recipient Terminal** — act as Officer K. Rao, request decryption,
   narrate the ledger commit as it happens ("nothing decrypts before
   this step completes").
4. **Secure Viewer** — show the normal-looking document, click
   "Simulate photograph" to download a capture.
5. **Investigator Portal** — drag in the downloaded capture, narrate the
   recovery pipeline down to ML-DSA verification.
6. **Attribution Result** — show the officer UID, session, and the two
   distinct badges: *watermark extracted* vs. *cryptographically
   attributed*.
