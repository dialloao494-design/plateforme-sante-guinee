import { ADMISSION_CONFIRMATIONS, ADMISSION_TYPES, FIELD_HINTS, PATIENT_REQUIRED_NOTICE } from '../constants.js';
import PatientContextPanel from '../components/PatientContextPanel.jsx';
import { DisplayField, FormNotice, GeneratedIdBanner } from '../components/FormPrimitives.jsx';

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
          <form className="clinical-card reception-his-form-sheet" onSubmit={handleAdmission}>
            <h2>Admission</h2>
            <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>
            <GeneratedIdBanner label="N° admission généré" value={lastAdmission?.admission_number} />
            <fieldset>
              <legend>Admission</legend>
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
                  <span className="reception-his-multi-service-label">Services demandés *</span>
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
                        {svc}
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
                      <div className="reception-his-specialty-picker">
                        <label>
                          Examen de laboratoire *
                          <input
                            type="search"
                            value={admissionLabSearchQ}
                            onChange={(e) => setAdmissionLabSearchQ(e.target.value)}
                            placeholder="Rechercher un examen…"
                          />
                        </label>
                        {admissionLabSelection && (
                          <p className="clinical-hint">Sélectionné : <strong>{admissionLabSelection.name}</strong></p>
                        )}
                        {filteredAdmissionLabTests.length > 0 && (
                          <ul className="reception-his-lab-search-results">
                            {filteredAdmissionLabTests.map((test) => (
                              <li key={test.code}>
                                <button type="button" onClick={() => setAdmissionLabSelection(test)}>
                                  {test.name} ({test.code})
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="reception-his-admission-meta">
                  <label>
                    Date et heure d&apos;admission
                    <div className="reception-his-datetime-pair">
                      <input
                        required
                        type="date"
                        value={admissionForm.admission_date}
                        onChange={(e) => updateAdmission({ admission_date: e.target.value })}
                      />
                      <input
                        required
                        type="time"
                        value={admissionForm.admission_time}
                        onChange={(e) => updateAdmission({ admission_time: e.target.value })}
                      />
                    </div>
                  </label>
                  <label>
                    Médecin traitant
                    <select value={admissionForm.attending_clinician_user_id} onChange={(e) => updateAdmission({ attending_clinician_user_id: e.target.value })}>
                      <option value="">— Sélectionner —</option>
                      {doctors.map((d) => (
                        <option key={d.user_id || d.id} value={d.user_id || d.id}>
                          {d.name || d.full_name || d.email}
                        </option>
                      ))}
                    </select>
                    <input
                      type="text"
                      placeholder="Ou saisir le nom du médecin"
                      value={admissionForm.attending_physician_name}
                      onChange={(e) => updateAdmission({ attending_physician_name: e.target.value })}
                    />
                  </label>
                  <label>
                    Type d&apos;admission
                    <select
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
                  <label>
                    Confirmation / rendez-vous
                    <select value={admissionForm.confirmation_status} onChange={(e) => updateAdmission({ confirmation_status: e.target.value })}>
                      {ADMISSION_CONFIRMATIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                  </label>
                  <label className="reception-his-notes-field reception-his-admission-notes">
                    Notes
                    <textarea rows={2} value={admissionForm.notes} onChange={(e) => updateAdmission({ notes: e.target.value })} />
                  </label>
                </div>
              </div>
            </fieldset>
            <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>Créer l&apos;admission</button>
          </form>
        </section>
  );
}
