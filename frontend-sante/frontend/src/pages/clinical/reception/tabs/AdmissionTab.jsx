import { ADMISSION_CONFIRMATIONS, ADMISSION_TYPES, FIELD_HINTS, PATIENT_REQUIRED_NOTICE } from '../constants.js';
import PatientContextPanel from '../components/PatientContextPanel.jsx';
import { DisplayField, FormNotice, GeneratedIdBanner } from '../components/FormPrimitives.jsx';
import { formatGNF } from '../../../../utils/appointmentPresentation.js';

export default function AdmissionTab({
  patientPayerLabel,
  admissionForm,
  admissionImagingCode,
  admissionLabSearchQ,
  admissionLabSelection,
  admissionServices,
  doctors,
  filteredAdmissionLabTests,
  handleAdmission,
  imagingExaminations,
  lastAdmission,
  loading,
  patientDisplayName,
  patientDossier,
  renderSpecialtyPicker,
  selectedPatient,
  setAdmissionImagingCode,
  setAdmissionLabSearchQ,
  setAdmissionLabSelection,
  showSpecialtyPicker,
  updateAdmission,
}) {
  return (
        <section className="reception-his-panel">
          <PatientContextPanel selectedPatient={selectedPatient} patientPayerLabel={patientPayerLabel} />
          <form className="clinical-card reception-his-form-sheet reception-admission-form" onSubmit={handleAdmission}>
            <header className="reception-admission-header">
              <div>
                <p>Parcours patient</p>
                <h2>Nouvelle admission</h2>
                <span>Choisissez les services et l’orientation du patient.</span>
              </div>
            </header>
            <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>
            <GeneratedIdBanner label="N° admission généré" value={lastAdmission?.admission_number} />
            <section className="reception-admission-body" aria-label="Informations d’admission">
              <div className="reception-his-admission-grid">
                <div className="reception-his-admission-ids">
                  <DisplayField
                    label="N° d'admission"
                    value={lastAdmission?.admission_number || ''}
                    hint={lastAdmission?.admission_number ? undefined : FIELD_HINTS.admissionNumber}
                  />
                  <DisplayField label="N° dossier patient" value={patientDossier} />
                  <DisplayField label="Nom et prénom" value={patientDisplayName} />
                </div>

                <div className="reception-his-admission-services">
                  <div className="reception-admission-section-title">
                    <strong>Services demandés *</strong>
                    <span>Sélectionnez un ou plusieurs services.</span>
                  </div>
                  <div className="reception-his-multi-service-grid">
                    {admissionServices.map((svc) => (
                      <label key={svc} className="reception-his-check">
                        <input
                          type="checkbox"
                          checked={(admissionForm.services || []).includes(svc)}
                          onChange={() => {
                            const current = admissionForm.services || [];
                            updateAdmission({
                              services: current.includes(svc)
                                ? current.filter((s) => s !== svc)
                                : [...current, svc],
                            });
                          }}
                        />
                        <span>{svc}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {(showSpecialtyPicker || (admissionForm.services || []).includes('Imagerie médicale') || (admissionForm.services || []).includes('Laboratoire')) && (
                  <div className="reception-his-admission-subopts">
                    {showSpecialtyPicker && renderSpecialtyPicker('admission')}
                    {(admissionForm.services || []).includes('Imagerie médicale') && imagingExaminations.length > 0 && (
                      <div className="reception-his-specialty-picker">
                        <label>
                          Examen d&apos;imagerie médicale *
                          <select
                            required
                            value={admissionImagingCode}
                            onChange={(e) => setAdmissionImagingCode(e.target.value)}
                          >
                            <option value="">Choisir un examen…</option>
                            {imagingExaminations.map((exam) => (
                              <option key={exam.code} value={exam.code}>{exam.label}</option>
                            ))}
                          </select>
                        </label>
                      </div>
                    )}
                    {(admissionForm.services || []).includes('Laboratoire') && (
                      <section className="reception-admission-service-detail reception-admission-lab-picker" aria-labelledby="admission-lab-title">
                        <div className="reception-admission-service-detail__head">
                          <div>
                            <span>Laboratoire</span>
                            <h3 id="admission-lab-title">Choisir un examen</h3>
                          </div>
                          {admissionLabSelection && (
                            <button
                              type="button"
                              className="reception-admission-selection"
                              onClick={() => {
                                setAdmissionLabSelection(null);
                                setAdmissionLabSearchQ('');
                              }}
                              aria-label={`Retirer ${admissionLabSelection.name}`}
                            >
                              <span>Sélectionné</span>
                              <strong>{admissionLabSelection.name}</strong>
                              <b aria-hidden="true">×</b>
                            </button>
                          )}
                        </div>
                        <label className="reception-admission-lab-search">
                          Rechercher dans le catalogue
                          <input
                            type="search"
                            name="admission_lab_search"
                            autoComplete="off"
                            value={admissionLabSearchQ}
                            onChange={(e) => setAdmissionLabSearchQ(e.target.value)}
                            placeholder="Nom ou code de l’examen…"
                            aria-controls="admission-lab-results"
                          />
                        </label>
                        {!admissionLabSearchQ.trim() && !admissionLabSelection && (
                          <p className="reception-admission-search-guidance">Saisissez au moins quelques lettres pour afficher les examens.</p>
                        )}
                        {filteredAdmissionLabTests.length > 0 && (
                          <ul id="admission-lab-results" className="reception-admission-lab-results" aria-label="Résultats des examens">
                            {filteredAdmissionLabTests.map((test) => (
                              <li key={test.code}>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setAdmissionLabSelection(test);
                                    setAdmissionLabSearchQ('');
                                  }}
                                >
                                  <span><strong>{test.name}</strong><small>{test.code}</small></span>
                                  <b>{formatGNF(test.price_gnf ?? test.unit_price_gnf ?? test.price ?? 0)}</b>
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                        {admissionLabSearchQ.trim() && filteredAdmissionLabTests.length === 0 && (
                          <p className="reception-admission-search-guidance" role="status">Aucun examen trouvé. Vérifiez le nom ou le code.</p>
                        )}
                      </section>
                    )}
                  </div>
                )}

                <div className="reception-his-admission-meta">
                  <label className="reception-admission-datetime">
                    Date et heure d&apos;admission
                    <div className="reception-his-datetime-pair">
                      <input
                        required
                        type="date"
                        name="admission_date"
                        autoComplete="off"
                        value={admissionForm.admission_date}
                        onChange={(e) => updateAdmission({ admission_date: e.target.value })}
                      />
                      <input
                        required
                        type="time"
                        name="admission_time"
                        autoComplete="off"
                        value={admissionForm.admission_time}
                        onChange={(e) => updateAdmission({ admission_time: e.target.value })}
                      />
                    </div>
                  </label>
                  <label className="reception-admission-physician">
                    Médecin traitant
                    <select name="attending_clinician_user_id" autoComplete="off" value={admissionForm.attending_clinician_user_id} onChange={(e) => updateAdmission({ attending_clinician_user_id: e.target.value })}>
                      <option value="">— Sélectionner —</option>
                      {doctors.map((d) => (
                        <option key={d.user_id || d.id} value={d.user_id || d.id}>
                          {d.name || d.full_name || d.email}
                        </option>
                      ))}
                    </select>
                    <input
                      type="text"
                      name="attending_physician_name"
                      autoComplete="off"
                      placeholder="Ou saisir un médecin externe…"
                      value={admissionForm.attending_physician_name}
                      onChange={(e) => updateAdmission({ attending_physician_name: e.target.value })}
                    />
                  </label>
                  <label className="reception-admission-type">
                    Type d&apos;admission
                    <select
                      name="admission_type"
                      autoComplete="off"
                      value={admissionForm.admission_type}
                      onChange={(e) => {
                        const v = e.target.value;
                        const patch = { admission_type: v };
                        if (v === 'specialized_consultation') {
                          const current = admissionForm.services || [];
                          if (!current.includes('Consultation spécialisée')) {
                            patch.services = [...current, 'Consultation spécialisée'];
                          }
                        }
                        updateAdmission(patch);
                      }}
                    >
                      {ADMISSION_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </label>
                  <label className="reception-admission-confirmation">
                    Confirmation / rendez-vous
                    <select name="confirmation_status" autoComplete="off" value={admissionForm.confirmation_status} onChange={(e) => updateAdmission({ confirmation_status: e.target.value })}>
                      {ADMISSION_CONFIRMATIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                  </label>
                  <label className="reception-his-notes-field reception-his-admission-notes">
                    Notes
                    <textarea name="admission_notes" rows={3} value={admissionForm.notes} onChange={(e) => updateAdmission({ notes: e.target.value })} />
                  </label>
                </div>
              </div>
            </section>
            <footer className="reception-admission-actions">
              <div>
                <strong>{selectedPatient ? 'Admission prête à être créée' : 'Sélectionnez d’abord un patient'}</strong>
                <span>Le numéro d’admission sera attribué automatiquement.</span>
              </div>
              <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>
                {loading ? 'Création…' : 'Créer l’admission'}
              </button>
            </footer>
          </form>
        </section>
  );
}
