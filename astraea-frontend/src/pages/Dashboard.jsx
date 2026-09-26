import { Link } from 'react-router-dom';
import PipelineStepper from '../components/PipelineStepper';
import DataField from '../components/DataField';
import { listDocuments, listLedger, getNodes } from '../services/astraeaLedger';

const STORY = [
  { to: '/distribution', label: 'Distribution', desc: 'A document is sealed and sent to recipient lockboxes.' },
  { to: '/recipient', label: 'Recipient Terminal', desc: 'An officer requests access; the ledger commits before anything decrypts.' },
  { to: '/viewer', label: 'Secure Viewer', desc: 'The document renders normally, carrying an invisible forensic mark.' },
  { to: '/investigator', label: 'Investigator Portal', desc: 'A suspected leak is uploaded and the mark is recovered.' },
  { to: '/attribution', label: 'Attribution', desc: 'The recovered mark is matched against the ledger and verified.' },
];

export default function Dashboard() {
  const docs = listDocuments();
  const ledger = listLedger();
  const nodes = getNodes();
  const pendingLockboxes = docs.reduce(
    (sum, d) => sum + d.recipients.filter((r) => r.status !== 'decrypted').length,
    0
  );

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow mono">SIH DEMO · ASTRAEA</div>
        <h1 className="page-title">Chain of custody, made visible</h1>
        <p className="page-desc">
          This console walks the full path a classified document takes: who it was sent to, when
          access was requested, what the ledger recorded before decryption, and how a leaked photo
          is traced back to the officer who was granted access.
        </p>
      </div>

      <div className="panel">
        <div className="panel-title">The seven-stage chain</div>
        <PipelineStepper statusOf={() => 'pending'} />
      </div>

      <div className="panel panel-grid">
        <div className="stack">
          <DataField label="Documents distributed" value={docs.length} />
          <DataField label="Lockboxes awaiting decryption" value={pendingLockboxes} />
          <DataField label="Ledger height" value={ledger.length} />
          <DataField label="Ledger nodes online" value={`${nodes.filter((n) => n.status === 'online').length}/${nodes.length}`} />
        </div>
        <div className="stack">
          <div className="panel-title" style={{ marginBottom: 4 }}>Where to start</div>
          <p className="muted small" style={{ margin: 0, lineHeight: 1.6 }}>
            New to this demo? Start at Distribution to send a document, then switch to the
            Recipient Terminal to request access as one of its recipients.
          </p>
          <Link to="/distribution" className="btn btn-primary" style={{ textAlign: 'center', textDecoration: 'none', width: 'fit-content' }}>
            Go to Distribution
          </Link>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">Demo narrative</div>
        <div className="stack">
          {STORY.map((s, i) => (
            <Link key={s.to} to={s.to} className="data-field" style={{ textDecoration: 'none', color: 'inherit' }}>
              <span className="data-field-label">
                <span className="mono muted" style={{ marginRight: 10 }}>{i + 1}</span>
                {s.label}
              </span>
              <span className="data-field-value" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-ui)', fontWeight: 400, textAlign: 'left' }}>
                {s.desc}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
