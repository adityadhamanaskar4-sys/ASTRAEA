function formatTime(ts) {
  if (!ts) return '';
  return new Date(ts).toLocaleTimeString([], { hour12: false });
}

export default function StepLog({ steps, statuses, times }) {
  return (
    <div className="step-log">
      {steps.map((step) => {
        const status = statuses[step.key] || 'pending';
        return (
          <div className={`step-log-row ${status}`} key={step.key}>
            <span className="step-log-marker" />
            <span>{step.label}</span>
            {times?.[step.key] && <span className="step-log-time mono">{formatTime(times[step.key])}</span>}
          </div>
        );
      })}
    </div>
  );
}
