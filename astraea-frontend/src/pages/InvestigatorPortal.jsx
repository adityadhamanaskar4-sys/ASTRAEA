import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DropZone from '../components/DropZone';
import StepLog from '../components/StepLog';
import { extractWatermark } from '../services/watermark';
import { findLedgerRecordByWid, verifyLedgerRecord, auditWidWithBackend, getOfficers } from '../services/astraeaLedger';
import { useAstraea } from '../context/AstraeaContext';

const STEPS = [
  { key: 'received', label: 'Photo Received' },
  { key: 'correction', label: 'Perspective Correction' },
  { key: 'extraction', label: 'DWT Extraction' },
  { key: 'wid', label: 'W_ID Recovered' },
  { key: 'query', label: 'Querying ASTRAEA Ledger' },
  { key: 'receipt', label: 'Retrieving Signed Receipt' },
  { key: 'verify', label: 'Verifying ML-DSA' },
  { key: 'attribution', label: 'Attribution Complete' },
];

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function loadImageData(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      resolve(ctx.getImageData(0, 0, canvas.width, canvas.height));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

export default function InvestigatorPortal() {
  const { setInvestigation } = useAstraea();
  const navigate = useNavigate();

  const [statuses, setStatuses] = useState({});
  const [running, setRunning] = useState(false);
  const [outcome, setOutcome] = useState(null); // { level: 'none' | 'extracted-only' | 'attributed', ... }

  const setStep = (key, status) => setStatuses((prev) => ({ ...prev, [key]: status }));

  const runPipeline = async (file) => {
    setRunning(true);
    setOutcome(null);
    setStatuses({});

    setStep('received', 'active');
    await wait(400);
    setStep('received', 'complete');

    setStep('correction', 'active');
    await wait(500);
    setStep('correction', 'complete');

    setStep('extraction', 'active');
    const imageData = await loadImageData(file);
    const wId = extractWatermark(imageData);
    await wait(600);

    if (!wId) {
      setStep('extraction', 'error');
      setOutcome({ level: 'none' });
      setRunning(false);
      return;
    }
    setStep('extraction', 'complete');

    setStep('wid', 'active');
    await wait(400);
    setStep('wid', 'complete');

    setStep('query', 'active');
    await wait(500);

    let record = null;
    let valid = false;

    // 1. Query DLT Ledger in Backend SQLite
    try {
      const backendAudit = await auditWidWithBackend(wId);
      if (backendAudit && backendAudit.attribution_status === 'FOUND') {
        const officersList = getOfficers();
        const officerUid = backendAudit.parsed_receipt?.uid;
        const officer = officersList.find((o) => o.uid === officerUid);

        record = {
          ledgerId: `LR-${backendAudit.block_id || 1}`,
          docId: backendAudit.parsed_receipt?.doc_id || 'DOC-CLASSIFIED',
          officerUid: officerUid,
          officerName: officer?.name || officerUid,
          sessionId: 'SES-DLT-AUDIT',
          receipt: backendAudit.client_receipt,
          signature: backendAudit.client_signature,
          wId: backendAudit.extracted_wid,
          y_current: backendAudit.y_current,
          timestamp: backendAudit.parsed_receipt?.timestamp ? Number(backendAudit.parsed_receipt.timestamp) * 1000 : Date.now(),
          status: 'committed'
        };
        valid = backendAudit.signature_verified;
      }
    } catch (auditErr) {
      console.warn('Backend forensic audit call failed, using local ledger records:', auditErr);
    }

    // 2. Fall back to local ledger search if offline
    if (!record) {
      record = findLedgerRecordByWid(wId);
    }
    setStep('query', 'complete');

    if (!record) {
      setStep('receipt', 'error');
      setOutcome({ level: 'extracted-only', wId });
      setRunning(false);
      return;
    }

    setStep('receipt', 'active');
    await wait(500);
    setStep('receipt', 'complete');

    setStep('verify', 'active');
    if (!valid) {
      valid = await verifyLedgerRecord(record);
    }
    await wait(600);
    setStep('verify', valid ? 'complete' : 'error');

    if (!valid) {
      setOutcome({ level: 'extracted-only', wId, record });
      setRunning(false);
      return;
    }

    setStep('attribution', 'active');
    await wait(400);
    setStep('attribution', 'complete');

    const investigation = { wId, record, verified: true };
    setInvestigation(investigation);
    setOutcome({ level: 'attributed', wId, record });
    setRunning(false);
  };

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow mono">STAGE 04 — FORENSICS / ATTRIBUTION</div>
        <h1 className="page-title">Investigator Portal</h1>
        <p className="page-desc">
          Upload a suspected leak. Recovering a mark from the image is only half the story — it
          only becomes attribution once it is matched to a committed ledger record with a valid
          signature.
        </p>
      </div>

      <div className="panel">
        <div className="panel-title">Upload suspected leak</div>
        <DropZone onFile={runPipeline} />
      </div>

      {(running || outcome) && (
        <div className="panel panel-accent">
          <div className="panel-title">Recovery pipeline</div>
          <StepLog steps={STEPS} statuses={statuses} times={{}} />

          {outcome?.level === 'none' && (
            <p className="small" style={{ color: 'var(--red)', marginTop: 12 }}>
              No forensic mark could be recovered from this image. This looks like it was not
              sourced from an ASTRAEA secure session — or the mark did not survive this file.
            </p>
          )}

          {outcome?.level === 'extracted-only' && (
            <p className="small" style={{ color: 'var(--amber)', marginTop: 12 }}>
              A mark was extracted, but it does not resolve to a valid, committed ledger record.
              <strong> Extraction alone is not attribution</strong> — this leak cannot be pinned on
              anyone from this evidence.
            </p>
          )}

          {outcome?.level === 'attributed' && (
            <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => navigate('/attribution')}>
              View attribution result
            </button>
          )}
        </div>
      )}
    </div>
  );
}
