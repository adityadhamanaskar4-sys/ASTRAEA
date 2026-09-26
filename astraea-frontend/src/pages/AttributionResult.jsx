import { Link } from 'react-router-dom';
import { useAstraea } from '../context/AstraeaContext';
import DataField from '../components/DataField';
import StatusChip from '../components/StatusChip';

export default function AttributionResult() {
  const { investigation } = useAstraea();

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

  const { record, wId } = investigation;

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow mono">STAGE 05 — ATTRIBUTION</div>
        <h1 className="page-title">Leak attributed</h1>
        <p className="page-desc">
          The recovered mark resolved to a single, signed, ledger-committed decryption session.
        </p>
      </div>

      <div className="panel spread">
        <StatusChip variant="complete">Watermark extracted</StatusChip>
        <StatusChip variant="verified">Cryptographically attributed</StatusChip>
      </div>

      <div className="panel panel-accent">
        <div className="panel-title">Case file</div>
        <DataField label="Officer UID" value={record.officerUid} />
        <DataField label="Officer name" value={record.officerName} />
        <DataField label="Document ID" value={record.docId} />
        <DataField label="Decryption session" value={record.sessionId} />
        <DataField label="Session time" value={new Date(record.timestamp).toLocaleString()} />
        <DataField label="W_ID (display-safe)" value={`${wId.slice(0, 8)}…${wId.slice(-4)}`} />
        <DataField label="ML-DSA verification" value={<span style={{ color: 'var(--green)' }}>VALID</span>} />
        <DataField label="Ledger record" value={<span style={{ color: 'var(--gold)' }}>COMMITTED</span>} />
      </div>

      <div className="panel">
        <p className="small muted" style={{ margin: 0, lineHeight: 1.6 }}>
          Recovering a mark from an image only shows a mark is present. Attribution required
          matching it to this specific ledger record and confirming its ML-DSA signature — both
          steps above passed, which is what makes this result admissible as attribution rather
          than a bare extraction.
        </p>
      </div>
    </div>
  );
}
