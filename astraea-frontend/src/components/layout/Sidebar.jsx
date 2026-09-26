import { NavLink } from 'react-router-dom';
import sealUrl from '../../assets/seal.svg';
import { getNodes } from '../../services/astraeaLedger';

const LINKS = [
  { to: '/', label: 'Dashboard', index: '01' },
  { to: '/distribution', label: 'Distribution', index: '02' },
  { to: '/recipient', label: 'Recipient Terminal', index: '03' },
  { to: '/viewer', label: 'Secure Viewer', index: '04' },
  { to: '/investigator', label: 'Investigator Portal', index: '05' },
  { to: '/attribution', label: 'Attribution', index: '06' },
  { to: '/system', label: 'System Status', index: '07' },
];

export default function Sidebar() {
  const nodes = getNodes();
  const online = nodes.filter((n) => n.status === 'online').length;

  return (
    <aside className="sidebar">
      <div className="brand">
        <img src={sealUrl} alt="" className="brand-mark" />
        <div>
          <div className="brand-name">ASTRAEA</div>
          <div className="brand-sub">chain-of-custody demo</div>
        </div>
      </div>

      <nav className="nav">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/'}
            className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
          >
            <span className="nav-index mono">{link.index}</span>
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="spread">
          <span>LEDGER NODES</span>
          <span style={{ color: 'var(--teal)' }}>{online}/{nodes.length} ONLINE</span>
        </div>
        <div>SIH DEMO BUILD · v0.1</div>
      </div>
    </aside>
  );
}
