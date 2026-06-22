import { useState } from 'react';
import './PasswordInput.css';

export default function PasswordInput({
  id,
  value,
  onChange,
  placeholder = 'Mot de passe',
  autoComplete = 'current-password',
  disabled = false,
  required = true,
  readOnly = false,
  label,
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="password-input-wrap">
      {label && <label htmlFor={id}>{label}</label>}
      <div className="password-input-field">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          disabled={disabled}
          required={required}
          readOnly={readOnly}
        />
        <button
          type="button"
          className="password-input-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
          tabIndex={-1}
          disabled={disabled}
        >
          {visible ? '🙈' : '👁'}
        </button>
      </div>
    </div>
  );
}

export async function copyToClipboard(text) {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
