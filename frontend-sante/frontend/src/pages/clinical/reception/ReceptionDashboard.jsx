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

export default function ReceptionDashboard() {
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

  return (
    <div className="clinical-page reception-his">
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
                    onClick={() => selectPatient(p)}
                  >
                    <strong>{p.last_name} {p.first_name}</strong>
                    <span>ID patient {p.patient_number || '—'} · {p.phone || '—'}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>

      {selectedPatient && (
        <div className="reception-his-selected">
          Patient actif : <strong>{selectedPatient.last_name} {selectedPatient.first_name}</strong> · ID patient{' '}
          <strong>{selectedPatient.patient_number || '—'}</strong>
          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={clearPatient}>Effacer</button>
        </div>
      )}

      {message && <p className="clinical-message clinical-message--ok">{message}</p>}
      {error && <p className="clinical-message clinical-message--err">{error}</p>}

      <nav className="reception-his-tabs">
        {TABS.map((t) => (
          <button key={t.id} type="button" className={tab === t.id ? 'active' : ''} onClick={() => setTab(t.id)}>
            {t.label}<kbd>{t.shortcut}</kbd>
          </button>
        ))}
      </nav>

      {tab === 'dashboard' && <DashboardTab {...dashboard} />}
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
