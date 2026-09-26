import { createLockboxReference, ciphertextFingerprint, newDocumentId, newSessionId, signReceipt, verifySignature, fingerprint } from './cryptoSim';

const API_BASE_URL = 'http://localhost:8000';
const STORAGE_KEY = 'astraea_state_v1';

const NODE_NAMES = ['NODE-ALPHA', 'NODE-BRAVO', 'NODE-CHARLIE', 'NODE-DELTA', 'NODE-ECHO'];

const OFFICERS = [
  { uid: 'OFC-2291', name: 'Officer K. Rao' },
  { uid: 'OFC-1187', name: 'Officer A. Verma' },
  { uid: 'OFC-3305', name: 'Officer S. Nair' },
];

const SAMPLE_DOCS = [
  {
    title: 'OP ORDER — ALPHA',
    classification: 'RESTRICTED',
    body: 'Section 4.2 — Movement Schedule\nSector clearance pending final\nauthorization from command.',
  },
  {
    title: 'SATCOM FREQUENCY TABLE',
    classification: 'CONFIDENTIAL',
    body: 'Channel allocation — Q3 rotation\nPrimary / secondary uplink pairs\nlisted by sector code.',
  },
  {
    title: 'RECON BRIEF — 07',
    classification: 'RESTRICTED',
    body: 'Terrain assessment summary\nAttached imagery references\nlogged under separate manifest.',
  },
];

function defaultState() {
  return {
    documents: {},
    ledger: [],
    nodes: NODE_NAMES.map((name) => ({ name, status: 'online', height: 0 })),
  };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultState();
    const parsed = JSON.parse(raw);
    return { ...defaultState(), ...parsed };
  } catch {
    return defaultState();
  }
}

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function getOfficers() {
  return OFFICERS;
}

export function getSampleDocuments() {
  return SAMPLE_DOCS;
}

export function getNodes() {
  return loadState().nodes;
}

export function listDocuments() {
  const state = loadState();
  return Object.values(state.documents).sort((a, b) => b.createdAt - a.createdAt);
}

export function listLedger() {
  return loadState().ledger.slice().sort((a, b) => b.timestamp - a.timestamp);
}

export function listPendingForOfficer(officerUid) {
  const docs = listDocuments();
  return docs
    .map((doc) => ({ doc, lockbox: doc.recipients.find((r) => r.uid === officerUid) }))
    .filter((entry) => entry.lockbox && entry.lockbox.status !== 'decrypted');
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// ---- Sender flow ----
export async function distributeDocument({ title, classification, body, recipientUids, onStatus }) {
  // Call Backend 1 API
  try {
    onStatus?.('Sealing content under AES-256-GCM & generating ML-KEM lockboxes via Backend 1 API…');
    const res = await fetch(`${API_BASE_URL}/broadcast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, classification, body, recipient_uids: recipientUids })
    });

    if (res.ok) {
      const apiDoc = await res.json();
      const state = loadState();
      const doc = {
        docId: apiDoc.doc_id,
        title: apiDoc.title,
        classification: apiDoc.classification,
        body: body,
        ciphertextFp: apiDoc.ciphertext_fp,
        createdAt: apiDoc.created_at || Date.now(),
        recipients: apiDoc.recipients.map(r => ({
          uid: r.uid,
          name: OFFICERS.find(o => o.uid === r.uid)?.name || r.name || r.uid,
          lockboxRef: r.lockbox_ref,
          status: r.status
        }))
      };
      state.documents[doc.docId] = doc;
      saveState(state);
      return doc;
    }
  } catch (err) {
    console.warn('Backend 1 API offline, using local client simulation mode:', err.message);
  }

  // Local fallback
  const state = loadState();
  const docId = newDocumentId();

  onStatus?.('Sealing content under AES-256-GCM…');
  await wait(500);
  const ciphertextFp = await ciphertextFingerprint(docId);

  onStatus?.('Wrapping content key for each recipient (ML-KEM)…');
  await wait(500);
  const recipients = [];
  for (const uid of recipientUids) {
    const officer = OFFICERS.find((o) => o.uid === uid);
    const { lockboxRef } = await createLockboxReference(docId, uid);
    recipients.push({ uid, name: officer?.name || uid, lockboxRef, status: 'delivered' });
  }

  const doc = {
    docId,
    title,
    classification,
    body,
    ciphertextFp,
    createdAt: Date.now(),
    recipients,
  };

  state.documents[docId] = doc;
  saveState(state);
  return doc;
}

// ---- Recipient flow ----
export async function requestDecryption({ docId, officerUid, onStep }) {
  const state = loadState();
  const doc = state.documents[docId];
  if (!doc) throw new Error('Unknown document');
  const lockbox = doc.recipients.find((r) => r.uid === officerUid);
  if (!lockbox) throw new Error('No lockbox for this officer');

  const officer = OFFICERS.find((o) => o.uid === officerUid);
  const sessionId = newSessionId();
  const timestamp = String(Math.floor(Date.now() / 1000));

  onStep?.('requested', 'active');
  await wait(400);
  onStep?.('requested', 'complete');

  onStep?.('receipt', 'active');
  const receipt = {
    docId,
    officerUid,
    officerName: officer?.name,
    lockboxRef: lockbox.lockboxRef,
    sessionId,
    requestedAt: Date.now(),
  };
  await wait(400);
  onStep?.('receipt', 'complete');

  onStep?.('signing', 'active');
  const signature = await signReceipt(receipt);
  await wait(500);
  onStep?.('signing', 'complete');

  // Call Backend 1 API
  try {
    onStep?.('submitting', 'active');
    const res = await fetch(`${API_BASE_URL}/request_decryption`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        uid: officerUid,
        doc_id: docId,
        timestamp: timestamp,
        signature: signature
      })
    });

    if (res.ok) {
      onStep?.('submitting', 'complete');
      onStep?.('consensus', 'active');
      await wait(600);
      onStep?.('consensus', 'complete');

      onStep?.('committed', 'active');
      const apiRes = await res.json();
      const wId = apiRes.w_id;

      const ledgerRecord = {
        ledgerId: apiRes.ledger_record?.ledgerId || `LR-${state.ledger.length + 1}`,
        docId,
        officerUid,
        officerName: officer?.name,
        sessionId,
        receipt: apiRes.ledger_record?.receipt || `${officerUid} || ${docId} || ${timestamp}`,
        signature: apiRes.ledger_record?.signature || signature,
        wId: wId,
        consensusNodes: apiRes.ledger_record?.consensusNodes || state.nodes.map((n) => n.name),
        timestamp: Date.now(),
        status: 'committed',
      };

      state.ledger.push(ledgerRecord);
      state.nodes = state.nodes.map((n) => ({ ...n, height: n.height + 1 }));
      const idx = doc.recipients.findIndex((r) => r.uid === officerUid);
      doc.recipients[idx] = { ...lockbox, status: 'decrypted' };
      saveState(state);
      await wait(300);
      onStep?.('committed', 'complete');

      onStep?.('token', 'active');
      await wait(400);
      onStep?.('token', 'complete');

      onStep?.('decrypting', 'active');
      await wait(400);
      onStep?.('decrypting', 'complete');

      onStep?.('watermarking', 'active');
      await wait(400);
      onStep?.('watermarking', 'complete');

      onStep?.('ready', 'active');
      await wait(200);
      onStep?.('ready', 'complete');

      return { ledgerRecord, wId, doc, lockbox, watermarkedImageBase64: apiRes.watermarked_image_base64 };
    }
  } catch (err) {
    console.warn('Backend 1 API offline, using local client simulation mode:', err.message);
  }

  // Local fallback simulation
  onStep?.('submitting', 'active');
  await wait(500);
  onStep?.('submitting', 'complete');

  onStep?.('consensus', 'active');
  await wait(700);
  onStep?.('consensus', 'complete');

  onStep?.('committed', 'active');
  const wId = (await fingerprint(`${docId}:${officerUid}:${sessionId}`, 24)).toUpperCase();
  const ledgerRecord = {
    ledgerId: `LR-${state.ledger.length + 1}`,
    docId,
    officerUid,
    officerName: officer?.name,
    sessionId,
    receipt,
    signature,
    wId,
    consensusNodes: state.nodes.map((n) => n.name),
    timestamp: Date.now(),
    status: 'committed',
  };
  state.ledger.push(ledgerRecord);
  state.nodes = state.nodes.map((n) => ({ ...n, height: n.height + 1 }));
  const idx = doc.recipients.findIndex((r) => r.uid === officerUid);
  doc.recipients[idx] = { ...lockbox, status: 'decrypted' };
  saveState(state);
  await wait(400);
  onStep?.('committed', 'complete');

  onStep?.('token', 'active');
  await wait(400);
  onStep?.('token', 'complete');

  onStep?.('decrypting', 'active');
  await wait(500);
  onStep?.('decrypting', 'complete');

  onStep?.('watermarking', 'active');
  await wait(400);
  onStep?.('watermarking', 'complete');

  onStep?.('ready', 'active');
  await wait(200);
  onStep?.('ready', 'complete');

  return { ledgerRecord, wId, doc, lockbox };
}

// ---- Investigator flow ----
export async function auditWidWithBackend(wId) {
  try {
    const res = await fetch(`${API_BASE_URL}/audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ w_id: wId })
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn('Backend audit API offline:', err.message);
  }
  return null;
}

export function findLedgerRecordByWid(wId) {
  const state = loadState();
  return state.ledger.find((r) => r.wId === wId || (r.wId && r.wId.toLowerCase() === wId.toLowerCase())) || null;
}

export async function verifyLedgerRecord(record) {
  if (!record) return false;
  return verifySignature(record.receipt, record.signature);
}

export function seedDemoData() {
  const state = loadState();
  if (Object.keys(state.documents).length > 0) return;
}
