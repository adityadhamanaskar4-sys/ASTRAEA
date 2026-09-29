import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DropZone from '../components/DropZone';
import StepLog from '../components/StepLog';
import { extractWatermark } from '../services/watermark';
import {
  findLedgerRecordByWid,
  verifyLedgerRecord,
  auditWidWithBackend,
  auditUploadedImageWithBackend,
  getOfficers
} from '../services/astraeaLedger';
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
    await wait(350);
    setStep('received', 'complete');

    setStep('correction', 'active');
    await wait(450);
    setStep('correction', 'complete');

    setStep('extraction', 'active');

    let backendAudit = null;
    let wId = null;

    // 1. Primary: Send leaked photograph to Backend DWT + OpenCV forensics engine
    try {
      backendAudit = await auditUploadedImageWithBackend(file);
      if (backendAudit && backendAudit.extracted_wid) {
        wId = backendAudit.extracted_wid;
      }
    } catch (err) {
      console.warn('Backend image forensics audit offline, trying local client extract:', err);
    }

    // 2. Fallback: Local client-side canvas extraction if backend did not extract
    if (!wId) {
      try {
        const imageData = await loadImageData(file);
        wId = extractWatermark(imageData);
      } catch (err) {
        console.warn('Local canvas watermark extract failed:', err);
      }
    }

    await wait(400);

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
    await wait(450);

    let record = null;
    let valid = false;

    // If backend audit succeeded, build full attribution record
    if (backendAudit && (backendAudit.attribution_status === 'FOUND' || backendAudit.attribution_status === 'FOUND_BUT_INVALID')) {
      const officersList = getOfficers();
      const officerUid = backendAudit.parsed_receipt?.uid;
      const officer = officersList.find((o) => o.uid === officerUid);

      record = {
        ledgerId: `LR-${backendAudit.block_id || 1}`,
        docId: backendAudit.parsed_receipt?.doc_id || 'DOC-CLASSIFIED',
        officerUid: officerUid,
        officerName: officer?.name || (officerUid ? `Officer ${officerUid}` : 'Unknown Officer'),
        sessionId: 'SES-DLT-AUDIT',
        receipt: backendAudit.client_receipt,
        signature: backendAudit.client_signature,
        wId: backendAudit.extracted_wid,
        y_current: backendAudit.y_current,
        timestamp: backendAudit.parsed_receipt?.timestamp ? Number(backendAudit.parsed_receipt.timestamp) * 1000 : Date.now(),
        status: 'committed'
      };
      valid = Boolean(backendAudit.signature_verified);
    }

    // If backend did not find in ledger yet, try querying with extracted wId directly
    if (!record && wId) {
      try {
        const auditRes = await auditWidWithBackend(wId);
        if (auditRes && (auditRes.attribution_status === 'FOUND' || auditRes.attribution_status === 'FOUND_BUT_INVALID')) {
          const officersList = getOfficers();
          const officerUid = auditRes.parsed_receipt?.uid;
          const officer = officersList.find((o) => o.uid === officerUid);

          record = {
            ledgerId: `LR-${auditRes.block_id || 1}`,
            docId: auditRes.parsed_receipt?.doc_id || 'DOC-CLASSIFIED',
            officerUid: officerUid,
            officerName: officer?.name || (officerUid ? `Officer ${officerUid}` : 'Unknown Officer'),
            sessionId: 'SES-DLT-AUDIT',
            receipt: auditRes.client_receipt,
            signature: auditRes.client_signature,
            wId: auditRes.extracted_wid,
            y_current: auditRes.y_current,
            timestamp: auditRes.parsed_receipt?.timestamp ? Number(auditRes.parsed_receipt.timestamp) * 1000 : Date.now(),
            status: 'committed'
          };
          valid = Boolean(auditRes.signature_verified);
        }
      } catch (err) {
        console.warn('Backend audit W_ID query failed:', err);
      }
    }

    // Final fallback to local localStorage ledger
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
    await wait(400);
    setStep('receipt', 'complete');

    setStep('verify', 'active');
    if (!valid) {
      valid = await verifyLedgerRecord(record);
    }
    await wait(500);
    setStep('verify', valid ? 'complete' : 'error');

    if (!valid) {
      setOutcome({ level: 'extracted-only', wId, record });
      setRunning(false);
      return;
    }

    setStep('attribution', 'active');
    await wait(350);
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
