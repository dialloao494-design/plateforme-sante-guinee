import { formatClinicalDateTime } from '../../../utils/clinicalPresentation.js';

const qrImageUrl = (token) =>
  token ? `https://api.qrserver.com/v1/create-qr-code/?size=110x110&data=${encodeURIComponent(token)}` : '';

function genderLabel(gender) {
  if (gender === 'F' || gender === 'Féminin' || gender === 'f') return 'Féminin';
  if (gender === 'M' || gender === 'Masculin' || gender === 'm') return 'Masculin';
  return gender || '—';
}

export default function DoctorPatientOverview({ identity, nurseAssessment }) {
  return (
    <>
      <section className="doctor-box" data-testid="doctor-patient-overview">
        <div className="doctor-box-title">Identité du patient</div>
        <div className="doctor-box-body">
          {identity ? (
            <div className="doctor-identity">
              <div className="doctor-identity-grid">
                <div><span>N° dossier</span><strong translate="no">{identity.patient_number || '—'}</strong></div>
                <div><span>Nom complet</span><strong>{identity.full_name}</strong></div>
                <div><span>Âge</span><strong>{identity.age ?? '—'}</strong></div>
                <div><span>Sexe</span><strong>{genderLabel(identity.sex)}</strong></div>
                <div><span>Téléphone</span><strong>{identity.phone || '—'}</strong></div>
                <div><span>Prise en charge</span><strong>{identity.payer || '—'}</strong></div>
              </div>
              {identity.qr_token && (
                <img
                  className="doctor-identity-qr"
                  src={qrImageUrl(identity.qr_token)}
                  alt="QR patient"
                  width={92}
                  height={92}
                />
              )}
            </div>
          ) : (
            <p className="clinical-hint">Identité indisponible.</p>
          )}
        </div>
      </section>

      <section className="doctor-box doctor-box--readonly" aria-label="Paramètres vitaux en lecture seule">
        <div className="doctor-box-title">
          Paramètres vitaux
          <span className="doctor-readonly-badge">Lecture seule — saisie infirmière</span>
        </div>
        <div className="doctor-box-body">
          {nurseAssessment ? (
            <>
              <p className="clinical-lead" style={{ marginTop: 0 }}>
                {nurseAssessment.nurse_name || 'Infirmier(ère)'} · {formatClinicalDateTime(nurseAssessment.recorded_at)}
              </p>
              <div className="doctor-vitals-grid">
                <div><span>T°</span><strong>{nurseAssessment.temperature_c ?? '—'} °C</strong></div>
                <div><span>TA</span><strong>{nurseAssessment.bp_systolic || '—'}/{nurseAssessment.bp_diastolic || '—'}</strong></div>
                <div><span>FC</span><strong>{nurseAssessment.heart_rate || '—'}</strong></div>
                <div><span>FR</span><strong>{nurseAssessment.respiratory_rate || '—'}</strong></div>
                <div><span>Poids</span><strong>{nurseAssessment.weight_kg ?? '—'} kg</strong></div>
                <div><span>Taille</span><strong>{nurseAssessment.height_cm ?? '—'} cm</strong></div>
                <div><span>IMC</span><strong>{nurseAssessment.bmi ?? '—'}</strong></div>
              </div>
              {nurseAssessment.vitals_observations && <p><strong>Observations :</strong> {nurseAssessment.vitals_observations}</p>}
              {nurseAssessment.hospitalized_daily_vitals && (
                <div className="doctor-nurse-readonly-block">
                  <strong>Signes vitaux hospitalisés (soins quotidiens) — infirmier(ère) :</strong>
                  <p>{nurseAssessment.hospitalized_daily_vitals}</p>
                </div>
              )}
              {nurseAssessment.reason_for_consultation && <p><strong>Motif (infirmière) :</strong> {nurseAssessment.reason_for_consultation}</p>}
              {nurseAssessment.prescription && <p><strong>Ordonnance (infirmière) :</strong> {nurseAssessment.prescription}</p>}
              {nurseAssessment.nurse_notes && <p><strong>Notes infirmières :</strong> {nurseAssessment.nurse_notes}</p>}
              <p className="clinical-hint">
                Le médecin consulte ces paramètres sans pouvoir les modifier. La saisie se fait uniquement côté infirmier.
              </p>
            </>
          ) : (
            <p className="clinical-hint">Aucune évaluation infirmière disponible.</p>
          )}
        </div>
      </section>
    </>
  );
}
