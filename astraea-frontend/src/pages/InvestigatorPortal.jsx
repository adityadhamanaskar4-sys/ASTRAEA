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
  getOfficers,
  listDocuments
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
  const [docIdFilter, setDocIdFilter] = useState('');

  const availableDocs = listDocuments();

  const setStep = (key, status) => setStatuses((prev) => ({ ...prev, [key]: status }));

  const runPipeline = async (file) => {
    setRunning(true);
    setOutcome(null);
    setStatuses({});

    const effectiveDocId = docIdFilter.trim() || null;

    setStep('received', 'active');
    await wait(350);
    setStep('received', 'complete');

    setStep('correction', 'active');
    await wait(450);
    setStep('correction', 'complete');

    setStep('extraction', 'active');

    let backendAudit = null;
    let wId = null;

    // 1. Primary: Send leaked photograph to Backend DWT + OpenCV forensics engine (scoped by doc_id if provided)
    try {
      backendAudit = await auditUploadedImageWithBackend(file, effectiveDocId);
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
      setOutcome({ level: 'none', searchedDocId: effectiveDocId });
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
    let candidates = (backendAudit && backendAudit.candidates) || [];

    // If backend audit succeeded (either exact FOUND or PARTIAL_MATCH)
    if (backendAudit && (backendAudit.attribution_status === 'FOUND' || backendAudit.attribution_status === 'PARTIAL_MATCH' || backendAudit.attribution_status === 'FOUND_BUT_INVALID')) {
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
        status: 'committed',
        similarityPercentage: candidates[0]?.similarity_percentage || 100.0,
        matchType: candidates[0]?.match_type || 'EXACT_MATCH'
      };
      valid = Boolean(backendAudit.signature_verified);
    }

    // If backend did not find in ledger yet, try querying with extracted wId directly
    if (!record && wId) {
      try {
        const auditRes = await auditWidWithBackend(wId, effectiveDocId);
        if (auditRes && (auditRes.attribution_status === 'FOUND' || auditRes.attribution_status === 'PARTIAL_MATCH' || auditRes.attribution_status === 'FOUND_BUT_INVALID')) {
          const officersList = getOfficers();
          const officerUid = auditRes.parsed_receipt?.uid;
          const officer = officersList.find((o) => o.uid === officerUid);
          if (auditRes.candidates) candidates = auditRes.candidates;

          record = {
            ledgerId: `LR-${auditRes.block_id || 1}`,
            docId: auditRes.parsed_receipt?.doc_id || effectiveDocId || 'DOC-CLASSIFIED',
            officerUid: officerUid,
            officerName: officer?.name || (officerUid ? `Officer ${officerUid}` : 'Unknown Officer'),
            sessionId: 'SES-DLT-AUDIT',
            receipt: auditRes.client_receipt,
            signature: auditRes.client_signature,
            wId: auditRes.extracted_wid,
            y_current: auditRes.y_current,
            timestamp: auditRes.parsed_receipt?.timestamp ? Number(auditRes.parsed_receipt.timestamp) * 1000 : Date.now(),
            status: 'committed',
            similarityPercentage: candidates[0]?.similarity_percentage || 100.0,
            matchType: candidates[0]?.match_type || 'EXACT_MATCH'
          };
          valid = Boolean(auditRes.signature_verified);
        }
      } catch (err) {
        console.warn('Backend audit W_ID query failed:', err);
      }
    }

    // Final fallback to local localStorage ledger
    if (!record) {
      record = findLedgerRecordByWid(wId, effectiveDocId);
    }
    setStep('query', 'complete');

    if (!record) {
      setStep('receipt', 'error');
      setOutcome({ level: 'extracted-only', wId, candidates, searchedDocId: effectiveDocId });
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
      setOutcome({ level: 'extracted-only', wId, record, candidates, searchedDocId: effectiveDocId });
      setRunning(false);
      return;
    }

    setStep('attribution', 'active');
    await wait(350);
    setStep('attribution', 'complete');

    const isPartial = backendAudit?.attribution_status === 'PARTIAL_MATCH';
    const investigation = { wId, record, candidates, verified: true, isPartial, searchedDocId: effectiveDocId };
    setInvestigation(investigation);
    setOutcome({
      level: isPartial ? 'partial' : 'attributed',
      wId,
      record,
      candidates,
      searchedDocId: effectiveDocId
    });
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
          signature. Supports partial and corrupted watermark matching.
        </p>
      </div>

      <div className="panel">
        <div className="panel-title">1. Search Window Scope (Optional)</div>
        <p className="small muted" style={{ marginBottom: 12 }}>
          Optionally specify a Document ID to narrow the ledger search window and prioritize homography alignment for that specific document.
        </p>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: 10 }}>
          <div style={{ flex: '1 1 240px' }}>
            <input
              type="text"
              className="input mono"
              placeholder="e.g. DOC-E0544A41 (or leave blank for all)"
              value={docIdFilter}
              onChange={(e) => setDocIdFilter(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', fontSize: '13px' }}
            />
          </div>
          {availableDocs && availableDocs.length > 0 && (
            <div style={{ flex: '1 1 280px' }}>
              <select
                className="input"
                value={docIdFilter}
                onChange={(e) => setDocIdFilter(e.target.value)}
                style={{ width: '100%', padding: '8px 12px', fontSize: '13px' }}
              >
                <option value="">-- All Documents (Global Search) --</option>
                {availableDocs.map((d) => (
                  <option key={d.docId} value={d.docId}>
                    {d.docId} — {d.title} ({d.classification})
                  </option>
                ))}
              </select>
            </div>
          )}
          {docIdFilter && (
            <button
              type="button"
              className="btn btn-secondary small"
              onClick={() => setDocIdFilter('')}
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              Clear Filter
            </button>
          )}
        </div>
        <div className="small mono" style={{ color: docIdFilter ? 'var(--teal)' : 'var(--muted)' }}>
          {docIdFilter
            ? `• Scoped Window: Searching only ledger blocks associated with ${docIdFilter}`
            : '• Full Ledger Window: Traversing all historical document blocks (Global)'}
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">2. Upload suspected leak</div>
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
              A mark was extracted, but it does not resolve to a valid, committed ledger record
              {outcome.searchedDocId ? ` for Document ${outcome.searchedDocId}` : ''}.
              <strong> Extraction alone is not attribution</strong> — this leak cannot be pinned on
              anyone from this evidence.
              {outcome.searchedDocId && (
                <span style={{ display: 'block', marginTop: 6, color: 'var(--text-muted)' }}>
                  Tip: If the document ID was uncertain, clear the filter to search across all documents globally.
                </span>
              )}
            </p>
          )}

          {outcome?.level === 'partial' && (
            <p className="small" style={{ color: 'var(--amber)', marginTop: 12 }}>
              Partial watermark recovered ({outcome.record?.similarityPercentage}% similarity). Correlated against ledger records below.
            </p>
          )}

          {(outcome?.level === 'attributed' || outcome?.level === 'partial') && (
            <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => navigate('/attribution')}>
              View attribution case file
            </button>
          )}

          {outcome?.candidates && outcome.candidates.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div className="panel-title" style={{ fontSize: '14px', marginBottom: 8 }}>
                Potential Recipients Ranked by Watermark Similarity
              </div>
              <p className="small muted" style={{ marginBottom: 12 }}>
                The extracted mark was compared against all committed ledger states using bit-level Hamming distance.
              </p>
              <div className="stack">
                {outcome.candidates.map((cand, idx) => (
                  <div
                    key={cand.block_id + '-' + idx}
                    className="spread"
                    style={{
                      padding: '10px 14px',
                      borderRadius: '6px',
                      background: idx === 0 ? 'rgba(46, 204, 113, 0.08)' : 'rgba(255, 255, 255, 0.03)',
                      border: idx === 0 ? '1px solid rgba(46, 204, 113, 0.35)' : '1px solid rgba(255, 255, 255, 0.1)',
                      marginBottom: 8
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>
                        #{idx + 1} {cand.officer_name || `Officer ${cand.officer_uid}`}
                        <span className="mono muted small" style={{ marginLeft: 8 }}>{cand.officer_uid}</span>
                      </div>
                      <div className="small muted" style={{ marginTop: 4 }}>
                        Doc: <span className="mono">{cand.doc_id}</span> | Block #{cand.block_id} | {cand.matching_bits} bits ({cand.match_type})
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span
                        className="mono"
                        style={{
                          fontSize: '16px',
                          fontWeight: 700,
                          color: cand.similarity_percentage >= 90 ? 'var(--green, #2ecc71)' : (cand.similarity_percentage >= 60 ? 'var(--amber, #f39c12)' : 'var(--muted, #888)')
                        }}
                      >
                        {cand.similarity_percentage}%
                      </span>
                      <div className="small muted">similarity</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
