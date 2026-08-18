export function ReadOnlyDisplay({ value }) {
  return <div className={`reception-his-auto-display${value ? ' reception-his-auto-display--filled' : ' reception-his-auto-display--empty'}`}>{value || '—'}</div>;
}

export function DisplayField({ label, value }) {
  return <div className="nurse-his-display-field"><span>{label}</span><ReadOnlyDisplay value={value} /></div>;
}

export function TextAreaField({ label, value, onChange, rows = 4 }) {
  return <label className="nurse-his-textarea-field">{label}<textarea rows={rows} value={value} onChange={onChange} /></label>;
}
