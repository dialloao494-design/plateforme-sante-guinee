import './ClinicalWorkflowNav.css';

export default function ClinicalWorkflowNav({ items, value, onChange, label, testIdPrefix }) {
  return (
    <nav className="clinical-workflow-nav" aria-label={label}>
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          data-testid={testIdPrefix ? `${testIdPrefix}-${item.id}` : undefined}
          className={value === item.id ? 'active' : ''}
          aria-current={value === item.id ? 'page' : undefined}
          onClick={() => onChange(item.id)}
        >
          {item.label}
          {item.shortcut ? <kbd>{item.shortcut}</kbd> : null}
        </button>
      ))}
    </nav>
  );
}
