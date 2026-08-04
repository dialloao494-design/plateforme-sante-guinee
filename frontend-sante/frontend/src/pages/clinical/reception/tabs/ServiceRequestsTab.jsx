import {
  PATIENT_REQUIRED_NOTICE,
  SERVICE_REQUEST_CATEGORIES,
  SERVICE_REQUEST_CHARGE_TYPES,
  SERVICE_REQUEST_STATUSES,
} from '../constants.js';
import PatientContextPanel from '../components/PatientContextPanel.jsx';
import { FormNotice, ReadOnlyDisplay } from '../components/FormPrimitives.jsx';
import { formatGNF } from '../../../../utils/appointmentPresentation.js';
import { formatDateTime, serviceRequestCategoryLabel, serviceRequestStatusLabel } from '../utils.js';

export default function ServiceRequestsTab({
  patientPayerLabel,
  applyServiceRequestToBilling,
  chooseServiceRequest,
  deleteServiceRequest,
  editingServiceRequestId,
  filteredServicePrestations,
  filteredServiceRequestImaging,
  filteredServiceRequestLabTests,
  filteredServiceRequestSpecialties,
  filteredSurgicalActs,
  lastCreatedServiceRequest,
  loadServiceRequests,
  loading,
  loadingServiceRequests,
  resetServiceRequestForm,
  saveServiceRequest,
  selectedPatient,
  serviceRequestExamSearchQ,
  serviceRequestForm,
  serviceRequestSearchQ,
  serviceRequestStatusFilter,
  serviceRequests,
  setServiceRequestExamSearchQ,
  setServiceRequestForm,
  setServiceRequestSearchQ,
  setServiceRequestStatusFilter,
  startEditServiceRequest,
}) {
  return (
        <section className="reception-his-panel">
          <PatientContextPanel selectedPatient={selectedPatient} patientPayerLabel={patientPayerLabel} />
          <div className="clinical-card reception-his-form-sheet">
            <h2>Demandes de service</h2>
            <div className="reception-his-search-inline reception-his-service-request-filters">
              <input
                type="search"
                placeholder="Rechercher une demande (service, n°…)"
                value={serviceRequestSearchQ}
                onChange={(e) => setServiceRequestSearchQ(e.target.value)}
              />
              <select value={serviceRequestStatusFilter} onChange={(e) => setServiceRequestStatusFilter(e.target.value)}>
                <option value="">Tous les statuts</option>
                {SERVICE_REQUEST_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
              <button type="button" className="clinical-btn clinical-btn--secondary" onClick={loadServiceRequests}>Actualiser</button>
            </div>

            <form className="reception-his-service-request-form" onSubmit={saveServiceRequest}>
              <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>
              <div className="clinical-form-row">
                <label>
                  Catégorie
                  <select
                    value={serviceRequestForm.service_category}
                    onChange={(e) => {
                      const category = e.target.value;
                      setServiceRequestForm((p) => ({
                        ...p,
                        service_category: category,
                        service_name: '',
                        catalog_code: '',
                        charge_type: SERVICE_REQUEST_CHARGE_TYPES[category] || 'other',
                        unit_price_gnf: 0,
                      }));
                      setServiceRequestExamSearchQ('');
                    }}
                    disabled={!selectedPatient}
                  >
                    {SERVICE_REQUEST_CATEGORIES.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Service / examen sélectionné
                  <ReadOnlyDisplay value={serviceRequestForm.service_name} />
                </label>
                <label>
                  Statut
                  <select
                    value={serviceRequestForm.status}
                    onChange={(e) => setServiceRequestForm((p) => ({ ...p, status: e.target.value }))}
                    disabled={!selectedPatient}
                  >
                    {SERVICE_REQUEST_STATUSES.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </label>
              </div>

              {serviceRequestForm.service_category === 'laboratory' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Tous les examens de laboratoire</legend>
                  <label>
                    Rechercher un examen
                    <input
                      type="search"
                      value={serviceRequestExamSearchQ}
                      onChange={(e) => setServiceRequestExamSearchQ(e.target.value)}
                      placeholder="Nom ou code analyse…"
                      disabled={!selectedPatient}
                    />
                  </label>
                  <ul className="reception-his-lab-search-results">
                    {filteredServiceRequestLabTests.map((test) => (
                      <li key={test.code}>
                        <button
                          type="button"
                          onClick={() => chooseServiceRequest('laboratory', `${test.name} (${test.code})`, {
                            catalog_code: test.code,
                            charge_type: 'laboratory',
                            unit_price_gnf: test.price_gnf || 0,
                          })}
                          disabled={!selectedPatient}
                        >
                          {test.name} ({test.code})
                          {test.category ? ` · ${test.category}` : ''}
                          {` · ${formatGNF(test.price_gnf || 0)}`}
                        </button>
                      </li>
                    ))}
                  </ul>
                  {filteredServiceRequestLabTests.length === 0 && (
                    <p className="clinical-hint">Aucun examen trouvé.</p>
                  )}
                </fieldset>
              )}

              {serviceRequestForm.service_category === 'imaging' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Tous les examens d&apos;imagerie</legend>
                  <label>
                    Rechercher un examen
                    <input
                      type="search"
                      value={serviceRequestExamSearchQ}
                      onChange={(e) => setServiceRequestExamSearchQ(e.target.value)}
                      placeholder="Nom examen imagerie…"
                      disabled={!selectedPatient}
                    />
                  </label>
                  <div className="reception-his-service-options">
                    {filteredServiceRequestImaging.map((exam) => (
                      <button
                        key={exam.code}
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => chooseServiceRequest('imaging', exam.label, {
                          catalog_code: exam.code,
                          charge_type: 'imaging',
                          unit_price_gnf: exam.price_gnf || 0,
                        })}
                        disabled={!selectedPatient}
                      >
                        {exam.label} · {formatGNF(exam.price_gnf || 0)}
                      </button>
                    ))}
                  </div>
                  {filteredServiceRequestImaging.length === 0 && (
                    <p className="clinical-hint">Aucun examen d&apos;imagerie trouvé.</p>
                  )}
                </fieldset>
              )}

              {serviceRequestForm.service_category === 'consultation' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Spécialités (tarifs fiche AASMA)</legend>
                  <label>
                    Rechercher une spécialité
                    <input
                      type="search"
                      value={serviceRequestExamSearchQ}
                      onChange={(e) => setServiceRequestExamSearchQ(e.target.value)}
                      placeholder="Médecine, Chirurgie, Pédiatrie…"
                      disabled={!selectedPatient}
                    />
                  </label>
                  <div className="reception-his-service-options">
                    {filteredServiceRequestSpecialties.map((spec) => (
                      <button
                        key={spec.code}
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => chooseServiceRequest(
                          'consultation',
                          `Consultation spécialisée — ${spec.label}`,
                          {
                            catalog_code: spec.code,
                            charge_type: 'consultation',
                            unit_price_gnf: spec.price_gnf || 0,
                          }
                        )}
                        disabled={!selectedPatient}
                      >
                        {spec.label}
                        {' · spé. '}
                        {formatGNF(spec.price_gnf || 0)}
                        {' · urg. '}
                        {formatGNF(spec.emergency_price_gnf || 0)}
                      </button>
                    ))}
                  </div>
                  {filteredServiceRequestSpecialties.length === 0 && (
                    <p className="clinical-hint">Aucune spécialité trouvée.</p>
                  )}
                </fieldset>
              )}

              {serviceRequestForm.service_category === 'surgery' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Actes chirurgicaux</legend>
                  <label>
                    Rechercher un acte
                    <input
                      type="search"
                      value={serviceRequestExamSearchQ}
                      onChange={(e) => setServiceRequestExamSearchQ(e.target.value)}
                      placeholder="Suture, césarienne, hernie…"
                      disabled={!selectedPatient}
                    />
                  </label>
                  <div className="reception-his-service-options">
                    {filteredSurgicalActs.map((act) => (
                      <button
                        key={act.code}
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => chooseServiceRequest('surgery', act.label, {
                          catalog_code: act.code,
                          charge_type: 'procedure',
                          unit_price_gnf: act.price_gnf || 0,
                        })}
                        disabled={!selectedPatient}
                      >
                        {act.label} · {formatGNF(act.price_gnf || 0)}
                      </button>
                    ))}
                  </div>
                  {filteredSurgicalActs.length === 0 && (
                    <p className="clinical-hint">Aucun acte chirurgical trouvé.</p>
                  )}
                </fieldset>
              )}

              {serviceRequestForm.service_category === 'service' && (
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Services / Prestations</legend>
                  <div className="reception-his-service-options">
                    {filteredServicePrestations.map((svc) => (
                      <button
                        key={svc.code}
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => chooseServiceRequest('service', svc.label, {
                          catalog_code: svc.code,
                          charge_type: 'procedure',
                          unit_price_gnf: svc.price_gnf || 0,
                        })}
                        disabled={!selectedPatient}
                      >
                        {svc.label} · {formatGNF(svc.price_gnf || 0)}
                      </button>
                    ))}
                  </div>
                </fieldset>
              )}

              {['nursing', 'pharmacy', 'doctor', 'other'].includes(serviceRequestForm.service_category) && (
                <label>
                  Service / prestation
                  <input
                    value={serviceRequestForm.service_name}
                    onChange={(e) => setServiceRequestForm((p) => ({
                      ...p,
                      service_name: e.target.value,
                      charge_type: SERVICE_REQUEST_CHARGE_TYPES[p.service_category] || 'other',
                    }))}
                    disabled={!selectedPatient}
                    required
                  />
                </label>
              )}
              {serviceRequestForm.service_name ? (
                <p className="clinical-hint">
                  Sélection enregistrée : <strong>{serviceRequestForm.service_name}</strong>
                  {' · '}
                  {formatGNF(serviceRequestForm.unit_price_gnf || 0)}
                  {' — cliquez « Créer la demande » pour la conserver.'}
                </p>
              ) : null}
              <div className="reception-his-form-actions">
                <button type="submit" className="clinical-btn" disabled={!selectedPatient || loading || !serviceRequestForm.service_name.trim()}>
                  {editingServiceRequestId ? 'Mettre à jour la demande' : 'Créer la demande'}
                </button>
                {editingServiceRequestId && (
                  <button type="button" className="clinical-btn clinical-btn--secondary" onClick={resetServiceRequestForm}>Annuler</button>
                )}
                {lastCreatedServiceRequest?.request_number && (
                  <button
                    type="button"
                    className="clinical-btn clinical-btn--secondary"
                    onClick={() => applyServiceRequestToBilling(lastCreatedServiceRequest)}
                  >
                    Facturer {lastCreatedServiceRequest.request_number}
                  </button>
                )}
              </div>
            </form>

            {loadingServiceRequests ? (
              <FormNotice>Chargement des demandes…</FormNotice>
            ) : serviceRequests.length === 0 ? (
              <FormNotice>Aucune demande de service{selectedPatient ? ' pour ce patient' : ''}.</FormNotice>
            ) : (
              <table className="reception-his-billing-lines">
                <thead>
                  <tr>
                    <th>N° demande</th>
                    <th>Patient</th>
                    <th>Catégorie</th>
                    <th>Service</th>
                    <th>Statut</th>
                    <th>Créée le</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {serviceRequests.map((row) => (
                    <tr key={row.id}>
                      <td>{row.request_number}</td>
                      <td>{row.patient_name || row.patient_id}</td>
                      <td>{serviceRequestCategoryLabel(row.service_category)}</td>
                      <td>{row.service_name}</td>
                      <td>{serviceRequestStatusLabel(row.status)}</td>
                      <td>{formatDateTime(row.created_at)}</td>
                      <td>
                        <div className="reception-his-refund-actions">
                          <button type="button" className="clinical-btn" onClick={() => applyServiceRequestToBilling(row)}>Facturer</button>
                          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => startEditServiceRequest(row)}>Modifier</button>
                          <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => deleteServiceRequest(row.id)}>Supprimer</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
  );
}
