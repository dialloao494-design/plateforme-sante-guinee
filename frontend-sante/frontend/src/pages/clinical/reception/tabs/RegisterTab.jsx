import { PAYER_TYPE_OPTIONS } from '../../../../constants/clinicBranding.js';
import { FIELD_HINTS, RELATIONSHIP_OPTIONS, todayStr, EMPTY_REG } from '../constants.js';
import { calcAge, qrImageUrl } from '../utils.js';
import {
  DisplayField,
  FormNotice,
  GeneratedIdBanner,
} from '../components/FormPrimitives.jsx';

export default function RegisterTab({
  handleRegister,
  handleConfirmDuplicateRegister,
  openExistingDuplicate,
  clearDuplicatePanel,
  duplicateMatches = [],
  pendingRegPayload,
  loading,
  onPhotoFile,
  printRegistrationSheet,
  regForm,
  registeredPatient,
  setMessage,
  setRegForm,
  setRegisteredPatient,
  setRegistrationPrintForm,
  updateReg,
}) {
  return (
        <section className="reception-his-panel">
          <form className="clinical-card reception-his-form-sheet" onSubmit={handleRegister}>
            <h2>Enregistrement patient</h2>
            <GeneratedIdBanner label="N° dossier patient généré" value={registeredPatient?.patient_number} />
            {registeredPatient?._sync_status === 'queued' && !registeredPatient?.patient_number && (
              <div
                className="reception-his-qr-block"
                data-testid="reception-registration-queued"
              >
                <div>
                  <p data-testid="reception-patient-sync-status">
                    <strong>Statut :</strong> Enregistré hors ligne — synchronisation en attente
                  </p>
                  <p className="clinical-hint">
                    Le N° dossier patient sera attribué automatiquement dès la reconnexion.
                    Ne créez pas un second enregistrement pour le même patient.
                  </p>
                </div>
              </div>
            )}
            {registeredPatient?.patient_number && (
              <div
                className="reception-his-qr-block"
                data-testid="reception-registration-success"
              >
                <div>
                  <p data-testid="reception-patient-number">
                    <strong>N° dossier patient :</strong> {registeredPatient.patient_number}
                  </p>
                  <p><strong>QR :</strong> {registeredPatient.qr_token || '—'}</p>
                  <p className="clinical-hint">
                    Identifiant généré. Utilisez « Nouvel enregistrement » pour saisir un autre patient.
                  </p>
                </div>
                {registeredPatient.qr_token && <img src={qrImageUrl(registeredPatient.qr_token)} alt="QR patient" width={140} height={140} />}
              </div>
            )}
            <fieldset><legend>Identité</legend><div className="clinical-form-row">
              <DisplayField
                label="N° dossier patient"
                value={registeredPatient?.patient_number || ''}
                hint={
                  registeredPatient?.patient_number
                    ? undefined
                    : (registeredPatient?._sync_status === 'queued'
                      ? 'Synchronisation en attente — le N° dossier sera généré à la reconnexion.'
                      : FIELD_HINTS.patientId)
                }
              />
              <label>Date inscription<input required type="date" value={regForm.registration_date} onChange={(e) => updateReg({ registration_date: e.target.value })} /></label>
              <label className="reception-his-check"><input type="checkbox" checked={regForm.is_newborn} onChange={(e) => updateReg({ is_newborn: e.target.checked })} />Nouveau-né</label>
              <label>Nom *<input required value={regForm.last_name} onChange={(e) => updateReg({ last_name: e.target.value })} /></label>
              <label>Prénom *<input required value={regForm.first_name} onChange={(e) => updateReg({ first_name: e.target.value })} /></label>
              <div className="reception-his-birthdate-field">
                <span>Date naissance *</span>
                <div className="reception-his-birthdate-modes">
                  <label>
                    <input
                      type="radio"
                      name="birth-date-mode"
                      value="full"
                      checked={regForm.date_of_birth_precision === 'full'}
                      onChange={() => updateReg({ date_of_birth_precision: 'full', birth_year: '' })}
                    />
                    Date complète (JJ/MM/AAAA)
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="birth-date-mode"
                      value="year"
                      checked={regForm.date_of_birth_precision === 'year'}
                      onChange={() => updateReg({ date_of_birth_precision: 'year', date_of_birth: '' })}
                    />
                    Année seulement (AAAA)
                  </label>
                </div>
                {regForm.date_of_birth_precision === 'year' ? (
                  <input
                    required
                    type="number"
                    inputMode="numeric"
                    min="1900"
                    max={new Date().getFullYear()}
                    placeholder="AAAA"
                    value={regForm.birth_year}
                    onChange={(e) => {
                      const year = e.target.value.replace(/[^\d]/g, '').slice(0, 4);
                      updateReg({
                        birth_year: year,
                        age_years: year.length === 4 ? String(new Date().getFullYear() - Number(year)) : regForm.age_years,
                      });
                    }}
                  />
                ) : (
                  <input
                    type="date"
                    value={regForm.date_of_birth}
                    onChange={(e) => {
                      const dob = e.target.value;
                      const age = calcAge(dob);
                      updateReg({
                        date_of_birth: dob,
                        age_years: age !== '' ? String(age) : regForm.age_years,
                      });
                    }}
                  />
                )}
              </div>
              <label>
                Âge *
                <input
                  required
                  type="number"
                  inputMode="numeric"
                  min="0"
                  max="130"
                  value={regForm.age_years}
                  onChange={(e) => updateReg({ age_years: e.target.value.replace(/[^\d]/g, '').slice(0, 3) })}
                  placeholder="Saisir ou corriger l’âge"
                />
                <span className="reception-his-field-hint">
                  Saisissable manuellement si la date exacte est inconnue.
                </span>
              </label>
              <label>Sexe *<select required value={regForm.gender} onChange={(e) => updateReg({ gender: e.target.value })}><option value="F">Féminin</option><option value="M">Masculin</option><option value="Autre">Autre</option></select></label>
              <label>État civil<input value={regForm.marital_status} onChange={(e) => updateReg({ marital_status: e.target.value })} /></label>
              <label>Nationalité<input value={regForm.nationality} onChange={(e) => updateReg({ nationality: e.target.value })} /></label>
              <label>Nom mère<input value={regForm.mother_last_name} onChange={(e) => updateReg({ mother_last_name: e.target.value })} /></label>
              <label>Prénom mère<input value={regForm.mother_first_name} onChange={(e) => updateReg({ mother_first_name: e.target.value })} /></label>
              <label>Profession du patient<input value={regForm.profession} onChange={(e) => updateReg({ profession: e.target.value })} /></label>
              <label>Langue<input value={regForm.preferred_language} onChange={(e) => updateReg({ preferred_language: e.target.value })} /></label>
              <label>Email<input type="email" value={regForm.email} onChange={(e) => updateReg({ email: e.target.value })} /></label>
            </div></fieldset>
            <fieldset><legend>Photo</legend><div className="clinical-form-row">
              <label>Photo (optionnelle)<input type="file" accept="image/*" onChange={(e) => onPhotoFile(e.target.files?.[0])} /></label>
              {regForm.photo_url && <div className="reception-his-photo-preview"><img src={regForm.photo_url} alt="Aperçu" /></div>}
            </div></fieldset>
            <fieldset><legend>Adresse</legend><div className="clinical-form-row">
              <label>Adresse *<input required value={regForm.address} onChange={(e) => updateReg({ address: e.target.value })} /></label>
              <label>Tél. principal *<input required value={regForm.phone} onChange={(e) => updateReg({ phone: e.target.value })} /></label>
              <label>Tél. secondaire<input value={regForm.phone_secondary} onChange={(e) => updateReg({ phone_secondary: e.target.value })} /></label>
              <label>Commune / ville<input value={regForm.commune} onChange={(e) => updateReg({ commune: e.target.value })} /></label>
              <label>Région<input value={regForm.region} onChange={(e) => updateReg({ region: e.target.value })} /></label>
              <label>Pays<input value={regForm.country} onChange={(e) => updateReg({ country: e.target.value })} /></label>
            </div></fieldset>
            <fieldset><legend>Personne à contacter</legend>
              <label className="reception-his-check"><input type="checkbox" checked={regForm.emergency_same_address} onChange={(e) => updateReg({ emergency_same_address: e.target.checked })} />Adresse identique à celle du patient</label>
              <div className="clinical-form-row">
                <label>Nom du contact *<input required value={regForm.emergency_full_name} onChange={(e) => updateReg({ emergency_full_name: e.target.value })} /></label>
                <label>
                  Relation *
                  <select
                    required
                    value={regForm.emergency_relationship}
                    onChange={(e) => updateReg({ emergency_relationship: e.target.value })}
                  >
                    <option value="">— Sélectionner —</option>
                    {RELATIONSHIP_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </label>
                {regForm.emergency_relationship === 'Autre' && (
                  <label>
                    Préciser la relation
                    <input
                      required
                      value={regForm.emergency_relationship_other}
                      onChange={(e) => updateReg({ emergency_relationship_other: e.target.value })}
                      placeholder="Saisir la relation…"
                    />
                  </label>
                )}
                <label>Téléphone *<input required value={regForm.emergency_phone} onChange={(e) => updateReg({ emergency_phone: e.target.value })} /></label>
                {!regForm.emergency_same_address && (
                  <>
                    <label>Adresse contact<input value={regForm.emergency_address} onChange={(e) => updateReg({ emergency_address: e.target.value })} /></label>
                    <label>Commune / ville contact<input value={regForm.emergency_commune} onChange={(e) => updateReg({ emergency_commune: e.target.value })} /></label>
                    <label>Région contact<input value={regForm.emergency_region} onChange={(e) => updateReg({ emergency_region: e.target.value })} /></label>
                    <label>Pays contact<input value={regForm.emergency_country} onChange={(e) => updateReg({ emergency_country: e.target.value })} /></label>
                  </>
                )}
              </div>
            </fieldset>
            <fieldset><legend>Payeur</legend><div className="clinical-form-row">
              <label>Type de payeur<select value={regForm.payer_type} onChange={(e) => updateReg({ payer_type: e.target.value })}>{PAYER_TYPE_OPTIONS.map((o) => (<option key={o.value} value={o.value}>{o.label}</option>))}</select></label>
              {regForm.payer_type === 'insurance' && (<><label>Compagnie d’assurance<input value={regForm.insurance_company} onChange={(e) => updateReg({ insurance_company: e.target.value })} /></label><label>Numéro d’assurance<input value={regForm.insurance_number} onChange={(e) => updateReg({ insurance_number: e.target.value })} /></label></>)}
              {regForm.payer_type === 'company' && <label>Nom de l’entreprise<input value={regForm.company_name} onChange={(e) => updateReg({ company_name: e.target.value })} /></label>}
              <label>Notes<textarea rows={2} value={regForm.payer_notes} onChange={(e) => updateReg({ payer_notes: e.target.value })} /></label>
            </div></fieldset>
            {duplicateMatches.length > 0 && (
              <div className="reception-his-duplicate-panel" role="alert" data-testid="duplicate-patient-panel">
                <h3>Patients similaires détectés</h3>
                <p>
                  Un enregistrement avec le même téléphone ou le même nom + date de naissance existe déjà.
                  Ouvrez le dossier existant, ou confirmez uniquement s’il s’agit d’un nouveau patient distinct.
                </p>
                <table className="lab-his-queue-table">
                  <thead>
                    <tr>
                      <th>N° dossier</th>
                      <th>Nom</th>
                      <th>Téléphone</th>
                      <th>Date de naissance</th>
                      <th>Correspondance</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {duplicateMatches.map((match) => (
                      <tr key={match.id}>
                        <td>{match.patient_number || match.id}</td>
                        <td>{match.last_name} {match.first_name}</td>
                        <td>{match.phone || '—'}</td>
                        <td>{match.date_of_birth || '—'}</td>
                        <td>{(match.match_reasons || []).join(', ') || '—'}</td>
                        <td>
                          <button
                            type="button"
                            className="clinical-btn clinical-btn--secondary"
                            onClick={() => openExistingDuplicate(match)}
                            disabled={loading}
                          >
                            Ouvrir
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="reception-his-duplicate-actions">
                  <button
                    type="button"
                    className="clinical-btn"
                    data-testid="confirm-duplicate-register"
                    onClick={handleConfirmDuplicateRegister}
                    disabled={loading || !pendingRegPayload}
                  >
                    Confirmer nouvel enregistrement
                  </button>
                  <button
                    type="button"
                    className="clinical-btn clinical-btn--secondary"
                    onClick={clearDuplicatePanel}
                    disabled={loading}
                  >
                    Annuler
                  </button>
                </div>
              </div>
            )}
            <button
              type="submit"
              className="clinical-btn"
              disabled={
                loading
                || Boolean(registeredPatient?.patient_number)
                || registeredPatient?._sync_status === 'queued'
              }
              data-testid="reception-register-submit"
            >
              Enregistrer le patient
            </button>
            {registeredPatient?.patient_number && (
              <button
                type="button"
                className="clinical-btn clinical-btn--secondary"
                onClick={printRegistrationSheet}
              >
                Imprimer la fiche d&apos;enregistrement
              </button>
            )}
            {registeredPatient && (
              <button
                type="button"
                className="clinical-btn clinical-btn--secondary"
                onClick={() => {
                  setRegisteredPatient(null);
                  setRegistrationPrintForm(null);
                  clearDuplicatePanel?.();
                  setRegForm({ ...EMPTY_REG, registration_date: todayStr });
                  setMessage('');
                }}
                data-testid="reception-new-registration"
              >
                Nouvel enregistrement
              </button>
            )}
          </form>
        </section>
  );
}
