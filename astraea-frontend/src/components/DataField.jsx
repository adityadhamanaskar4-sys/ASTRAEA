export default function DataField({ label, value }) {
  return (
    <div className="data-field">
      <span className="data-field-label">{label}</span>
      <span className="data-field-value">{value}</span>
    </div>
  );
}
