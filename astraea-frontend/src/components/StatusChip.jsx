const VARIANT_CLASS = {
  pending: 'chip-pending',
  active: 'chip-active',
  complete: 'chip-complete',
  verified: 'chip-verified',
  error: 'chip-error',
};

export default function StatusChip({ variant = 'pending', children }) {
  return (
    <span className={`chip ${VARIANT_CLASS[variant] || 'chip-pending'}`}>
      <span className="chip-dot" />
      {children}
    </span>
  );
}
