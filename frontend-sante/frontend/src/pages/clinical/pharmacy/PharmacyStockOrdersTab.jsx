import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../../services/clinicalApi.js';
import { formatApiError } from '../../../utils/apiError.js';
import { formatClinicalDate } from '../../../utils/clinicalPresentation.js';

const EMPTY = { inventory_item_id: '', medication_name: '', quantity: '', supplier: '' };
const STATUS = { ordered: 'Commandée', received: 'Réceptionnée', cancelled: 'Annulée' };

export default function PharmacyStockOrdersTab({ inventory, onInventoryChange }) {
  const [orders, setOrders] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    const { data } = await clinicalApi.pharmacyStockOrders();
    setOrders(data || []);
  }, []);

  useEffect(() => { load().catch((err) => setError(formatApiError(err, 'Chargement des commandes impossible'))); }, [load]);

  const chooseMedication = (value) => {
    const item = inventory.find((row) => String(row.id) === value);
    setForm((previous) => ({
      ...previous,
      inventory_item_id: value,
      medication_name: item?.medication_name || '',
    }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true); setError(''); setMessage('');
    try {
      await clinicalApi.createPharmacyStockOrder({
        inventory_item_id: Number(form.inventory_item_id),
        medication_name: form.medication_name,
        quantity: Number(form.quantity),
        supplier: form.supplier.trim(),
      });
      setForm(EMPTY);
      setMessage('Commande de stock enregistrée.');
      await load();
    } catch (err) {
      setError(formatApiError(err, 'Enregistrement de la commande impossible'));
    } finally { setLoading(false); }
  };

  const closeOrder = async (order, action) => {
    setLoading(true); setError(''); setMessage('');
    try {
      if (action === 'receive') await clinicalApi.receivePharmacyStockOrder(order.id);
      else await clinicalApi.cancelPharmacyStockOrder(order.id);
      setMessage(action === 'receive' ? 'Commande réceptionnée et quantité ajoutée au stock.' : 'Commande annulée.');
      await load();
      if (action === 'receive') {
        const { data } = await clinicalApi.pharmacyInventory();
        onInventoryChange?.(data || []);
      }
    } catch (err) { setError(formatApiError(err, 'Mise à jour impossible')); }
    finally { setLoading(false); }
  };

  return (
    <section className="pharmacy-panel pharmacy-orders-panel" aria-labelledby="stock-orders-title">
      <div className="pharmacy-panel-header">
        <div><p className="pharmacy-section-kicker">Approvisionnement</p><h2 id="stock-orders-title">Commandes de stock</h2></div>
        <p className="clinical-hint">Le fournisseur reste dans ce registre; le stock affiche uniquement ce qui aide à délivrer.</p>
      </div>
      {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}
      {message && <p className="clinical-message clinical-message--ok" role="status">{message}</p>}
      <form className="pharmacy-order-form" onSubmit={submit}>
        <label>Médicament
          <select value={form.inventory_item_id} onChange={(event) => chooseMedication(event.target.value)} required>
            <option value="">Choisir dans le stock</option>
            {inventory.map((item) => <option key={item.id} value={item.id}>{item.medication_name} · stock {item.quantity}</option>)}
          </select>
        </label>
        <label>Quantité commandée
          <input type="number" min="1" value={form.quantity} onChange={(event) => setForm((p) => ({ ...p, quantity: event.target.value }))} required />
        </label>
        <label>Fournisseur
          <input value={form.supplier} onChange={(event) => setForm((p) => ({ ...p, supplier: event.target.value }))} required />
        </label>
        <button className="clinical-btn pharmacy-his-primary-action" disabled={loading}>{loading ? 'Enregistrement…' : 'Enregistrer la commande'}</button>
      </form>
      <div className="pharmacy-table-wrap" tabIndex="0" role="region" aria-label="Registre des commandes de stock">
        <table className="pharmacy-table">
          <thead><tr><th>N°</th><th>Date</th><th>Médicament</th><th>Quantité</th><th>Fournisseur</th><th>État</th><th>Actions</th></tr></thead>
          <tbody>
            {orders.length ? orders.map((order) => (
              <tr key={order.id}>
                <td><strong>{order.order_number}</strong></td><td>{formatClinicalDate(order.ordered_at)}</td><td>{order.medication_name}</td><td>{order.quantity}</td><td>{order.supplier}</td>
                <td><span className={`pharmacy-badge pharmacy-badge--${order.status === 'received' ? 'success' : order.status === 'cancelled' ? 'muted' : 'warning'}`}>{STATUS[order.status] || order.status}</span></td>
                <td className="pharmacy-stock-actions">{order.status === 'ordered' && <><button type="button" className="clinical-btn" onClick={() => closeOrder(order, 'receive')} disabled={loading}>Réceptionner</button><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => closeOrder(order, 'cancel')} disabled={loading}>Annuler</button></>}</td>
              </tr>
            )) : <tr><td colSpan="7" className="pharmacy-empty">Aucune commande enregistrée.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
