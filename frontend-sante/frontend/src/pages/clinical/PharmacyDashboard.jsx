import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import { deductStock, stockWithLevels } from './pharmacyStock.js';
import './clinical.css';

export default function PharmacyDashboard() {
  const [orders, setOrders] = useState([]);
  const [stock, setStock] = useState(stockWithLevels);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await clinicalApi.pharmacyQueue();
      setOrders(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'File pharmacie indisponible');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const refreshStock = () => setStock(stockWithLevels());

  const updateStatus = async (id, status, medications) => {
    try {
      await clinicalApi.updatePharmacyOrder(id, { status });
      if (status === 'dispensed') {
        const med = String(medications || '').toLowerCase();
        if (med.includes('paracétamol') || med.includes('paracetamol')) {
          deductStock('PARA-500', 20);
        }
        if (med.includes('amoxicilline')) deductStock('AMOX-500', 14);
        if (med.includes('ibuprofène') || med.includes('ibuprofene')) deductStock('IBU-400', 10);
        refreshStock();
      }
      setMessage(`Commande #${id} → ${status}`);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Mise à jour impossible');
    }
  };

  const pending = orders.filter((o) => o.status === 'pending').length;
  const preparing = orders.filter((o) => o.status === 'preparing' || o.status === 'ready').length;
  const lowStock = stock.filter((s) => s.low).length;

  const stats = [
    { label: 'Ordonnances en attente', value: pending, variant: 'warning' },
    { label: 'En préparation', value: preparing, variant: 'accent' },
    { label: 'Alertes stock', value: lowStock, variant: lowStock ? 'warning' : 'success' },
    { label: 'Références actives', value: stock.length },
  ];

  return (
    <div className="clinical-page">
      <h1>Tableau de bord — Pharmacie</h1>
      <p className="clinical-lead">Ordonnances, délivrance et visibilité du stock.</p>
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
                  <button type="button" className="clinical-btn secondary" onClick={() => updateStatus(order.id, 'preparing', order.medications)}>Préparer</button>
                )}
                {order.status === 'preparing' && (
                  <button type="button" className="clinical-btn secondary" onClick={() => updateStatus(order.id, 'ready', order.medications)}>Prêt</button>
                )}
                {(order.status === 'ready' || order.status === 'preparing') && (
                  <button type="button" className="clinical-btn" onClick={() => updateStatus(order.id, 'dispensed', order.medications)}>Délivrer</button>
                )}
              </div>
            </li>
          ))}
          {orders.length === 0 && <li>Aucune ordonnance en attente.</li>}
        </ul>
      </section>

      <section id="pharmacy-stock" className="clinical-card" style={{ marginTop: '1.25rem' }}>
        <h2>Stock — visibilité</h2>
        <p className="clinical-lead">Niveaux de stock opérationnels (mise à jour locale à la délivrance).</p>
        <table className="clinical-stock-table">
          <thead>
            <tr>
              <th>Réf.</th>
              <th>Médicament</th>
              <th>Quantité</th>
              <th>Seuil</th>
              <th>État</th>
            </tr>
          </thead>
          <tbody>
            {stock.map((item) => (
              <tr key={item.sku}>
                <td>{item.sku}</td>
                <td>{item.name}</td>
                <td>{item.qty} {item.unit}</td>
                <td>{item.threshold}</td>
                <td>
                  {item.low ? (
                    <span className="clinical-badge clinical-badge--warn">Stock bas</span>
                  ) : (
                    <span className="clinical-badge">OK</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
