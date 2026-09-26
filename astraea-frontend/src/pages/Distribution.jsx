import { useState } from 'react';
import { getOfficers, getSampleDocuments, distributeDocument, listDocuments } from '../services/astraeaLedger';
import PrimitiveBadges from '../components/PrimitiveBadges';
import DataField from '../components/DataField';
import StatusChip from '../components/StatusChip';
import { useAstraea } from '../context/AstraeaContext';

export default function Distribution() {
  const officers = getOfficers();
  const sampleDocs = getSampleDocuments();
  const { bumpRefresh } = useAstraea();

  const [docIndex, setDocIndex] = useState(0);
  const [selectedUids, setSelectedUids] = useState([officers[0].uid]);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  const toggleOfficer = (uid) => {
    setSelectedUids((prev) => (prev.includes(uid) ? prev.filter((u) => u !== uid) : [...prev, uid]));
  };

  const handleSend = async () => {
    if (selectedUids.length === 0) return;
    setBusy(true);
    setResult(null);
    const chosen = sampleDocs[docIndex];
    const doc = await distributeDocument({
      title: chosen.title,
      classification: chosen.classification,
      body: chosen.body,
      recipientUids: selectedUids,
      onStatus: setStatus,
    });
    setStatus('');
    setResult(doc);
    setBusy(false);
    bumpRefresh();
  };

  const history = listDocuments();

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow mono">STAGE 01 — AUTHENTICATION / PROVENANCE</div>
        <h1 className="page-title">Distribution</h1>
        <p className="page-desc">
          Select a document and its recipients. ASTRAEA seals the content once and wraps a copy of
          the content key into a lockbox for each recipient — nobody but that recipient can open
          theirs.
        </p>
      </div>

      <div className="panel">
        <div className="panel-title">Send a document</div>

        <label className="field-label" htmlFor="doc-select">Document</label>
        <select
          id="doc-select"
          className="select"
          value={docIndex}
          onChange={(e) => setDocIndex(Number(e.target.value))}
          style={{ marginBottom: 16 }}
        >
          {sampleDocs.map((d, i) => (
            <option key={d.title} value={i}>{d.title} — {d.classification}</option>
          ))}
        </select>

        <span className="field-label">Recipients</span>
        <div className="stack" style={{ marginBottom: 16 }}>
          {officers.map((o) => (
            <label className="checkbox-row" key={o.uid}>
              <input
                type="checkbox"
                checked={selectedUids.includes(o.uid)}
                onChange={() => toggleOfficer(o.uid)}
              />
              {o.name}
              <span className="mono muted small">{o.uid}</span>
            </label>
          ))}
        </div>

        <span className="field-label">Cryptographic primitives in use</span>
        <div style={{ marginBottom: 16 }}>
          <PrimitiveBadges />
        </div>

        <button className="btn btn-primary" onClick={handleSend} disabled={busy || selectedUids.length === 0}>
          {busy ? (status || 'Sealing…') : 'Initiate encryption & distribute'}
        </button>
      </div>

      {result && (
        <div className="panel panel-accent">
          <div className="panel-title">Distribution complete</div>
          <DataField label="Document ID" value={result.docId} />
          <DataField label="Ciphertext fingerprint" value={result.ciphertextFp} />
          <div style={{ marginTop: 12 }}>
            <span className="field-label">Recipient lockboxes</span>
            <div className="stack">
              {result.recipients.map((r) => (
                <div className="spread" key={r.uid}>
                  <span className="small">{r.name} <span className="mono muted">{r.uid}</span></span>
                  <StatusChip variant="complete">Lockbox delivered</StatusChip>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-title">Distribution log</div>
        {history.length === 0 && <p className="muted small">Nothing distributed yet.</p>}
        <div className="stack">
          {history.map((d) => (
            <div className="data-field" key={d.docId}>
              <span className="data-field-label">{d.title} <span className="mono muted">{d.docId}</span></span>
              <span className="data-field-value" style={{ fontFamily: 'var(--font-ui)' }}>
                {d.recipients.filter((r) => r.status === 'decrypted').length}/{d.recipients.length} opened
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
