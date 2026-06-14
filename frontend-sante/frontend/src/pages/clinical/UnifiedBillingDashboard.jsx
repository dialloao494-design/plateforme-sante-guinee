import { useCallback, useEffect, useState } from 'react';

import clinicalApi from '../../services/clinicalApi';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';

import './clinical.css';

function formatGNF(n) {
  return `${Number(n || 0).toLocaleString('fr-GN')} GNF`;
}

export default function UnifiedBillingDashboard() {
  const [invoices, setInvoices] = useState([]);
  const [patientId, setPatientId] = useState('');
  const [visitId, setVisitId] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await clinicalApi.listInvoices();
      setInvoices(data || []);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Facturation indisponible');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const generate = async () => {
    if (!patientId) return;
    try {
      await clinicalApi.generateInvoice({
        patient_id: Number(patientId),
        visit_id: visitId ? Number(visitId) : undefined,
      });
      setMessage('Facture unifiée générée');
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Génération impossible');
    }
  };

  const pay = async (invoiceId) => {
    try {
      await clinicalApi.payInvoice(invoiceId, { payment_method: paymentMethod });
      setMessage('Paiement enregistré');
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Paiement impossible');
    }
  };

  const downloadPdf = async (invoiceId, invoiceNumber) => {
    try {
      await clinicalApi.downloadInvoicePdf(invoiceId, `${invoiceNumber}.pdf`);
      setMessage(`PDF ${invoiceNumber} téléchargé`);
    } catch (err) {
      setError(err?.response?.data?.detail || 'PDF indisponible');
    }
  };

  const pending = invoices.filter((i) => i.status !== 'paid');
  const stats = [
    { label: 'Factures', value: invoices.length, hint: 'Total émis' },
    { label: 'En attente', value: pending.length, hint: formatGNF(pending.reduce((s, i) => s + (i.total_amount_gnf - i.paid_amount_gnf), 0)), variant: 'warning' },
    { label: 'Payées', value: invoices.filter((i) => i.status === 'paid').length, hint: 'Clôturées', variant: 'success' },
  ];

  return (
    <div className="clinical-page">
      <header className="clinical-header">
        <h1>Facturation unifiée</h1>
        <p>Agrégation consultation, labo, radio, pharmacie et hospitalisation.</p>
      </header>
      {error && <div className="clinical-alert clinical-alert--error">{error}</div>}
      {message && <div className="clinical-alert clinical-alert--success">{message}</div>}
      <ClinicalStatGrid stats={stats} />

      <section className="clinical-panel">
        <h2>Générer une facture</h2>
        <div className="clinical-form" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <label>
            ID patient
            <input value={patientId} onChange={(e) => setPatientId(e.target.value)} />
          </label>
          <label>
            ID visite (optionnel)
            <input value={visitId} onChange={(e) => setVisitId(e.target.value)} />
          </label>
          <button type="button" className="clinical-btn" onClick={generate}>Générer</button>
        </div>
      </section>

      <section className="clinical-panel">
        <h2>Factures</h2>
        <div className="clinical-form" style={{ marginBottom: '1rem' }}>
          <label>
            Mode de paiement
            <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
              <option value="cash">Espèces</option>
              <option value="orange_money">Orange Money</option>
              <option value="mobile_money">Mobile Money</option>
            </select>
          </label>
        </div>
        <ul className="clinical-queue">
          {invoices.length === 0 && <li>Aucune facture.</li>}
          {invoices.map((inv) => (
            <li key={inv.id}>
              <div>
                <strong>{inv.invoice_number}</strong> — {inv.patient_name}
                <span className="clinical-badge">{inv.status}</span>
                <div>{formatGNF(inv.total_amount_gnf)} · payé {formatGNF(inv.paid_amount_gnf)}</div>
                <ul className="clinical-list">
                  {(inv.items || []).map((item) => (
                    <li key={item.id}>{item.description}: {formatGNF(item.amount_gnf)}</li>
                  ))}
                </ul>
              </div>
              <div className="clinical-actions">
                {inv.status !== 'paid' && (
                  <button type="button" className="clinical-btn" onClick={() => pay(inv.id)}>Encaisser</button>
                )}
                <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => downloadPdf(inv.id, inv.invoice_number)}>PDF</button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
