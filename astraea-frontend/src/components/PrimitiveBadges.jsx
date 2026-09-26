import { PRIMITIVES } from '../services/cryptoSim';

export default function PrimitiveBadges() {
  return (
    <div className="row" style={{ flexWrap: 'wrap', gap: 8 }}>
      <span className="chip">{PRIMITIVES.symmetric}</span>
      <span className="chip">{PRIMITIVES.kem}</span>
      <span className="chip">{PRIMITIVES.signature}</span>
    </div>
  );
}
