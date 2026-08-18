import { useEffect, useMemo, useRef, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { formatGNF } from '../../utils/appointmentPresentation.js';

export default function PharmacyMedicationAutocomplete({
  value,
  onChange,
  onSelectItem,
  disabled,
  inventory,
  ariaLabel = 'Produit ou médicament',
}) {
  const [query, setQuery] = useState(value || '');
  const [remoteHits, setRemoteHits] = useState([]);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    setQuery(value || '');
  }, [value]);

  useEffect(() => {
    if (!query.trim()) {
      setRemoteHits([]);
      return undefined;
    }
    const t = setTimeout(async () => {
      try {
        const { data } = await clinicalApi.pharmacyInventorySearch(query.trim());
        setRemoteHits(data || []);
      } catch {
        setRemoteHits([]);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [query]);

  const localHits = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return inventory
      .filter(
        (item) =>
          item.medication_name?.toLowerCase().includes(q) ||
          item.sku?.toLowerCase().includes(q)
      )
      .slice(0, 12);
  }, [inventory, query]);

  const suggestions = remoteHits.length > 0 ? remoteHits : localHits;

  useEffect(() => {
    const onDoc = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const pick = (item) => {
    setQuery(item.medication_name);
    onChange(item.medication_name);
    onSelectItem?.(item);
    setOpen(false);
  };

  return (
    <div className="pharmacy-med-search" ref={wrapRef}>
      <input
        aria-label={ariaLabel}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        disabled={disabled}
        placeholder="Rechercher dans le stock (ex. Para…)"
        autoComplete="off"
      />
      {open && suggestions.length > 0 && (
        <ul className="pharmacy-med-search-results" role="listbox">
          {suggestions.map((item) => (
            <li key={item.id}>
              <button type="button" onClick={() => pick(item)}>
                <strong>{item.medication_name}</strong>
                <span>
                  Stock {item.quantity} · {formatGNF(item.unit_price_gnf)}
                  {item.out_of_stock ? ' · Rupture' : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
