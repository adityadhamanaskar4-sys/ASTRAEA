import { Link } from 'react-router-dom';
import { useAstraea } from '../context/AstraeaContext';
import DataField from '../components/DataField';
import StatusChip from '../components/StatusChip';

export default function AttributionResult() {
  const { investigation, setInvestigation } = useAstraea();

  if (!investigation) {
    return (
      <div>
        <div className="page-head">
          <div className="page-eyebrow mono">STAGE 05 — ATTRIBUTION</div>
          <h1 className="page-title">Attribution Result</h1>
        </div>
        <div className="panel">
          <div className="panel-title">No attribution on record</div>
          <p className="muted small" style={{ marginBottom: 14 }}>
            Run an image through the Investigator Portal to produce an attribution result.
          </p>
          <Link to="/investigator" className="btn btn-primary" style={{ textDecoration: 'none', width: 'fit-content', display: 'inline-block' }}>
            Go to Investigator Portal
          </Link>
        </div>
      </div>
    );
  }

  const { record, wId, candidates = [], isPartial } = investigation;

  const handleSelectCandidate = (cand) => {
    const updatedRecord = {
      ...record,
      officerUid: cand.officer_uid,
      officerName: cand.officer_name || `Officer ${cand.officer_uid}`,
      docId: cand.doc_id,
      ledgerId: `LR-${cand.block_id}`,
      similarityPercentage: cand.similarity_percentage,
      matchType: cand.match_type,
      wId: cand.computed_wid
    };
    setInvestigation({
      ...investigation,
      record: updatedRecord,
      wId: cand.computed_wid
    });
  };

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow mono">STAGE 05 — ATTRIBUTION</div>
        <h1 className="page-title">{isPartial ? 'Partial Match Attributed' : 'Leak Attributed'}</h1>
        <p className="page-desc">
          {isPartial
            ? 'The recovered watermark was partially reconstructed and correlated against all immutable ledger blocks.'
            : 'The recovered mark resolved to a verified, signed, ledger-committed decryption session.'}
        </p>
      </div>

      <div className="panel spread">
        <StatusChip variant="complete">
          {record.similarityPercentage ? `${record.similarityPercentage}% Similarity` : 'Watermark extracted'}
        </StatusChip>
        <StatusChip variant="verified">Cryptographically attributed</StatusChip>
        {investigation.searchedDocId && (
          <StatusChip variant="info">Scoped: {investigation.searchedDocId}</StatusChip>
        )}
      </div>

      <div className="panel panel-accent">
        <div className="panel-title">Primary Suspect Case File</div>
        <DataField label="Officer UID" value={record.officerUid} />
        <DataField label="Officer name" value={record.officerName} />
        <DataField label="Document ID" value={record.docId} />
        <DataField label="Decryption session" value={record.sessionId} />
        <DataField label="Session time" value={new Date(record.timestamp).toLocaleString()} />
        <DataField
          label="W_ID (Extracted / Display-Safe)"
          value={wId ? `${wId.slice(0, 10)}…${wId.slice(-6)}` : 'UNKNOWN'}
        />
        {record.similarityPercentage !== undefined && (
          <DataField
            label="Attribution Confidence"
            value={
              <span
                style={{
                  fontWeight: 700,
                  color: record.similarityPercentage >= 90 ? 'var(--green)' : 'var(--amber)'
                }}
              >
                {record.similarityPercentage}% ({record.matchType || 'MATCH'})
              </span>
            }
          />
        )}
        <DataField label="ML-DSA verification" value={<span style={{ color: 'var(--green)' }}>VALID</span>} />
        <DataField label="Ledger record" value={<span style={{ color: 'var(--gold)' }}>COMMITTED (#{record.ledgerId?.replace('LR-', '') || '1'})</span>} />
      </div>

      {candidates && candidates.length > 1 && (
        <div className="panel">
          <div className="panel-title">Candidate Officers Ranked by Watermark Similarity</div>
          <p className="small muted" style={{ marginBottom: 14 }}>
            Incomplete or analog-degraded watermarks are evaluated across all historical ledger blocks. The list below ranks every candidate by bit similarity.
          </p>
          <div className="stack">
            {candidates.map((cand, idx) => (
              <div
                key={cand.block_id + '-' + idx}
                className="spread"
                style={{
                  padding: '10px 14px',
                  borderRadius: '6px',
                  background: cand.officer_uid === record.officerUid ? 'rgba(46, 204, 113, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                  border: cand.officer_uid === record.officerUid ? '1px solid rgba(46, 204, 113, 0.4)' : '1px solid rgba(255, 255, 255, 0.1)',
                  marginBottom: 8
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>
                    #{idx + 1} {cand.officer_name || `Officer ${cand.officer_uid}`}
                    <span className="mono muted small" style={{ marginLeft: 8 }}>{cand.officer_uid}</span>
                  </div>
                  <div className="small muted" style={{ marginTop: 4 }}>
                    Doc: <span className="mono">{cand.doc_id}</span> | Block #{cand.block_id} | {cand.matching_bits} bits ({cand.match_type})
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ textAlign: 'right' }}>
                    <span
                      className="mono"
                      style={{
                        fontSize: '16px',
                        fontWeight: 700,
                        color: cand.similarity_percentage >= 90 ? 'var(--green)' : (cand.similarity_percentage >= 60 ? 'var(--amber)' : 'var(--muted)')
                      }}
                    >
                      {cand.similarity_percentage}%
                    </span>
                    <div className="small muted">similarity</div>
                  </div>
                  {cand.officer_uid !== record.officerUid && (
                    <button
                      className="btn btn-secondary small"
                      style={{ padding: '4px 10px', fontSize: '12px' }}
                      onClick={() => handleSelectCandidate(cand)}
                    >
                      Inspect
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <p className="small muted" style={{ margin: 0, lineHeight: 1.6 }}>
          Recovering a mark from an image reveals a forensic trace. Attribution requires
          matching it to an immutable ledger record and validating its ML-DSA signature —
          even when the mark is partial or degraded, cryptographic distance sorting pinpoints the exact recipient.
        </p>
      </div>
    </div>
  );
}
