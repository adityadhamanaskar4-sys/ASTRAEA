import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listPendingForOfficer, requestDecryption } from '../services/astraeaLedger';
import { useAstraea } from '../context/AstraeaContext';
import StepLog from '../components/StepLog';

const STEPS = [
  { key: 'requested', label: 'Decryption Requested' },
  { key: 'receipt', label: 'Creating Receipt' },
  { key: 'signing', label: 'Signing with ML-DSA' },
  { key: 'submitting', label: 'Submitting to Ledger' },
  { key: 'consensus', label: 'Awaiting Consensus' },
  { key: 'committed', label: 'Ledger Committed' },
  { key: 'token', label: 'Decryption Token Released' },
  { key: 'decrypting', label: 'Decrypting' },
  { key: 'watermarking', label: 'Generating Forensic Watermark' },
  { key: 'ready', label: 'Secure Viewer Ready' },
];

export default function RecipientTerminal() {
  const { officers, actingOfficerUid, setActingOfficerUid, setActiveSession, refreshTick } = useAstraea();
  const navigate = useNavigate();

  const pending = listPendingForOfficer(actingOfficerUid);
  const [selectedDocId, setSelectedDocId] = useState(pending[0]?.doc.docId || '');
  const [statuses, setStatuses] = useState({});
  const [times, setTimes] = useState({});
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [sealStamped, setSealStamped] = useState(false);

  const currentPending = listPendingForOfficer(actingOfficerUid);
  const effectiveDocId = currentPending.find((p) => p.doc.docId === selectedDocId)
    ? selectedDocId
    : currentPending[0]?.doc.docId || '';

  const handleRequest = async () => {
    if (!effectiveDocId) return;
    setRunning(true);
    setDone(false);
    setSealStamped(false);
    setStatuses({});
    setTimes({});

    const res = await requestDecryption({
      docId: effectiveDocId,
      officerUid: actingOfficerUid,
      onStep: (key, status) => {
        setStatuses((prev) => ({ ...prev, [key]: status }));
        setTimes((prev) => ({ ...prev, [key]: Date.now() }));
        if (key === 'committed' && status === 'complete') setSealStamped(true);
      },
    });

    setActiveSession({
      doc: res.doc,
      wId: res.wId,
      ledgerRecord: res.ledgerRecord,
      watermarkedImageBase64: res.watermarkedImageBase64,
      decryptedContent: res.decryptedContent,
    });
    setRunning(false);
    setDone(true);
  };

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow mono">STAGE 02 — AUTHORIZATION / DECRYPTION</div>
        <h1 className="page-title">Recipient Terminal</h1>
        <p className="page-desc">
          The document does not appear before the ledger commits. Every step below happens with
          no plaintext in play until the commit step completes.
        </p>
      </div>

      <div className="panel">
        <div className="panel-title">Acting as</div>
        <select
          className="select"
          value={actingOfficerUid}
          onChange={(e) => {
            setActingOfficerUid(e.target.value);
            setDone(false);
            setStatuses({});
          }}
        >
          {officers.map((o) => (
            <option key={o.uid} value={o.uid}>{o.name} — {o.uid}</option>
          ))}
        </select>
      </div>

      <div className="panel">
        <div className="panel-title">Pending lockboxes</div>
        {currentPending.length === 0 && (
          <p className="muted small">
            No documents waiting for this officer. Distribute one from the Distribution page first.
          </p>
        )}
        {currentPending.length > 0 && (
          <>
            <select
              className="select"
              value={effectiveDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              style={{ marginBottom: 16 }}
              disabled={running}
            >
              {currentPending.map(({ doc }) => (
                <option key={doc.docId} value={doc.docId}>{doc.title} — {doc.docId}</option>
              ))}
            </select>
            <button className="btn btn-primary" onClick={handleRequest} disabled={running}>
              {running ? 'Processing…' : 'Request Decryption'}
            </button>
          </>
        )}
      </div>

      {(running || done) && (
        <div className="panel panel-accent">
          <div className="panel-title">Access request</div>
          <StepLog steps={STEPS} statuses={statuses} times={times} />
          {sealStamped && (
            <div className="seal-wrap">
              <div className={`seal${sealStamped ? ' stamped' : ''}`}>LEDGER<br />COMMITTED</div>
            </div>
          )}
          {done && (
            <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => navigate('/viewer')}>
              Open Secure Viewer
            </button>
          )}
        </div>
      )}
    </div>
  );
}
