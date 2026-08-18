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
import '../serviceRequests.css';

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
          <div className="clinical-card reception-his-form-sheet service-request-workspace" data-testid="service-request-workspace">
            <header className="service-request-workspace__header">
              <div>
                <p>Prescription interne</p>
                <h2>Demandes de service</h2>
              </div>
              <span>Créer une demande et suivre sa facturation</span>
            </header>

            <div className="reception-his-service-request-filters" data-testid="service-request-filters" aria-label="Filtres du registre des demandes">
              <label className="service-request-field service-request-field--search">
                <span>Rechercher une demande</span>
                <input
                  type="search"
                  placeholder="Service ou numéro de demande"
                  value={serviceRequestSearchQ}
                  onChange={(e) => setServiceRequestSearchQ(e.target.value)}
                />
              </label>
              <label className="service-request-field">
                <span>Statut du registre</span>
                <select value={serviceRequestStatusFilter} onChange={(e) => setServiceRequestStatusFilter(e.target.value)}>
                  <option value="">Tous les statuts</option>
                  {SERVICE_REQUEST_STATUSES.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </label>
              <button type="button" className="clinical-btn clinical-btn--secondary" onClick={loadServiceRequests}>Actualiser</button>
            </div>

            <form className="reception-his-service-request-form" onSubmit={saveServiceRequest}>
              <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>
              <div className="service-request-setup" data-testid="service-request-setup">
                <label className="service-request-field">
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
                <label className="service-request-field service-request-field--selected">
                  Service / examen sélectionné
                  <ReadOnlyDisplay value={serviceRequestForm.service_name} />
                </label>
                <label className="service-request-field">
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
                <fieldset className="reception-his-nested-fieldset" data-testid="service-request-catalog">
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
                <fieldset className="reception-his-nested-fieldset" data-testid="service-request-catalog">
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
                <fieldset className="reception-his-nested-fieldset" data-testid="service-request-catalog">
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
                <fieldset className="reception-his-nested-fieldset" data-testid="service-request-catalog">
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
                <fieldset className="reception-his-nested-fieldset" data-testid="service-request-catalog">
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
              <section className="service-request-register" aria-labelledby="service-request-register-title">
                <header className="service-request-register__header">
                  <div>
                    <p className="service-request-register__eyebrow">Registre des demandes</p>
                    <h3 id="service-request-register-title">
                      {serviceRequests.length} demande{serviceRequests.length > 1 ? 's' : ''}
                    </h3>
                  </div>
                  <p>Les demandes en attente peuvent être envoyées directement en facturation.</p>
                </header>

                <div className="service-request-list" role="list">
                  {serviceRequests.map((row) => (
                    <article className="service-request-item" key={row.id} role="listitem">
                      <div className="service-request-item__identity">
                        <span className="service-request-item__label">N° demande</span>
                        <strong translate="no">{row.request_number || `DSR-${row.id}`}</strong>
                        <span className={`service-request-status service-request-status--${row.status || 'unknown'}`}>
                          {serviceRequestStatusLabel(row.status)}
                        </span>
                      </div>

                      <div className="service-request-item__patient">
                        <span className="service-request-item__label">Patient</span>
                        <strong>{row.patient_name || `Patient ${row.patient_id}`}</strong>
                        <span>{serviceRequestCategoryLabel(row.service_category)}</span>
                      </div>

                      <div className="service-request-item__service">
                        <span className="service-request-item__label">Service demandé</span>
                        <strong>{row.service_name || 'Service non renseigné'}</strong>
                        {Number(row.unit_price_gnf || 0) > 0 && (
                          <span>{formatGNF(row.unit_price_gnf)}</span>
                        )}
                      </div>

                      <div className="service-request-item__date">
                        <span className="service-request-item__label">Créée le</span>
                        <time dateTime={row.created_at || undefined}>{formatDateTime(row.created_at)}</time>
                      </div>

                      <div className="service-request-item__actions" aria-label={`Actions pour ${row.request_number || `la demande ${row.id}`}`}>
                        <span className="service-request-item__label">Actions</span>
                        <div>
                          <button
                            type="button"
                            className="clinical-btn service-request-action service-request-action--billing"
                            onClick={() => applyServiceRequestToBilling(row)}
                            disabled={loading}
                          >
                            Facturer
                          </button>
                          <button
                            type="button"
                            className="clinical-btn clinical-btn--secondary service-request-action"
                            onClick={() => startEditServiceRequest(row)}
                            disabled={loading}
                          >
                            Modifier
                          </button>
                          <button
                            type="button"
                            className="service-request-action service-request-action--danger"
                            onClick={() => deleteServiceRequest(row.id)}
                            disabled={loading}
                          >
                            Supprimer
                          </button>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            )}
          </div>
        </section>
  );
}
