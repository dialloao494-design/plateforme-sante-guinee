import { useCallback, useEffect, useMemo, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { formatGNF } from '../../utils/appointmentPresentation.js';
import { formatApiError } from '../../utils/apiError.js';
import { useAuth } from '../../contexts/AuthContext.jsx';
import {
  computeStockAlerts,
  filterOrders,
  filterStock,
  loadMovements,
  saveMovement,
  statusMeta,
  totalStockValue,
} from '../../utils/pharmacyWorkspace.js';
import './clinical.css';
import './pharmacy.css';

const EMPTY_STOCK_FORM = {
  medication_name: '',
  sku: '',
  quantity: 50,
  reorder_level: 10,
  unit_price_gnf: 25_000,
  batch_number: '',
  expiry_date: '',
  supplier: '',
};

function Badge({ status }) {
  const meta = statusMeta(status);
  return <span className={`pharmacy-badge pharmacy-badge--${meta.tone}`}>{meta.label}</span>;
}

function formatDateTime(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('fr-FR');
  } catch {
    return String(value);
  }
}

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString('fr-FR');
  } catch {
    return String(value);
  }
}

export default function PharmacyDashboard() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [dispensedToday, setDispensedToday] = useState([]);
  const [stock, setStock] = useState([]);
  const [movements, setMovements] = useState(loadMovements);
  const [revenue, setRevenue] = useState(null);
  const [tab, setTab] = useState('orders');
  const [orderFilter, setOrderFilter] = useState('all');
  const [orderSearch, setOrderSearch] = useState('');
  const [stockSearch, setStockSearch] = useState('');
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [stockForm, setStockForm] = useState(EMPTY_STOCK_FORM);
  const [editingStock, setEditingStock] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [pharmacyStats, setPharmacyStats] = useState(null);
  const [doctorDeliveries, setDoctorDeliveries] = useState([]);
  const [doctorForm, setDoctorForm] = useState({
    patient_name: '',
    medicine_name: '',
    quantity: 1,
    doctor_name: '',
    reason: '',
  });
  const [pharmacyReport, setPharmacyReport] = useState(null);
  const [reportMonth, setReportMonth] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });
  const [saleForm, setSaleForm] = useState({ item_id: '', quantity: 1, patient_name: '' });
  const [stockAdjust, setStockAdjust] = useState({ item_id: '', delta: 10, reason: 'Réapprovisionnement' });

  const load = useCallback(async () => {
    try {
      const today = new Date().toISOString().slice(0, 10);
      const [ordersRes, todayRes, stockRes, revRes, dashRes, doctorRes] = await Promise.all([
        clinicalApi.pharmacyQueue({ scope: 'all' }),
        clinicalApi.pharmacyQueue({ scope: 'dispensed_today' }),
        clinicalApi.pharmacyInventory(),
        clinicalApi.dailyRevenue(today).catch(() => ({ data: null })),
        clinicalApi.pharmacyDashboardStats().catch(() => ({ data: null })),
        clinicalApi.doctorMedicineDeliveries().catch(() => ({ data: [] })),
      ]);
      setOrders(ordersRes.data || []);
      setDispensedToday(todayRes.data || []);
      setStock(stockRes.data || []);
      setRevenue(revRes.data || null);
      setPharmacyStats(dashRes.data || null);
      setDoctorDeliveries(doctorRes.data || []);
      setError('');
    } catch (err) {
      setError(formatApiError(err, 'Chargement pharmacie impossible'));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (tab !== 'report') return;
    const [year, month] = reportMonth.split('-').map(Number);
    clinicalApi.pharmacyMonthlyReport(year, month)
      .then(({ data }) => setPharmacyReport(data))
      .catch((err) => setError(err?.response?.data?.detail || 'Rapport indisponible'));
  }, [tab, reportMonth]);

  const saveDoctorDelivery = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await clinicalApi.createDoctorMedicineDelivery({
        ...doctorForm,
        quantity: Number(doctorForm.quantity),
      });
      setMessage('Livraison cabinet médecin enregistrée (hors stock pharmacie)');
      setDoctorForm({ patient_name: '', medicine_name: '', quantity: 1, doctor_name: '', reason: '' });
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Enregistrement impossible');
    } finally {
      setBusy(false);
    }
  };

  const alerts = useMemo(() => computeStockAlerts(stock), [stock]);
  const stockValue = useMemo(() => totalStockValue(stock), [stock]);
  const filteredOrders = useMemo(
    () => filterOrders(orders, { status: orderFilter, query: orderSearch }),
    [orders, orderFilter, orderSearch]
  );
  const filteredStock = useMemo(() => filterStock(stock, stockSearch), [stock, stockSearch]);

  const pendingCount = orders.filter((o) => o.status === 'pending').length;
  const pharmacyRevenueToday =
    revenue?.by_charge_type?.pharmacy ?? revenue?.by_charge_type?.Pharmacie ?? null;

  const stats = pharmacyStats
    ? [
        { label: 'Ordonnances en attente', value: pharmacyStats.pending_orders, tone: 'warning', hint: 'À traiter' },
        { label: 'Délivrées aujourd\'hui', value: pharmacyStats.dispensed_today, tone: 'success', hint: 'Session du jour' },
        { label: 'Délivrées ce mois', value: pharmacyStats.dispensed_this_month, tone: 'accent', hint: 'Mensuel' },
        { label: 'Stock bas', value: pharmacyStats.low_stock_count, tone: pharmacyStats.low_stock_count ? 'warning' : 'muted', hint: 'Sous seuil' },
        { label: 'Valeur stock', value: formatGNF(pharmacyStats.stock_value_gnf), tone: 'accent', hint: 'Estimation' },
      ]
    : [
        { label: 'Ordonnances en attente', value: pendingCount, tone: 'warning', hint: 'À traiter' },
        { label: 'Délivrées aujourd\'hui', value: dispensedToday.length, tone: 'success', hint: 'Session du jour' },
        { label: 'Stock bas', value: alerts.low.length, tone: alerts.low.length ? 'warning' : 'muted', hint: 'Sous seuil' },
        { label: 'Expire bientôt', value: alerts.expiring.length, tone: alerts.expiring.length ? 'danger' : 'muted', hint: '< 30 jours' },
        { label: 'Valeur stock', value: formatGNF(stockValue), tone: 'accent', hint: 'Estimation' },
        {
          label: 'Recettes pharmacie',
          value: pharmacyRevenueToday != null ? formatGNF(pharmacyRevenueToday) : '—',
          tone: 'accent',
          hint: 'Aujourd\'hui',
        },
      ];

  const recordMovement = (order, action, quantityHint) => {
    const pharmacist = user?.full_name || user?.email?.split('@')[0] || 'Pharmacien';
    const meds = order.items?.length
      ? order.items.map((i) => i.medication_name).join(', ')
      : order.medications;
    const qty = quantityHint || order.items?.[0]?.quantity || '—';
    const next = saveMovement({
      pharmacist,
      patient_name: order.patient_name,
      medicine: meds,
      quantity: qty,
      at: new Date().toISOString(),
      order_id: order.id,
      action,
    });
    setMovements(next);
  };

  const logStockMovement = (item, action, quantity, patientName = '—') => {
    const pharmacist = user?.full_name || user?.email?.split('@')[0] || 'Pharmacien';
    const next = saveMovement({
      pharmacist,
      patient_name: patientName,
      medicine: item.medication_name,
      quantity,
      at: new Date().toISOString(),
      order_id: `stock-${item.id}`,
      action,
    });
    setMovements(next);
  };

  const applyStockDelta = async (itemId, delta, reason, patientName) => {
    setBusy(true);
    setError('');
    try {
      const item = stock.find((s) => String(s.id) === String(itemId));
      await clinicalApi.adjustPharmacyInventory(itemId, { delta });
      if (item) {
        logStockMovement(item, reason, Math.abs(delta), patientName);
      }
      setMessage(`Stock mis à jour (${delta > 0 ? '+' : ''}${delta})`);
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Mouvement stock impossible');
    } finally {
      setBusy(false);
    }
  };

  const submitDirectSale = async (e) => {
    e.preventDefault();
    if (!saleForm.item_id) {
      setError('Choisissez un médicament');
      return;
    }
    const qty = Number(saleForm.quantity);
    if (qty < 1) {
      setError('Quantité invalide');
      return;
    }
    await applyStockDelta(saleForm.item_id, -qty, 'Vente directe', saleForm.patient_name || 'Client comptoir');
    setSaleForm({ item_id: '', quantity: 1, patient_name: '' });
  };

  const submitStockEntry = async (e) => {
    e.preventDefault();
    if (!stockAdjust.item_id) {
      setError('Choisissez un article');
      return;
    }
    const delta = Number(stockAdjust.delta);
    await applyStockDelta(stockAdjust.item_id, delta, stockAdjust.reason || (delta > 0 ? 'Entrée stock' : 'Sortie stock'));
    setStockAdjust((prev) => ({ ...prev, delta: 10, reason: 'Réapprovisionnement' }));
  };

  const updateStatus = async (order, status) => {
    setBusy(true);
    setError('');
    try {
      await clinicalApi.updatePharmacyOrder(order.id, { status });
      setMessage(`Ordonnance #${order.id} → ${statusMeta(status).label}`);
      if (status === 'dispensed' || status === 'partially_dispensed') {
        recordMovement(order, statusMeta(status).label, order.items?.[0]?.quantity);
      }
      if (selectedOrder?.id === order.id) {
        setSelectedOrder(null);
      }
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Mise à jour impossible');
    } finally {
      setBusy(false);
    }
  };

  const saveStock = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await clinicalApi.upsertPharmacyInventory({
        ...stockForm,
        quantity: Number(stockForm.quantity),
        reorder_level: Number(stockForm.reorder_level),
        unit_price_gnf: Number(stockForm.unit_price_gnf),
        batch_number: stockForm.batch_number || undefined,
        expiry_date: stockForm.expiry_date || undefined,
        supplier: stockForm.supplier || undefined,
      });
      setMessage(`Stock ${stockForm.medication_name} enregistré`);
      setStockForm(EMPTY_STOCK_FORM);
      setEditingStock(null);
      await load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Stock impossible');
    } finally {
      setBusy(false);
    }
  };

  const startEditStock = (item) => {
    setEditingStock(item);
    setStockForm({
      medication_name: item.medication_name,
      sku: item.sku,
      quantity: item.quantity,
      reorder_level: item.reorder_level,
      unit_price_gnf: item.unit_price_gnf,
      batch_number: item.batch_number || '',
      expiry_date: item.expiry_date || '',
      supplier: item.supplier || '',
    });
    setTab('stock');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const historyRows = useMemo(() => {
    const fromOrders = orders
      .filter((o) => ['dispensed', 'partially_dispensed'].includes(o.status))
      .map((o) => ({
        id: `order-${o.id}`,
        pharmacist: o.prepared_by || '—',
        patient_name: o.patient_name,
        medicine: o.medications,
        quantity: o.items?.[0]?.quantity ?? '—',
        at: o.dispensed_at || o.created_at,
        order_id: o.id,
        action: statusMeta(o.status).label,
      }));
    const merged = [...movements, ...fromOrders];
    const seen = new Set();
    return merged
      .filter((row) => {
        const key = `${row.order_id}-${row.at}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .sort((a, b) => new Date(b.at) - new Date(a.at))
      .slice(0, 50);
  }, [movements, orders]);

  return (
    <div className="clinical-page pharmacy-page">
      <header className="pharmacy-header">
        <div>
          <h1>Poste pharmacie</h1>
          <p className="clinical-lead">Ordonnances, stock, alertes et traçabilité — stock pharmacie et livraisons cabinet médecin.</p>
        </div>
        <div className="pharmacy-header-actions">
          <button type="button" className="pharmacy-btn pharmacy-btn--secondary" onClick={load} disabled={busy}>
            Actualiser
          </button>
        </div>
      </header>

      {error && (
        <div className="clinical-retry-bar">
          <p>{String(error)}</p>
          <button type="button" className="clinical-btn" onClick={load} disabled={busy}>Réessayer</button>
        </div>
      )}
      {message && <p className="clinical-success">{message}</p>}

      <div className="pharmacy-stat-grid">
        {stats.map((s) => (
          <div key={s.label} className={`pharmacy-stat pharmacy-stat--${s.tone}`}>
            <span className="pharmacy-stat-label">{s.label}</span>
            <strong className="pharmacy-stat-value">{s.value}</strong>
            {s.hint && <span className="pharmacy-stat-hint">{s.hint}</span>}
          </div>
        ))}
      </div>

      <nav className="pharmacy-tabs" aria-label="Sections pharmacie">
        {[
          ['orders', 'Ordonnances'],
          ['stock', 'Stock'],
          ['sale', 'Vente directe'],
          ['alerts', 'Alertes'],
          ['history', 'Mouvements'],
          ['doctor', 'Stock médecin'],
          ['report', 'Rapport mensuel'],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            className={`pharmacy-tab${tab === key ? ' active' : ''}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === 'orders' && (
        <section id="pharmacy-orders" className="pharmacy-panel">
          <div className="pharmacy-panel-header">
            <h2>Ordonnances / commandes</h2>
            <div className="pharmacy-toolbar">
              <input
                type="search"
                placeholder="Patient, médecin, médicament…"
                value={orderSearch}
                onChange={(e) => setOrderSearch(e.target.value)}
              />
              <select value={orderFilter} onChange={(e) => setOrderFilter(e.target.value)}>
                <option value="all">Tous statuts</option>
                <option value="pending">En attente</option>
                <option value="preparing">Préparé</option>
                <option value="ready">Prêt</option>
                <option value="partially_dispensed">Partiellement délivré</option>
                <option value="dispensed">Délivré</option>
                <option value="cancelled">Annulé</option>
              </select>
            </div>
          </div>
          <div className="pharmacy-table-wrap">
            <table className="pharmacy-table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Médecin</th>
                  <th>Date</th>
                  <th>Médicaments</th>
                  <th>Qté</th>
                  <th>Statut</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.length === 0 && (
                  <tr>
                    <td colSpan={7} className="pharmacy-empty">Aucune ordonnance pour ce filtre.</td>
                  </tr>
                )}
                {filteredOrders.map((order) => (
                  <tr key={order.id}>
                    <td><strong>{order.patient_name}</strong></td>
                    <td>{order.doctor_name || '—'}</td>
                    <td>{formatDateTime(order.created_at)}</td>
                    <td>{order.medications || '—'}</td>
                    <td>{order.items?.[0]?.quantity ?? '—'}</td>
                    <td><Badge status={order.status} /></td>
                    <td>
                      <div className="pharmacy-actions">
                        <button type="button" className="pharmacy-btn pharmacy-btn--ghost" onClick={() => setSelectedOrder(order)}>
                          Détails
                        </button>
                        {order.status === 'pending' && (
                          <button type="button" className="pharmacy-btn pharmacy-btn--secondary" disabled={busy} onClick={() => updateStatus(order, 'preparing')}>
                            Préparer
                          </button>
                        )}
                        {['pending', 'preparing', 'ready', 'partially_dispensed'].includes(order.status) && (
                          <>
                            <button type="button" className="pharmacy-btn pharmacy-btn--primary" disabled={busy} onClick={() => updateStatus(order, 'dispensed')}>
                              Délivrer
                            </button>
                            <button type="button" className="pharmacy-btn pharmacy-btn--ghost" disabled={busy} onClick={() => updateStatus(order, 'partially_dispensed')}>
                              Partiel
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === 'stock' && (
        <>
          <section id="pharmacy-stock" className="pharmacy-panel">
            <div className="pharmacy-panel-header">
              <h2>{editingStock ? 'Mettre à jour le stock' : 'Ajouter / mettre à jour'}</h2>
              {editingStock && (
                <button type="button" className="pharmacy-btn pharmacy-btn--secondary" onClick={() => { setEditingStock(null); setStockForm(EMPTY_STOCK_FORM); }}>
                  Annuler édition
                </button>
              )}
            </div>
            <form onSubmit={saveStock}>
              <div className="pharmacy-form-grid">
                <label>
                  Médicament
                  <input required value={stockForm.medication_name} onChange={(e) => setStockForm({ ...stockForm, medication_name: e.target.value })} />
                </label>
                <label>
                  SKU
                  <input required value={stockForm.sku} onChange={(e) => setStockForm({ ...stockForm, sku: e.target.value })} disabled={Boolean(editingStock)} />
                </label>
                <label>
                  Quantité
                  <input type="number" min={0} value={stockForm.quantity} onChange={(e) => setStockForm({ ...stockForm, quantity: e.target.value })} />
                </label>
                <label>
                  Seuil alerte
                  <input type="number" min={0} value={stockForm.reorder_level} onChange={(e) => setStockForm({ ...stockForm, reorder_level: e.target.value })} />
                </label>
                <label>
                  Prix unitaire (GNF)
                  <input type="number" min={0} value={stockForm.unit_price_gnf} onChange={(e) => setStockForm({ ...stockForm, unit_price_gnf: e.target.value })} />
                </label>
                <label>
                  N° lot
                  <input value={stockForm.batch_number} onChange={(e) => setStockForm({ ...stockForm, batch_number: e.target.value })} placeholder="LOT-2026-001" />
                </label>
                <label>
                  Date péremption
                  <input type="date" value={stockForm.expiry_date} onChange={(e) => setStockForm({ ...stockForm, expiry_date: e.target.value })} />
                </label>
                <label>
                  Fournisseur
                  <input value={stockForm.supplier} onChange={(e) => setStockForm({ ...stockForm, supplier: e.target.value })} placeholder="Pharma Guinée" />
                </label>
              </div>
              <button type="submit" className="pharmacy-btn pharmacy-btn--primary" disabled={busy}>
                {editingStock ? 'Enregistrer les modifications' : 'Ajouter / mettre à jour'}
              </button>
            </form>
          </section>

          <section className="pharmacy-panel">
            <div className="pharmacy-panel-header">
              <h2>Entrée / sortie stock</h2>
            </div>
            <form onSubmit={submitStockEntry}>
              <div className="pharmacy-form-grid">
                <label>
                  Article
                  <select
                    required
                    value={stockAdjust.item_id}
                    onChange={(e) => setStockAdjust({ ...stockAdjust, item_id: e.target.value })}
                  >
                    <option value="">Choisir</option>
                    {stock.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.medication_name} — Qté {item.quantity}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Quantité (+ entrée / − sortie)
                  <input
                    type="number"
                    value={stockAdjust.delta}
                    onChange={(e) => setStockAdjust({ ...stockAdjust, delta: Number(e.target.value) })}
                  />
                </label>
                <label>
                  Motif
                  <input
                    value={stockAdjust.reason}
                    onChange={(e) => setStockAdjust({ ...stockAdjust, reason: e.target.value })}
                  />
                </label>
              </div>
              <button type="submit" className="pharmacy-btn pharmacy-btn--primary" disabled={busy}>
                Enregistrer mouvement
              </button>
            </form>
          </section>

          <section className="pharmacy-panel">
            <div className="pharmacy-panel-header">
              <h2>Inventaire</h2>
              <div className="pharmacy-toolbar">
                <input type="search" placeholder="Rechercher médicament, SKU, lot…" value={stockSearch} onChange={(e) => setStockSearch(e.target.value)} />
              </div>
            </div>
            <div className="pharmacy-table-wrap">
              <table className="pharmacy-table">
                <thead>
                  <tr>
                    <th>Médicament</th>
                    <th>SKU</th>
                    <th>Qté</th>
                    <th>Seuil</th>
                    <th>Péremption</th>
                    <th>Lot</th>
                    <th>Fournisseur</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStock.length === 0 && (
                    <tr><td colSpan={8} className="pharmacy-empty">Aucun article en stock.</td></tr>
                  )}
                  {filteredStock.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.medication_name}</strong>
                        {item.out_of_stock && <span className="pharmacy-badge pharmacy-badge--danger"> Rupture</span>}
                        {item.low_stock && !item.out_of_stock && <span className="pharmacy-badge pharmacy-badge--warning"> Stock bas</span>}
                      </td>
                      <td>{item.sku}</td>
                      <td>{item.quantity}</td>
                      <td>{item.reorder_level}</td>
                      <td>{formatDate(item.expiry_date)}</td>
                      <td>{item.batch_number || '—'}</td>
                      <td>{item.supplier || '—'}</td>
                      <td>
                        <button type="button" className="pharmacy-btn pharmacy-btn--ghost" onClick={() => startEditStock(item)}>
                          Modifier
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {tab === 'sale' && (
        <section className="pharmacy-panel">
          <h2>Vente directe (comptoir)</h2>
          <p className="clinical-stat-hint">Déduit automatiquement le stock pharmacie et enregistre le mouvement.</p>
          <form onSubmit={submitDirectSale}>
            <div className="pharmacy-form-grid">
              <label>
                Médicament
                <select
                  required
                  value={saleForm.item_id}
                  onChange={(e) => setSaleForm({ ...saleForm, item_id: e.target.value })}
                >
                  <option value="">Choisir</option>
                  {stock.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.medication_name} — {item.quantity} en stock · {formatGNF(item.unit_price_gnf)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Quantité
                <input
                  type="number"
                  min={1}
                  required
                  value={saleForm.quantity}
                  onChange={(e) => setSaleForm({ ...saleForm, quantity: Number(e.target.value) })}
                />
              </label>
              <label>
                Patient / client (optionnel)
                <input
                  value={saleForm.patient_name}
                  onChange={(e) => setSaleForm({ ...saleForm, patient_name: e.target.value })}
                  placeholder="Nom du client"
                />
              </label>
            </div>
            <button type="submit" className="pharmacy-btn pharmacy-btn--primary" disabled={busy}>
              Valider la vente
            </button>
          </form>
        </section>
      )}

      {tab === 'alerts' && (
        <section className="pharmacy-panel">
          <h2>Alertes stock</h2>
          <div className="pharmacy-alert-grid">
            <div className="pharmacy-alert-card pharmacy-alert-card--danger">
              <h3>Rupture de stock ({alerts.out.length})</h3>
              <ul>
                {alerts.out.length === 0 && <li>Aucune rupture.</li>}
                {alerts.out.map((i) => <li key={i.id}>{i.medication_name} ({i.sku})</li>)}
              </ul>
            </div>
            <div className="pharmacy-alert-card pharmacy-alert-card--warning">
              <h3>Stock bas ({alerts.low.length})</h3>
              <ul>
                {alerts.low.length === 0 && <li>Tous les seuils OK.</li>}
                {alerts.low.map((i) => <li key={i.id}>{i.medication_name} — {i.quantity} / seuil {i.reorder_level}</li>)}
              </ul>
            </div>
            <div className="pharmacy-alert-card pharmacy-alert-card--warning">
              <h3>Expire sous 30 j ({alerts.expiring.length})</h3>
              <ul>
                {alerts.expiring.length === 0 && <li>Aucune péremption proche.</li>}
                {alerts.expiring.map((i) => <li key={i.id}>{i.medication_name} — {formatDate(i.expiry_date)} (J-{i.days})</li>)}
              </ul>
            </div>
            <div className="pharmacy-alert-card pharmacy-alert-card--danger">
              <h3>Périmés ({alerts.expired.length})</h3>
              <ul>
                {alerts.expired.length === 0 && <li>Aucun lot périmé.</li>}
                {alerts.expired.map((i) => <li key={i.id}>{i.medication_name} — {formatDate(i.expiry_date)}</li>)}
              </ul>
            </div>
          </div>
        </section>
      )}

      {tab === 'history' && (
        <section className="pharmacy-panel">
          <h2>Mouvements / historique délivrance</h2>
          <div className="pharmacy-table-wrap">
            <table className="pharmacy-table">
              <thead>
                <tr>
                  <th>Date / heure</th>
                  <th>Pharmacien</th>
                  <th>Patient</th>
                  <th>Médicament</th>
                  <th>Qté</th>
                  <th>Ordonnance</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {historyRows.length === 0 && (
                  <tr><td colSpan={7} className="pharmacy-empty">Aucun mouvement enregistré.</td></tr>
                )}
                {historyRows.map((row) => (
                  <tr key={row.id}>
                    <td>{formatDateTime(row.at)}</td>
                    <td>{row.pharmacist}</td>
                    <td>{row.patient_name}</td>
                    <td>{row.medicine}</td>
                    <td>{row.quantity}</td>
                    <td>#{row.order_id}</td>
                    <td>{row.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {tab === 'doctor' && (
        <>
          <section className="pharmacy-panel">
            <h2>Livraison depuis le stock médecin</h2>
            <p className="clinical-stat-hint">Ces médicaments sont délivrés depuis le cabinet médical — ils ne sont pas déduits du stock pharmacie.</p>
            <form onSubmit={saveDoctorDelivery}>
              <div className="pharmacy-form-grid">
                <label>
                  Patient
                  <input required value={doctorForm.patient_name} onChange={(e) => setDoctorForm({ ...doctorForm, patient_name: e.target.value })} />
                </label>
                <label>
                  Médicament
                  <input required value={doctorForm.medicine_name} onChange={(e) => setDoctorForm({ ...doctorForm, medicine_name: e.target.value })} />
                </label>
                <label>
                  Quantité
                  <input type="number" min={1} required value={doctorForm.quantity} onChange={(e) => setDoctorForm({ ...doctorForm, quantity: e.target.value })} />
                </label>
                <label>
                  Médecin
                  <input required value={doctorForm.doctor_name} onChange={(e) => setDoctorForm({ ...doctorForm, doctor_name: e.target.value })} />
                </label>
                <label>
                  Motif / note
                  <input value={doctorForm.reason} onChange={(e) => setDoctorForm({ ...doctorForm, reason: e.target.value })} />
                </label>
              </div>
              <button type="submit" className="pharmacy-btn pharmacy-btn--primary" disabled={busy}>
                Enregistrer — stock médecin
              </button>
            </form>
          </section>
          <section className="pharmacy-panel">
            <h2>Historique livraisons cabinet médecin</h2>
            <div className="pharmacy-table-wrap">
              <table className="pharmacy-table">
                <thead>
                  <tr>
                    <th>Date / heure</th>
                    <th>Patient</th>
                    <th>Médicament</th>
                    <th>Qté</th>
                    <th>Médecin</th>
                    <th>Note</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {doctorDeliveries.length === 0 && (
                    <tr><td colSpan={7} className="pharmacy-empty">Aucune livraison enregistrée.</td></tr>
                  )}
                  {doctorDeliveries.map((row) => (
                    <tr key={row.id}>
                      <td>{formatDateTime(row.delivered_at)}</td>
                      <td>{row.patient_name}</td>
                      <td>{row.medicine_name}</td>
                      <td>{row.quantity}</td>
                      <td>{row.doctor_name}</td>
                      <td>{row.reason || '—'}</td>
                      <td><span className="pharmacy-badge pharmacy-badge--warning">Stock médecin</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {tab === 'report' && (
        <section className="pharmacy-panel">
          <div className="pharmacy-panel-header">
            <h2>Rapport mensuel pharmacie</h2>
            <input type="month" value={reportMonth} onChange={(e) => setReportMonth(e.target.value)} />
          </div>
          {pharmacyReport && (
            <>
              <p>
                {pharmacyReport.total_orders ?? pharmacyReport.dispensed_count ?? '—'} délivrances ·
                Recettes {formatGNF(pharmacyReport.total_revenue_gnf || pharmacyReport.revenue_gnf || 0)}
              </p>
              <ul className="clinical-list">
                {(pharmacyReport.register_entries || pharmacyReport.entries || []).slice(0, 50).map((row, idx) => (
                  <li key={row.id || idx}>
                    <strong>{row.patient_name || row.patient?.first_name}</strong>
                    {' — '}{row.medications || row.medicine_name || '—'}
                    {row.amount_gnf != null && <> · {formatGNF(row.amount_gnf)}</>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}

      {selectedOrder && (
        <div className="pharmacy-modal-backdrop" role="presentation" onClick={() => setSelectedOrder(null)}>
          <div className="pharmacy-modal" role="dialog" aria-labelledby="pharmacy-order-title" onClick={(e) => e.stopPropagation()}>
            <h2 id="pharmacy-order-title">Ordonnance #{selectedOrder.id}</h2>
            <ul className="pharmacy-detail-list">
              <li><strong>Patient :</strong> {selectedOrder.patient_name}</li>
              <li><strong>Médecin :</strong> {selectedOrder.doctor_name || '—'}</li>
              <li><strong>Date :</strong> {formatDateTime(selectedOrder.created_at)}</li>
              <li><strong>Statut :</strong> <Badge status={selectedOrder.status} /></li>
              {selectedOrder.dispensed_at && (
                <li><strong>Délivré le :</strong> {formatDateTime(selectedOrder.dispensed_at)}</li>
              )}
              {selectedOrder.prepared_by && (
                <li><strong>Traité par :</strong> {selectedOrder.prepared_by}</li>
              )}
            </ul>
            <h3>Médicaments prescrits</h3>
            {selectedOrder.items?.length ? (
              <ul className="pharmacy-med-list">
                {selectedOrder.items.map((item, idx) => (
                  <li key={`${item.medication_name}-${idx}`}>
                    <strong>{item.medication_name}</strong> — {item.dosage}, {item.frequency}
                    {item.quantity != null && ` · Qté ${item.quantity}`}
                    {item.duration_days != null && ` · ${item.duration_days} j`}
                  </li>
                ))}
              </ul>
            ) : (
              <p>{selectedOrder.medications || '—'}</p>
            )}
            <div className="pharmacy-actions" style={{ marginTop: '1rem' }}>
              {selectedOrder.status === 'pending' && (
                <button type="button" className="pharmacy-btn pharmacy-btn--secondary" disabled={busy} onClick={() => updateStatus(selectedOrder, 'preparing')}>
                  Préparer
                </button>
              )}
              {['pending', 'preparing', 'ready', 'partially_dispensed'].includes(selectedOrder.status) && (
                <>
                  <button type="button" className="pharmacy-btn pharmacy-btn--primary" disabled={busy} onClick={() => updateStatus(selectedOrder, 'dispensed')}>
                    Délivrer
                  </button>
                  <button type="button" className="pharmacy-btn pharmacy-btn--ghost" disabled={busy} onClick={() => updateStatus(selectedOrder, 'partially_dispensed')}>
                    Livraison partielle
                  </button>
                </>
              )}
              <button type="button" className="pharmacy-btn pharmacy-btn--secondary" onClick={() => setSelectedOrder(null)}>
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
