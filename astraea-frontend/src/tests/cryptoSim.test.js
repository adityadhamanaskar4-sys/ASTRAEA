// @vitest-environment node
import { describe, it, expect } from 'vitest';
import { fingerprint, newDocumentId, newSessionId, signReceipt, verifySignature } from '../services/cryptoSim';

describe('cryptoSim', () => {
  it('produces a deterministic fingerprint for the same input', async () => {
    const a = await fingerprint('DOC-1:OFC-1');
    const b = await fingerprint('DOC-1:OFC-1');
    expect(a).toBe(b);
    expect(a).toHaveLength(16);
  });

  it('produces different fingerprints for different input', async () => {
    const a = await fingerprint('DOC-1:OFC-1');
    const b = await fingerprint('DOC-1:OFC-2');
    expect(a).not.toBe(b);
  });

  it('generates document and session ids with the expected prefix', () => {
    expect(newDocumentId()).toMatch(/^DOC-/);
    expect(newSessionId()).toMatch(/^SES-/);
  });

  it('signs a receipt and verifies it against the same receipt only', async () => {
    const receipt = { docId: 'DOC-1', officerUid: 'OFC-1', sessionId: 'SES-1' };
    const signature = await signReceipt(receipt);
    expect(await verifySignature(receipt, signature)).toBe(true);

    const tampered = { ...receipt, officerUid: 'OFC-2' };
    expect(await verifySignature(tampered, signature)).toBe(false);
  });
});
