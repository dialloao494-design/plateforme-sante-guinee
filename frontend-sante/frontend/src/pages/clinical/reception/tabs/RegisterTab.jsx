import { PAYER_TYPE_OPTIONS } from '../../../../constants/clinicBranding.js';
import { RELATIONSHIP_OPTIONS, todayStr, EMPTY_REG } from '../constants.js';
import { calcAge, qrImageUrl } from '../utils.js';
import { GeneratedIdBanner } from '../components/FormPrimitives.jsx';

const SectionHeading = ({ id, number, title, description }) => (
  <div className="registration-section-heading">
    <span className="registration-section-number" aria-hidden="true">{number}</span>
    <div>
      <h3 id={id}>{title}</h3>
      {description && <p>{description}</p>}
    </div>
  </div>
);

const PatientSummary = ({ form, registeredPatient }) => {
  const fullName = [form.last_name, form.first_name].filter(Boolean).join(' ');
  const birth = form.date_of_birth_precision === 'year'
    ? form.birth_year
    : form.date_of_birth?.split('-').reverse().join('/');

  return (
    <aside className="registration-patient-strip" aria-label="Résumé du patient" aria-live="polite">
      <div className="registration-patient-avatar" aria-hidden="true">
        {(form.last_name?.[0] || 'P').toUpperCase()}{(form.first_name?.[0] || '').toUpperCase()}
      </div>
      <div className="registration-patient-identity">
        <span>Patient en cours</span>
        <strong>{fullName || 'Identité à renseigner'}</strong>
      </div>
      <dl>
        <div><dt>N° dossier</dt><dd>{registeredPatient?.patient_number || 'Attribué après synchronisation'}</dd></div>
        <div><dt>Naissance</dt><dd>{birth || 'À renseigner'}</dd></div>
        <div><dt>Sexe</dt><dd>{form.gender === 'F' ? 'Féminin' : form.gender === 'M' ? 'Masculin' : form.gender || 'À renseigner'}</dd></div>
        <div><dt>Téléphone</dt><dd>{form.phone || 'À renseigner'}</dd></div>
      </dl>
    </aside>
  );
};

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
  editingPatientId,
  cancelPatientEdit,
}) {
  const registrationLocked = Boolean(
    !editingPatientId && (registeredPatient?.patient_number || registeredPatient?._sync_status === 'queued'),
  );

  return (
    <section className="reception-his-panel registration-workspace">
      <form className="clinical-card reception-his-form-sheet registration-form" onSubmit={handleRegister}>
        <header className="registration-form-header">
          <div>
            <p className="registration-eyebrow">{editingPatientId ? 'Dossier patient existant' : 'Nouveau dossier patient'}</p>
            <h2>{editingPatientId ? 'Modifier les informations du patient' : 'Enregistrement patient'}</h2>
            <p>Les champs marqués d’un astérisque (*) sont obligatoires.</p>
          </div>
          <label className="registration-date-field">
            Date d’inscription
            <input
              required
              type="date"
              name="registration_date"
              value={regForm.registration_date}
              onChange={(e) => updateReg({ registration_date: e.target.value })}
              autoComplete="off"
            />
          </label>
        </header>

        <PatientSummary form={regForm} registeredPatient={registeredPatient} />
        <GeneratedIdBanner label="N° dossier patient généré" value={registeredPatient?.patient_number} />

        {registeredPatient?._sync_status === 'queued' && !registeredPatient?.patient_number && (
          <div className="reception-his-qr-block" data-testid="reception-registration-queued" role="status">
            <div>
              <p data-testid="reception-patient-sync-status"><strong>Enregistré hors ligne</strong> — synchronisation en attente</p>
              <p data-testid="reception-patient-local-id"><strong>ID local :</strong> {registeredPatient.id}</p>
              <p className="clinical-hint">Le N° dossier sera attribué à la reconnexion. Ne créez pas un second dossier pour ce patient.</p>
            </div>
          </div>
        )}

        {registeredPatient?.patient_number && (
          <div className="reception-his-qr-block" data-testid="reception-registration-success" role="status">
            <div>
              <p data-testid="reception-patient-number"><strong>N° dossier patient :</strong> {registeredPatient.patient_number}</p>
              <p><strong>QR :</strong> {registeredPatient.qr_token || '—'}</p>
              <p className="clinical-hint">Dossier créé. Imprimez la fiche ou commencez un nouvel enregistrement.</p>
            </div>
            {registeredPatient.qr_token && <img src={qrImageUrl(registeredPatient.qr_token)} alt="Code QR du patient" width={112} height={112} />}
          </div>
        )}

        <div className="registration-sections">
          <section className="registration-section" aria-labelledby="registration-identity-title">
            <SectionHeading id="registration-identity-title" number="1" title="Identité du patient" description="Vérifiez l’orthographe avec une pièce d’identité si elle est disponible." />
            <div className="registration-grid registration-grid--2">
              <label>Nom *
                <input required name="last_name" autoComplete="off" value={regForm.last_name} onChange={(e) => updateReg({ last_name: e.target.value })} />
              </label>
              <label>Prénom *
                <input required name="first_name" autoComplete="off" value={regForm.first_name} onChange={(e) => updateReg({ first_name: e.target.value })} />
              </label>
              <label>Sexe *
                <select required name="gender" autoComplete="off" value={regForm.gender} onChange={(e) => updateReg({ gender: e.target.value })}>
                  <option value="F">Féminin</option><option value="M">Masculin</option><option value="Autre">Autre</option>
                </select>
              </label>
              <label className="registration-checkbox-card">
                <input type="checkbox" name="is_newborn" checked={regForm.is_newborn} onChange={(e) => updateReg({ is_newborn: e.target.checked })} />
                <span><strong>Nouveau-né</strong><small>Patient âgé de moins de 28 jours</small></span>
              </label>
            </div>

            <div className="registration-birth-block">
              <div className="registration-field-label">Date de naissance ou âge *</div>
              <div className="registration-choice-group" role="radiogroup" aria-label="Précision de la date de naissance">
                <label><input type="radio" name="birth-date-mode" value="full" checked={regForm.date_of_birth_precision === 'full'} onChange={() => updateReg({ date_of_birth_precision: 'full', birth_year: '' })} />Date complète</label>
                <label><input type="radio" name="birth-date-mode" value="year" checked={regForm.date_of_birth_precision === 'year'} onChange={() => updateReg({ date_of_birth_precision: 'year', date_of_birth: '' })} />Année seulement</label>
                <label><input type="radio" name="birth-date-mode" value="unknown" checked={regForm.date_of_birth_precision === 'unknown'} onChange={() => updateReg({ date_of_birth_precision: 'unknown', date_of_birth: '', birth_year: '' })} />Âge seulement</label>
              </div>
              <div className="registration-grid registration-grid--2">
                {regForm.date_of_birth_precision === 'unknown' ? (
                  <>
                    <label>Âge déclaré *
                      <input required type="number" inputMode="numeric" name="age_value" min="0" max={{ days: 365, weeks: 104, months: 240, years: 130 }[regForm.age_unit]} value={regForm.age_value} onChange={(e) => updateReg({ age_value: e.target.value.replace(/[^\d]/g, '').slice(0, 3), age_years: e.target.value && regForm.age_unit === 'years' ? e.target.value : '0' })} placeholder="Ex. 2" />
                    </label>
                    <label>Unité *
                      <select required name="age_unit" value={regForm.age_unit} onChange={(e) => updateReg({ age_unit: e.target.value, age_years: e.target.value === 'years' ? regForm.age_value : '0' })}>
                        <option value="days">Jour(s)</option><option value="weeks">Semaine(s)</option><option value="months">Mois</option><option value="years">Année(s)</option>
                      </select>
                    </label>
                  </>
                ) : regForm.date_of_birth_precision === 'year' ? (
                  <label>Année de naissance *
                    <input required type="number" inputMode="numeric" name="birth_year" autoComplete="off" min="1900" max={new Date().getFullYear()} placeholder="Ex. 1985" value={regForm.birth_year} onChange={(e) => {
                      const year = e.target.value.replace(/[^\d]/g, '').slice(0, 4);
                      updateReg({ birth_year: year, age_years: year.length === 4 ? String(new Date().getFullYear() - Number(year)) : regForm.age_years });
                    }} />
                  </label>
                ) : (
                  <label>Date complète *
                    <input required type="date" name="date_of_birth" data-testid="reception-date-of-birth" autoComplete="bday" max={todayStr} value={regForm.date_of_birth} onChange={(e) => {
                      const dob = e.target.value;
                      const age = calcAge(dob);
                      updateReg({ date_of_birth: dob, age_years: age !== '' ? String(age) : regForm.age_years });
                    }} />
                    <small>Format affiché selon l’appareil · jour / mois / année</small>
                  </label>
                )}
                {regForm.date_of_birth_precision !== 'unknown' && <label>Âge calculé (années)
                  <input readOnly type="number" name="age_years" value={regForm.age_years} />
                  <small>Calculé automatiquement à partir de la naissance.</small>
                </label>}
              </div>
            </div>
          </section>

          <section className="registration-section" aria-labelledby="registration-contact-title">
            <SectionHeading id="registration-contact-title" number="2" title="Coordonnées" description="Utilisées pour joindre le patient et éviter les dossiers en double." />
            <div className="registration-grid registration-grid--2">
              <label>Tél. principal *<input required type="tel" inputMode="tel" name="phone" autoComplete="tel" placeholder="Ex. 622 00 00 00" value={regForm.phone} onChange={(e) => updateReg({ phone: e.target.value })} /></label>
              <label>Téléphone secondaire<input type="tel" inputMode="tel" name="phone_secondary" autoComplete="off" placeholder="Optionnel" value={regForm.phone_secondary} onChange={(e) => updateReg({ phone_secondary: e.target.value })} /></label>
              <label className="registration-grid-span">Adresse *<input required name="address" autoComplete="street-address" placeholder="Quartier, secteur ou repère" value={regForm.address} onChange={(e) => updateReg({ address: e.target.value })} /></label>
              <label>Commune / ville<input name="commune" autoComplete="address-level2" value={regForm.commune} onChange={(e) => updateReg({ commune: e.target.value })} /></label>
              <label>Région<input name="region" autoComplete="address-level1" value={regForm.region} onChange={(e) => updateReg({ region: e.target.value })} /></label>
            </div>
          </section>

          <section className="registration-section" aria-labelledby="registration-emergency-title">
            <SectionHeading id="registration-emergency-title" number="3" title="Personne à contacter" description="À prévenir en cas d’urgence ou d’impossibilité de joindre le patient." />
            <div className="registration-grid registration-grid--2">
              <label>Nom du contact *<input required name="emergency_full_name" autoComplete="off" value={regForm.emergency_full_name} onChange={(e) => updateReg({ emergency_full_name: e.target.value })} /></label>
              <label>Relation *<select required name="emergency_relationship" autoComplete="off" value={regForm.emergency_relationship} onChange={(e) => updateReg({ emergency_relationship: e.target.value })}><option value="">Sélectionner…</option>{RELATIONSHIP_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}</select></label>
              {regForm.emergency_relationship === 'Autre' && <label>Préciser la relation *<input required name="emergency_relationship_other" autoComplete="off" value={regForm.emergency_relationship_other} onChange={(e) => updateReg({ emergency_relationship_other: e.target.value })} /></label>}
              <label>Téléphone *<input required type="tel" inputMode="tel" name="emergency_phone" autoComplete="off" value={regForm.emergency_phone} onChange={(e) => updateReg({ emergency_phone: e.target.value })} /></label>
              <label className="registration-checkbox-card registration-grid-span"><input type="checkbox" checked={regForm.emergency_same_address} onChange={(e) => updateReg({ emergency_same_address: e.target.checked })} /><span><strong>Même adresse que le patient</strong><small>Masque les champs d’adresse du contact.</small></span></label>
              {!regForm.emergency_same_address && <>
                <label className="registration-grid-span">Adresse du contact<input name="emergency_address" autoComplete="off" value={regForm.emergency_address} onChange={(e) => updateReg({ emergency_address: e.target.value })} /></label>
                <label>Commune / ville<input name="emergency_commune" autoComplete="off" value={regForm.emergency_commune} onChange={(e) => updateReg({ emergency_commune: e.target.value })} /></label>
                <label>Région<input name="emergency_region" autoComplete="off" value={regForm.emergency_region} onChange={(e) => updateReg({ emergency_region: e.target.value })} /></label>
              </>}
            </div>
          </section>

          <details className="registration-section registration-optional">
            <summary><span><strong>Informations complémentaires</strong><small>Photo, langue, profession, filiation et payeur</small></span><span aria-hidden="true">＋</span></summary>
            <div className="registration-optional-content">
              <div className="registration-grid registration-grid--2">
                <label>État civil<input name="marital_status" autoComplete="off" value={regForm.marital_status} onChange={(e) => updateReg({ marital_status: e.target.value })} /></label>
                <label>Nationalité<input name="nationality" autoComplete="country-name" value={regForm.nationality} onChange={(e) => updateReg({ nationality: e.target.value })} /></label>
                <label>Nom de la mère<input name="mother_last_name" autoComplete="off" value={regForm.mother_last_name} onChange={(e) => updateReg({ mother_last_name: e.target.value })} /></label>
                <label>Prénom de la mère<input name="mother_first_name" autoComplete="off" value={regForm.mother_first_name} onChange={(e) => updateReg({ mother_first_name: e.target.value })} /></label>
                <label>Profession<input name="profession" autoComplete="organization-title" value={regForm.profession} onChange={(e) => updateReg({ profession: e.target.value })} /></label>
                <label>Langue préférée<input name="preferred_language" autoComplete="language" value={regForm.preferred_language} onChange={(e) => updateReg({ preferred_language: e.target.value })} /></label>
                <label>Email<input type="email" inputMode="email" name="email" autoComplete="email" spellCheck="false" value={regForm.email} onChange={(e) => updateReg({ email: e.target.value })} /></label>
                <label>Photo du patient<input type="file" name="photo" accept="image/*" capture="user" onChange={(e) => onPhotoFile(e.target.files?.[0])} /></label>
                {regForm.photo_url && <div className="reception-his-photo-preview"><img src={regForm.photo_url} alt="Aperçu de la photo du patient" width="96" height="96" /></div>}
                <label>Pays<input name="country" autoComplete="country-name" value={regForm.country} onChange={(e) => updateReg({ country: e.target.value })} /></label>
                <label>Type de payeur<select name="payer_type" value={regForm.payer_type} onChange={(e) => updateReg({ payer_type: e.target.value })}>{PAYER_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label>
                {regForm.payer_type === 'insurance' && <><label>Compagnie d’assurance<input name="insurance_company" autoComplete="organization" value={regForm.insurance_company} onChange={(e) => updateReg({ insurance_company: e.target.value })} /></label><label>Numéro d’assurance<input name="insurance_number" autoComplete="off" value={regForm.insurance_number} onChange={(e) => updateReg({ insurance_number: e.target.value })} /></label></>}
                {regForm.payer_type === 'company' && <label>Nom de l’entreprise<input name="company_name" autoComplete="organization" value={regForm.company_name} onChange={(e) => updateReg({ company_name: e.target.value })} /></label>}
                <label className="registration-grid-span">Notes sur le payeur<textarea rows={3} name="payer_notes" value={regForm.payer_notes} onChange={(e) => updateReg({ payer_notes: e.target.value })} /></label>
              </div>
            </div>
          </details>
        </div>

        {duplicateMatches.length > 0 && (
          <div className="reception-his-duplicate-panel" role="alert" data-testid="duplicate-patient-panel">
            <h3>Patients similaires détectés</h3>
            <p>Un dossier avec le même téléphone ou la même identité existe déjà. Ouvrez-le, ou confirmez seulement s’il s’agit bien d’un autre patient.</p>
            <div className="registration-table-scroll"><table className="lab-his-queue-table"><thead><tr><th>N° dossier</th><th>Nom</th><th>Téléphone</th><th>Date de naissance</th><th>Correspondance</th><th>Action</th></tr></thead><tbody>{duplicateMatches.map((match) => <tr key={match.id}><td>{match.patient_number || match.id}</td><td>{match.last_name} {match.first_name}</td><td>{match.phone || '—'}</td><td>{match.date_of_birth || '—'}</td><td>{(match.match_reasons || []).join(', ') || '—'}</td><td><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => openExistingDuplicate(match)} disabled={loading}>Ouvrir</button></td></tr>)}</tbody></table></div>
            <div className="reception-his-duplicate-actions"><button type="button" className="clinical-btn" data-testid="confirm-duplicate-register" onClick={handleConfirmDuplicateRegister} disabled={loading || !pendingRegPayload}>Confirmer le nouveau patient</button><button type="button" className="clinical-btn clinical-btn--secondary" onClick={clearDuplicatePanel} disabled={loading}>Revenir au formulaire</button></div>
          </div>
        )}

        <footer className="registration-action-bar">
          <div><strong>{editingPatientId ? 'Modification du dossier' : registrationLocked ? 'Dossier enregistré' : 'Prêt à enregistrer'}</strong><span>{editingPatientId ? 'Le numéro de dossier restera inchangé.' : registrationLocked ? 'Vous pouvez imprimer la fiche ou saisir un autre patient.' : 'Une vérification des doublons sera effectuée avant la création.'}</span></div>
          <div className="registration-actions">
            <button type="submit" className="clinical-btn registration-primary-action" disabled={loading || registrationLocked} data-testid="reception-register-submit">{loading ? 'Enregistrement…' : editingPatientId ? 'Enregistrer les modifications' : 'Enregistrer le patient'}</button>
            {editingPatientId && <button type="button" className="clinical-btn clinical-btn--secondary" onClick={cancelPatientEdit} disabled={loading}>Annuler</button>}
            {registeredPatient?.patient_number && <button type="button" className="clinical-btn clinical-btn--secondary" onClick={printRegistrationSheet}>Imprimer la fiche</button>}
            {registeredPatient && <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => { setRegisteredPatient(null); setRegistrationPrintForm(null); clearDuplicatePanel?.(); setRegForm({ ...EMPTY_REG, registration_date: todayStr }); setMessage(''); }} data-testid="reception-new-registration">Nouvel enregistrement</button>}
          </div>
        </footer>
      </form>
    </section>
  );
}
