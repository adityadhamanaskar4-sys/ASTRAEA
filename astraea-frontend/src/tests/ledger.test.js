import { describe, it, expect, beforeEach } from 'vitest';
import { getOfficers, getSampleDocuments, getNodes, listDocuments, listPendingForOfficer } from '../services/astraeaLedger';

beforeEach(() => {
  localStorage.clear();
});

describe('astraeaLedger static data', () => {
  it('exposes a fixed roster of officers with uid + name', () => {
    const officers = getOfficers();
    expect(officers.length).toBeGreaterThan(0);
    for (const o of officers) {
      expect(o).toHaveProperty('uid');
      expect(o).toHaveProperty('name');
    }
  });

  it('exposes sample documents with a classification', () => {
    const docs = getSampleDocuments();
    expect(docs.length).toBeGreaterThan(0);
    for (const d of docs) {
      expect(d).toHaveProperty('title');
      expect(d).toHaveProperty('classification');
    }
  });

  it('starts with five online consensus nodes at height 0', () => {
    const nodes = getNodes();
    expect(nodes).toHaveLength(5);
    for (const n of nodes) {
      expect(n.status).toBe('online');
      expect(n.height).toBe(0);
    }
  });

  it('starts with no distributed documents and nothing pending', () => {
    expect(listDocuments()).toEqual([]);
    expect(listPendingForOfficer(getOfficers()[0].uid)).toEqual([]);
  });
});
