import { useCallback, useEffect, useMemo, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { formatApiError } from '../../utils/apiError.js';

const EMPTY_FORM = {
  sku: '',
  medication_name: '',
  quantity: '',
  reorder_level: '10',
  unit_price_gnf: '',
  purchase_price_gnf: '',
  batch_number: '',
  expiry_date: '',
  supplier: '',
};

export default function PharmacyStockTab({ onInventoryChange }) {
  const [items, setItems] = useState([]);
  const [searchQ, setSearchQ] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const { data } = await clinicalApi.pharmacyInventory();
    setItems(data || []);
    onInventoryChange?.(data || []);
  }, [onInventoryChange]);

  useEffect(() => {
    load().catch(() => {});
  }, [load]);

  const filtered = useMemo(() => {
    const q = searchQ.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (i) =>
        i.medication_name?.toLowerCase().includes(q) ||
        i.sku?.toLowerCase().includes(q) ||
        i.supplier?.toLowerCase().includes(q)
    );
  }, [items, searchQ]);

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const startEdit = (item) => {
    setEditingId(item.id);
    setForm({
      sku: item.sku || '',
      medication_name: item.medication_name || '',
      quantity: String(item.quantity ?? ''),
      reorder_level: String(item.reorder_level ?? '10'),
      unit_price_gnf: String(item.unit_price_gnf ?? ''),
      purchase_price_gnf: item.purchase_price_gnf != null ? String(item.purchase_price_gnf) : '',
      batch_number: item.batch_number || '',
      expiry_date: item.expiry_date || '',
      supplier: item.supplier || '',
    });
  };

  const saveItem = async (e) => {
    e.preventDefault();
    if (!form.sku.trim() || !form.medication_name.trim()) {
      setError('SKU et nom du médicament sont obligatoires.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const payload = {
        sku: form.sku.trim(),
        medication_name: form.medication_name.trim(),
        quantity: Number(form.quantity) || 0,
        reorder_level: Number(form.reorder_level) || 10,
        unit_price_gnf: Number(form.unit_price_gnf) || 0,
        purchase_price_gnf: form.purchase_price_gnf === '' ? null : Number(form.purchase_price_gnf),
        batch_number: form.batch_number.trim() || null,
        expiry_date: form.expiry_date || null,
        supplier: form.supplier.trim() || null,
      };
      if (editingId) {
        await clinicalApi.updatePharmacyInventoryItem(editingId, payload);
        setMessage('Médicament mis à jour.');
      } else {
        await clinicalApi.upsertPharmacyInventory(payload);
        setMessage('Médicament ajouté au stock.');
      }
      resetForm();
      await load();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement impossible'));
    } finally {
      setLoading(false);
    }
  };

  const deleteItem = async (item) => {
    if (!window.confirm(`Supprimer « ${item.medication_name} » du stock ?`)) return;
    setLoading(true);
    setError('');
    try {
      await clinicalApi.deletePharmacyInventoryItem(item.id);
      if (editingId === item.id) resetForm();
      setMessage('Médicament supprimé.');
      await load();
    } catch (err) {
      setError(formatApiError(err, 'Suppression impossible'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pharmacy-panel pharmacy-stock-panel">
      <div className="pharmacy-panel-header">
        <h2>Stock pharmacie</h2>
        <div className="pharmacy-toolbar">
          <input
            type="search"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            placeholder="Rechercher un médicament…"
          />
        </div>
      </div>

      {error && <p className="clinical-message clinical-message--err">{error}</p>}
      {message && <p className="clinical-message clinical-message--ok">{message}</p>}

      <form className="pharmacy-stock-form" onSubmit={saveItem}>
        <div className="reception-his-form-row reception-his-form-row--4">
          <label>
            SKU / Code
            <input value={form.sku} onChange={(e) => setForm((p) => ({ ...p, sku: e.target.value }))} required />
          </label>
          <label>
            Nom du médicament
            <input
              value={form.medication_name}
              onChange={(e) => setForm((p) => ({ ...p, medication_name: e.target.value }))}
              required
            />
          </label>
          <label>
            Quantité disponible
            <input type="number" min="0" value={form.quantity} onChange={(e) => setForm((p) => ({ ...p, quantity: e.target.value }))} />
          </label>
          <label>
            Prix de vente (GNF)
            <input type="number" min="0" value={form.unit_price_gnf} onChange={(e) => setForm((p) => ({ ...p, unit_price_gnf: e.target.value }))} />
          </label>
        </div>
        <div className="reception-his-form-row reception-his-form-row--4">
          <label>
            Prix d&apos;achat (GNF)
            <input type="number" min="0" value={form.purchase_price_gnf} onChange={(e) => setForm((p) => ({ ...p, purchase_price_gnf: e.target.value }))} />
          </label>
          <label>
            Seuil alerte
            <input type="number" min="0" value={form.reorder_level} onChange={(e) => setForm((p) => ({ ...p, reorder_level: e.target.value }))} />
          </label>
          <label>
            N° lot
            <input value={form.batch_number} onChange={(e) => setForm((p) => ({ ...p, batch_number: e.target.value }))} />
          </label>
          <label>
            Date expiration
            <input type="date" value={form.expiry_date} onChange={(e) => setForm((p) => ({ ...p, expiry_date: e.target.value }))} />
          </label>
        </div>
        <label>
          Fournisseur
          <input value={form.supplier} onChange={(e) => setForm((p) => ({ ...p, supplier: e.target.value }))} />
        </label>
        <div className="pharmacy-his-actions">
          <button type="submit" className="clinical-btn pharmacy-his-primary-action" disabled={loading}>
            {loading ? 'Enregistrement…' : editingId ? 'Mettre à jour' : 'Ajouter au stock'}
          </button>
          {editingId && (
            <button type="button" className="clinical-btn clinical-btn--secondary" onClick={resetForm}>
              Annuler
            </button>
          )}
        </div>
      </form>

      <div className="pharmacy-table-wrap">
        <table className="pharmacy-table">
          <thead>
            <tr>
              <th>Médicament</th>
              <th>SKU</th>
              <th>Qté</th>
              <th>Prix vente</th>
              <th>Prix achat</th>
              <th>Lot</th>
              <th>Expiration</th>
              <th>Fournisseur</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id} className={item.out_of_stock ? 'pharmacy-stock-row--out' : item.low_stock ? 'pharmacy-stock-row--low' : ''}>
                <td>{item.medication_name}</td>
                <td>{item.sku}</td>
                <td>{item.quantity}</td>
                <td>{formatGNF(item.unit_price_gnf)}</td>
                <td>{item.purchase_price_gnf != null ? formatGNF(item.purchase_price_gnf) : '—'}</td>
                <td>{item.batch_number || '—'}</td>
                <td>{item.expiry_date || '—'}</td>
                <td>{item.supplier || '—'}</td>
                <td className="pharmacy-stock-actions">
                  <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => startEdit(item)}>
                    Modifier
                  </button>
                  <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => deleteItem(item)}>
                    Supprimer
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
