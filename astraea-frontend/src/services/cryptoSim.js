// ASTRAEA demo — cryptographic simulation layer.
//
// This module never generates, stores, or displays real secret key material.
// It produces short, display-safe SHA-256 fingerprints of PUBLIC strings
// (document ids, officer uids, timestamps) purely so the UI has realistic
// looking reference numbers to render. It is a UI simulation, not a
// cryptographic implementation, and must not be treated as one.

async function sha256Hex(input) {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function fingerprint(input, length = 16) {
  const hex = await sha256Hex(String(input));
  return hex.slice(0, length);
}

export function newDocumentId() {
  return `DOC-${Date.now().toString(36).toUpperCase()}-${Math.floor(Math.random() * 9000 + 1000)}`;
}

export function newSessionId() {
  return `SES-${Date.now().toString(36).toUpperCase()}-${Math.floor(Math.random() * 900 + 100)}`;
}

// Represents "a recipient lockbox was created" without ever exposing the
// wrapped content key. Only a fingerprint of the (docId, recipientUid) pair
// is produced, standing in for the ML-KEM ciphertext reference.
export async function createLockboxReference(docId, recipientUid) {
  const ref = await fingerprint(`${docId}:${recipientUid}:lockbox`, 20);
  return { recipientUid, lockboxRef: ref.toUpperCase() };
}

// Represents "the content was sealed under AES-256-GCM" — again, only a
// display fingerprint of the ciphertext, never the key.
export async function ciphertextFingerprint(docId) {
  const fp = await fingerprint(`${docId}:ciphertext:${Math.random()}`, 24);
  return fp.toUpperCase();
}

// Simulated ML-DSA signature over a receipt. Produces a fingerprint that
// stands in for a signature value — sized similarly to a truncated
// signature reference, never a real private-key operation.
export async function signReceipt(receipt) {
  const material = JSON.stringify(receipt);
  const sig = await fingerprint(`mldsa:${material}`, 32);
  return sig.toUpperCase();
}

export async function verifySignature(receipt, signature) {
  // In this simulation, verification recomputes the same fingerprint.
  // A real deployment would perform an actual ML-DSA public-key verify.
  const expected = await signReceipt(receipt);
  return expected === signature;
}

export const PRIMITIVES = {
  symmetric: 'AES-256-GCM',
  kem: 'ML-KEM-1024',
  signature: 'ML-DSA-87',
};
