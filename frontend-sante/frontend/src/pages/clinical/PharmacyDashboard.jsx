import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import './clinical.css';

export default function PharmacyDashboard() {
  const [orders, setOrders] = useState([]);
  const [stock, setStock] = useState([]);
  const [stockForm, setStockForm] = useState({ medication_name: '', sku: '', quantity: 50, reorder_level: 10 });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [ordersRes, stockRes] = await Promise.all([
        clinicalApi.pharmacyQueue(),
        clinicalApi.pharmacyInventory(),
      ]);
      setOrders(ordersRes.data || []);
      setStock(stockRes.data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'File pharmacie indisponible');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const updateStatus = async (id, status) => {
    try {
      await clinicalApi.updatePharmacyOrder(id, { status });
      setMessage(`Commande #${id} → ${status}`);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Mise à jour impossible');
    }
  };

  const saveStock = async (e) => {
    e.preventDefault();
    try {
      await clinicalApi.upsertPharmacyInventory({
        ...stockForm,
        quantity: Number(stockForm.quantity),
        reorder_level: Number(stockForm.reorder_level),
      });
      setMessage(`Stock ${stockForm.medication_name} enregistré`);
      setStockForm({ medication_name: '', sku: '', quantity: 50, reorder_level: 10 });
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Stock impossible');
    }
  };

  const pending = orders.filter((o) => o.status === 'pending').length;
  const preparing = orders.filter((o) => o.status === 'preparing' || o.status === 'ready').length;
  const lowStock = stock.filter((s) => s.low_stock).length;

  const stats = [
    { label: 'Ordonnances en attente', value: pending, variant: 'warning' },
    { label: 'En préparation', value: preparing, variant: 'accent' },
    { label: 'Alertes stock', value: lowStock, variant: lowStock ? 'warning' : 'success' },
    { label: 'Références actives', value: stock.length },
  ];

  return (
    <div className="clinical-page">
      <h1>Tableau de bord — Pharmacie</h1>
      <p className="clinical-lead">Ordonnances, délivrance et stock clinique (backend).</p>
      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

      <nav className="clinical-section-nav" aria-label="Sections pharmacie">
        <a href="#pharmacy-orders">Ordonnances</a>
        <a href="#pharmacy-stock">Stock</a>
      </nav>

      <section id="pharmacy-orders" className="clinical-card">
        <h2>Ordonnances à délivrer</h2>
        <ul className="clinical-list">
          {orders.map((order) => (
            <li key={order.id}>
              <strong>{order.patient_name}</strong>
              <br />
              {order.medications}
              <br />
              <span className="clinical-badge">{order.status}</span>
              <div className="clinical-actions">
                {order.status === 'pending' && (
                  <button type="button" className="clinical-btn secondary" onClick={() => updateStatus(order.id, 'preparing')}>
                    Préparer
                  </button>
                )}
                {['pending', 'preparing', 'ready'].includes(order.status) && (
                  <button type="button" className="clinical-btn" onClick={() => updateStatus(order.id, 'dispensed')}>
                    Délivrer
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section id="pharmacy-stock" className="clinical-card">
        <h2>Stock médicaments</h2>
        <form onSubmit={saveStock} className="clinical-form" style={{ marginBottom: '1rem' }}>
          <div className="clinical-field">
            <label>Médicament</label>
            <input value={stockForm.medication_name} onChange={(e) => setStockForm({ ...stockForm, medication_name: e.target.value })} required />
          </div>
          <div className="clinical-field">
            <label>SKU</label>
            <input value={stockForm.sku} onChange={(e) => setStockForm({ ...stockForm, sku: e.target.value })} required />
          </div>
          <div className="clinical-field">
            <label>Quantité</label>
            <input type="number" value={stockForm.quantity} onChange={(e) => setStockForm({ ...stockForm, quantity: e.target.value })} />
          </div>
          <button type="submit" className="clinical-btn">Ajouter / mettre à jour</button>
        </form>
        <ul className="clinical-list">
          {stock.map((item) => (
            <li key={item.id}>
              <strong>{item.medication_name}</strong> ({item.sku}) — {item.quantity} unités
              {item.low_stock && <span className="clinical-badge">Stock bas</span>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
