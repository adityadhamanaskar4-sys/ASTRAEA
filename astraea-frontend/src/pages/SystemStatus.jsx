import { getNodes, listLedger, listDocuments } from '../services/astraeaLedger';
import StatusChip from '../components/StatusChip';
import DataField from '../components/DataField';

export default function SystemStatus() {
  const nodes = getNodes();
  const ledger = listLedger();
  const docs = listDocuments();

  return (
    <div>
      <div className="page-head">
        <div className="page-eyebrow mono">SYSTEM</div>
        <h1 className="page-title">System &amp; node status</h1>
        <p className="page-desc">
          Consensus node health and the append-only ledger this demo runs on top of.
        </p>
      </div>

      <div className="panel">
        <div className="panel-title">Consensus nodes</div>
        <div className="node-grid">
          {nodes.map((n) => (
            <div className="node-tile" key={n.name}>
              <div className="node-tile-name">{n.name}</div>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <StatusChip variant={n.status === 'online' ? 'verified' : 'error'}>{n.status}</StatusChip>
                <span className="small mono muted">h/{n.height}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel panel-grid">
        <DataField label="Ledger height" value={ledger.length} />
        <DataField label="Documents tracked" value={docs.length} />
      </div>

      <div className="panel">
        <div className="panel-title">Recent ledger records</div>
        {ledger.length === 0 && <p className="muted small">No records committed yet.</p>}
        <div className="stack">
          {ledger.slice(0, 12).map((r) => (
            <div className="data-field" key={r.ledgerId}>
              <span className="data-field-label">
                {r.ledgerId} — {r.officerName} <span className="mono muted">{r.docId}</span>
              </span>
              <span className="data-field-value" style={{ color: 'var(--gold)' }}>COMMITTED</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
