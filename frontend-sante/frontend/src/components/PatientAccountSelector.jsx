import { useEffect, useRef, useState } from 'react';
import httpClient from '../services/httpClient';
import './PatientAccountSelector.css';

/**
 * Searchable selector for unlinked patient-role user accounts.
 * Replaces raw numeric user_id entry to prevent operator mistakes.
 */
export default function PatientAccountSelector({ value, onChange, disabled = false }) {
  const [query, setQuery] = useState('');
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState(null);
  const wrapRef = useRef(null);
  const selected = value && value.id ? value : null;

  useEffect(() => {
    const onDocClick = (event) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setOptions([]);
      setError(null);
      return undefined;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await httpClient.get('/patients/linkable-accounts', {
          params: { q, limit: 20 },
        });
        if (!cancelled) {
          setOptions(Array.isArray(data) ? data : []);
          setOpen(true);
        }
      } catch (err) {
        if (!cancelled) {
          setOptions([]);
          setError(err?.response?.data?.detail || 'Recherche de compte impossible');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  const selectAccount = (account) => {
    onChange?.(account);
    setQuery('');
    setOpen(false);
  };

  const clearSelection = () => {
    onChange?.(null);
    setQuery('');
    setOptions([]);
  };

  return (
    <div className="patient-account-selector" ref={wrapRef}>
      {selected ? (
        <div className="patient-account-selector__selected">
          <span>
            Compte lié : <strong>{selected.email}</strong>
          </span>
          <button type="button" onClick={clearSelection} disabled={disabled}>
            Changer
          </button>
        </div>
      ) : (
        <>
          <label className="patient-account-selector__label" htmlFor="patient-account-search">
            Compte patient (recherche email)
          </label>
          <input
            id="patient-account-search"
            type="search"
            autoComplete="off"
            placeholder="Tapez au moins 2 caractères (email)…"
            value={query}
            disabled={disabled}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => options.length > 0 && setOpen(true)}
          />
          {loading && <p className="patient-account-selector__hint">Recherche…</p>}
          {error && <p className="patient-account-selector__error">{error}</p>}
          {open && options.length > 0 && (
            <ul className="patient-account-selector__list" role="listbox">
              {options.map((opt) => (
                <li key={opt.id}>
                  <button type="button" role="option" onClick={() => selectAccount(opt)}>
                    <span className="patient-account-selector__email">{opt.email}</span>
                    <span className="patient-account-selector__meta">compte #{opt.id}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {open && !loading && query.trim().length >= 2 && options.length === 0 && !error && (
            <p className="patient-account-selector__hint">Aucun compte patient disponible</p>
          )}
        </>
      )}
    </div>
  );
}
