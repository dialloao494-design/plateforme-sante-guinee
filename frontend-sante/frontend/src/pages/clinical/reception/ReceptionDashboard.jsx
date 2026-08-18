import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import PatientRegistrationPrint from '../../../components/print/PatientRegistrationPrint.jsx';
import '../clinical.css';
import { TABS } from './constants.js';
import { useReceptionDashboard } from './hooks/useReceptionDashboard.jsx';
import AdmissionTab from './tabs/AdmissionTab.jsx';
import BillingTab from './tabs/BillingTab.jsx';
import DashboardTab from './tabs/DashboardTab.jsx';
import RefundTab from './tabs/RefundTab.jsx';
import RegisterTab from './tabs/RegisterTab.jsx';
import ServiceRequestsTab from './tabs/ServiceRequestsTab.jsx';
import PatientSafetyStrip from './components/PatientSafetyStrip.jsx';
import { readReceptionRouteState } from './routeState.js';

export default function ReceptionDashboard() {
  const [searchParams] = useSearchParams();
  const routeState = readReceptionRouteState(searchParams);
  const hydratedPatientId = useRef('');
  const dashboard = useReceptionDashboard();
  const {
    user,
    tab,
    setTab,
    searchRef,
    regPrintRef,
    message,
    error,
    searchQ,
    setSearchQ,
    searchResults,
    searching,
    runPatientSearch,
    selectedPatient,
    clearPatient,
    selectPatient,
    registeredPatient,
    registrationPrintForm,
    resolveRelationship,
  } = dashboard;

  const openPatient = async (patient, targetTab = 'admission') => {
    await selectPatient(patient, { silent: true, targetTab });
    hydratedPatientId.current = String(patient.id);
  };

  const closePatient = () => {
    clearPatient();
    hydratedPatientId.current = '';
  };

  useEffect(() => {
    if (!routeState.patientId || selectedPatient?.id || hydratedPatientId.current === routeState.patientId) return;
    hydratedPatientId.current = routeState.patientId;
    void selectPatient({ id: routeState.patientId }, { silent: true });
  }, [routeState.patientId, selectedPatient?.id, selectPatient]);

  return (
    <div className="clinical-page reception-his" data-testid="reception-dashboard">
      <header className="reception-his-header">
        <div>
          <h1>Tableau de bord — Réception</h1>
          <p className="clinical-lead">Enregistrement patient · Admission · Facturation · Remboursement</p>
          <p className="reception-his-session">Session : {user?.full_name || user?.email || 'Utilisateur'}</p>
        </div>
        <div className="reception-his-search">
          <label htmlFor="patient-search">Recherche patient</label>
          <div className="reception-his-search-inline">
            <input
              id="patient-search"
              ref={searchRef}
              type="search"
              placeholder="N° dossier, nom, téléphone, QR…"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  runPatientSearch();
                }
              }}
              autoComplete="off"
            />
            <button
              type="button"
              className="clinical-btn"
              onClick={() => runPatientSearch()}
              disabled={searching || !searchQ.trim()}
            >
              {searching ? '…' : 'Rechercher'}
            </button>
          </div>
          {searching && <span className="reception-his-search-hint">Recherche…</span>}
          {searchResults.length > 0 && (
            <ul className="reception-his-search-results">
              {searchResults.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    onClick={() => openPatient(p)}
                  >
                    <strong>{p.last_name} {p.first_name}</strong>
                    <span>N° dossier {p.patient_number || 'Non attribué'} · {p.phone || 'Téléphone non renseigné'}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>

      <PatientSafetyStrip patient={selectedPatient} onClose={closePatient} />

      {message && <p className="clinical-message clinical-message--ok" role="status" aria-live="polite">{message}</p>}
      {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}

      <nav className="reception-his-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            data-testid={`reception-tab-${t.id}`}
            className={tab === t.id ? 'active' : ''}
            onClick={() => setTab(t.id)}
            aria-current={tab === t.id ? 'page' : undefined}
          >
            {t.label}<kbd>{t.shortcut}</kbd>
          </button>
        ))}
      </nav>

      {tab === 'dashboard' && <DashboardTab {...dashboard} openPatient={openPatient} />}
      {tab === 'register' && <RegisterTab {...dashboard} />}
      {tab === 'admission' && <AdmissionTab {...dashboard} />}
      {tab === 'billing' && <BillingTab {...dashboard} />}
      {tab === 'refund' && <RefundTab {...dashboard} />}
      {tab === 'service_requests' && <ServiceRequestsTab {...dashboard} />}

      {registeredPatient && registrationPrintForm && (
        <div className="reception-his-registration-print" ref={regPrintRef}>
          <PatientRegistrationPrint
            patient={{
              ...registeredPatient,
              emergency_relationship: resolveRelationship(registrationPrintForm),
            }}
            form={registrationPrintForm}
            printedBy={(user?.full_name || user?.email || '').toUpperCase()}
          />
        </div>
      )}
    </div>
  );
}
