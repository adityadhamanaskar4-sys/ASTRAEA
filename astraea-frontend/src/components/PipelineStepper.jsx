export const CHAIN_STAGES = [
  { key: 'auth', label: 'Authentication' },
  { key: 'provenance', label: 'Provenance' },
  { key: 'authorization', label: 'Authorization' },
  { key: 'decryption', label: 'Decryption' },
  { key: 'watermarking', label: 'Watermarking' },
  { key: 'forensics', label: 'Forensics' },
  { key: 'attribution', label: 'Attribution' },
];

// statusOf: (stageKey) => 'pending' | 'active' | 'complete'
export default function PipelineStepper({ stages = CHAIN_STAGES, statusOf }) {
  return (
    <div className="stepper" role="list" aria-label="ASTRAEA chain of custody">
      {stages.map((stage) => {
        const status = statusOf ? statusOf(stage.key) : 'pending';
        return (
          <div className={`stepper-stage ${status}`} key={stage.key} role="listitem">
            <span className="stepper-line" aria-hidden="true" />
            <span className="stepper-marker" aria-hidden="true" />
            <span className="stepper-label">{stage.label}</span>
          </div>
        );
      })}
    </div>
  );
}
