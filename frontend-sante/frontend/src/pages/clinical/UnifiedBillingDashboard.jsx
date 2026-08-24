import { useCallback, useEffect, useRef, useState } from 'react';

import clinicalApi from '../../services/clinicalApi';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import PatientPicker from '../../components/PatientPicker.jsx';
import PatientSafetyStrip from '../../components/clinical/PatientSafetyStrip.jsx';
import ClinicalFeedback from '../../components/clinical/ClinicalFeedback.jsx';
import { useClinicalPatientRoute } from '../../hooks/useClinicalPatientRoute.js';
import { formatClinicalDateTime, formatClinicalStatus, formatGNF } from '../../utils/clinicalPresentation.js';

import './clinical.css';
import './billing.css';

export default function UnifiedBillingDashboard() {
  const { patientId: routePatientId, setPatientId: setRoutePatientId } = useClinicalPatientRoute();
  const closingPatientIdRef = useRef('');
  const [invoices, setInvoices] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patientVisits, setPatientVisits] = useState([]);
  const [visitId, setVisitId] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [invoiceView, setInvoiceView] = useState('pending');
  const [busyInvoice, setBusyInvoice] = useState('');
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
    if (!selectedPatient) return;
    try {
      await clinicalApi.generateInvoice({
        patient_id: selectedPatient.id,
        visit_id: visitId ? Number(visitId) : undefined,
      });
      setMessage('Facture unifiée générée');
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Génération impossible');
    }
  };

  const selectPatient = useCallback(async (patient, { updateRoute = true } = {}) => {
    setSelectedPatient(patient);
    setVisitId('');
    setPatientVisits([]);
    if (!patient) {
      if (updateRoute) setRoutePatientId('');
      return;
    }
    closingPatientIdRef.current = '';
    if (updateRoute) setRoutePatientId(patient.id);
    try {
      const response = await clinicalApi.billingPatientVisits(patient.id);
      setPatientVisits(response?.data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Visites du patient indisponibles');
    }
  }, [setRoutePatientId]);

  useEffect(() => {
    if (!routePatientId) return;
    if (closingPatientIdRef.current === routePatientId || String(selectedPatient?.id || '') === routePatientId) return;
    clinicalApi.patientTimeline(routePatientId)
      .then(({ data }) => selectPatient(data?.patient, { updateRoute: false }))
      .catch((err) => setError(err?.response?.data?.detail || 'Patient indisponible'));
  }, [routePatientId, selectPatient, selectedPatient?.id]);

  const closePatient = () => {
    closingPatientIdRef.current = String(selectedPatient?.id || routePatientId || '');
    setSelectedPatient(null);
    setPatientVisits([]);
    setVisitId('');
    setRoutePatientId('');
  };

  const pay = async (invoiceId) => {
    setBusyInvoice(`pay-${invoiceId}`);
    try {
      await clinicalApi.payInvoice(invoiceId, { payment_method: paymentMethod });
      setMessage('Paiement enregistré');
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Paiement impossible');
    } finally {
      setBusyInvoice('');
    }
  };

  const downloadPdf = async (invoiceId, invoiceNumber) => {
    setBusyInvoice(`pdf-${invoiceId}`);
    try {
      await clinicalApi.downloadInvoicePdf(invoiceId, `${invoiceNumber}.pdf`);
      setMessage(`PDF ${invoiceNumber} téléchargé`);
    } catch (err) {
      setError(err?.response?.data?.detail || 'PDF indisponible');
    } finally {
      setBusyInvoice('');
    }
  };

  const pending = invoices.filter((i) => i.status !== 'paid');
  const paid = invoices.filter((i) => i.status === 'paid');
  const visibleInvoices = invoiceView === 'pending' ? pending : paid;
  const stats = [
    { label: 'Factures', value: invoices.length, hint: 'Total émis' },
    { label: 'En attente', value: pending.length, hint: formatGNF(pending.reduce((s, i) => s + (i.total_amount_gnf - i.paid_amount_gnf), 0)), variant: 'warning' },
    { label: 'Payées', value: invoices.filter((i) => i.status === 'paid').length, hint: 'Clôturées', variant: 'success' },
  ];

  return (
    <div className="clinical-page billing-workspace" data-testid="billing-dashboard">
      <header className="clinical-header billing-workspace__header">
        <p className="clinical-eyebrow">Caisse clinique</p>
        <h1>Facturation unifiée</h1>
        <p>Centralisez les actes du patient, encaissez et remettez un justificatif.</p>
      </header>
      <ClinicalFeedback error={error} message={message} />
      <PatientSafetyStrip patient={selectedPatient} onClose={closePatient} contextLabel="Patient actif à la facturation" />
      <ClinicalStatGrid stats={stats} />

      <section className="clinical-panel billing-create-panel" aria-labelledby="billing-create-title">
        <header className="billing-section-heading">
          <div>
            <p>Étape 1</p>
            <h2 id="billing-create-title">Préparer la facture</h2>
          </div>
          <span>Les charges non facturées du dossier seront regroupées.</span>
        </header>
        <div className="clinical-form billing-create-form">
          {!selectedPatient && <PatientPicker search={clinicalApi.billingPatientSearch} onSelect={selectPatient} />}
          {selectedPatient && (
            <>
              <label htmlFor="billing-visit">Visite à facturer</label>
              <select id="billing-visit" name="billing_visit" autoComplete="off" value={visitId} onChange={(e) => setVisitId(e.target.value)}>
                <option value="">Toutes les charges non facturées</option>
                {patientVisits.map((visit) => (
                  <option key={visit.id} value={visit.id}>
                    Visite du {formatClinicalDateTime(visit.started_at)} · {visit.status}
                  </option>
                ))}
              </select>
              <button type="button" className="clinical-btn" data-testid="billing-generate-invoice" onClick={generate}>Générer la facture</button>
            </>
          )}
        </div>
      </section>

      <section className="clinical-panel billing-register" aria-labelledby="billing-register-title">
        <header className="billing-section-heading">
          <div>
            <p>Étape 2</p>
            <h2 id="billing-register-title">Encaisser et remettre le reçu</h2>
          </div>
          <span>{pending.length} facture{pending.length > 1 ? 's' : ''} à encaisser</span>
        </header>
        <div className="billing-register-toolbar">
          <div className="billing-view-tabs" role="tablist" aria-label="Afficher les factures">
            <button type="button" role="tab" aria-selected={invoiceView === 'pending'} onClick={() => setInvoiceView('pending')}>
              À encaisser <span>{pending.length}</span>
            </button>
            <button type="button" role="tab" aria-selected={invoiceView === 'paid'} onClick={() => setInvoiceView('paid')}>
              Payées <span>{paid.length}</span>
            </button>
          </div>
          {invoiceView === 'pending' && (
            <label className="billing-payment-method">
              Mode de paiement
              <select name="payment_method" autoComplete="off" value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}>
                <option value="cash">Espèces</option>
                <option value="orange_money">Orange Money</option>
                <option value="mobile_money">Mobile Money</option>
              </select>
            </label>
          )}
        </div>
        {visibleInvoices.length === 0 ? (
          <p className="billing-empty-state">
            {invoiceView === 'pending' ? 'Aucune facture en attente de paiement.' : 'Aucune facture payée à afficher.'}
          </p>
        ) : <ul className="billing-invoice-list" aria-label={invoiceView === 'pending' ? 'Factures à encaisser' : 'Factures payées'}>
          {visibleInvoices.map((inv) => {
            const remaining = Math.max(0, Number(inv.total_amount_gnf || 0) - Number(inv.paid_amount_gnf || 0));
            return (
            <li key={inv.id} className={`billing-invoice-card billing-invoice-card--${inv.status || 'unknown'}`}>
              <div className="billing-invoice-main">
                <header className="billing-invoice-identity">
                  <div>
                    <span className="billing-invoice-label">Facture</span>
                    <strong translate="no">{inv.invoice_number}</strong>
                  </div>
                  <span className={`clinical-badge billing-status billing-status--${inv.status || 'unknown'}`}>
                    {formatClinicalStatus(inv.status)}
                  </span>
                  <span className="billing-invoice-patient">{inv.patient_name || 'Patient non renseigné'}</span>
                </header>
                <div className="billing-invoice-amounts">
                  <span><small>Total</small><strong>{formatGNF(inv.total_amount_gnf)}</strong></span>
                  <span><small>Payé</small><strong>{formatGNF(inv.paid_amount_gnf)}</strong></span>
                  <span className="billing-invoice-balance"><small>Reste</small><strong>{formatGNF(remaining)}</strong></span>
                </div>
                <ul className="billing-invoice-items" aria-label="Prestations facturées">
                  {(inv.items || []).map((item) => (
                    <li key={item.id}>
                      <span>{item.description}</span>
                      <strong>{formatGNF(item.amount_gnf)}</strong>
                    </li>
                  ))}
                </ul>
              </div>
              <footer className="billing-invoice-actions">
                {inv.status !== 'paid' && (
                  <button type="button" className="clinical-btn" disabled={Boolean(busyInvoice)} onClick={() => pay(inv.id)}>
                    {busyInvoice === `pay-${inv.id}` ? 'Encaissement…' : `Encaisser ${formatGNF(remaining)}`}
                  </button>
                )}
                <button type="button" className="clinical-btn clinical-btn--secondary" disabled={Boolean(busyInvoice)} onClick={() => downloadPdf(inv.id, inv.invoice_number)}>
                  {busyInvoice === `pdf-${inv.id}` ? 'Préparation…' : 'Télécharger la facture'}
                </button>
              </footer>
            </li>
          );})}
        </ul>}
      </section>
    </div>
  );
}
