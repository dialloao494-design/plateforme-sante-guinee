import { CLINIC_LOGO_URL, CLINIC_PRINT_NAME } from '../../constants/clinicBranding.js';
import './print-documents.css';

const genderLabel = (g) => {
  if (g === 'F') return 'Féminin';
  if (g === 'M') return 'Masculin';
  return g || '—';
};

const formatDate = (d) => {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('fr-FR');
  } catch {
    return d;
  }
};

/** Printable patient registration sheet — AASMA clinic layout. */
export default function PatientRegistrationPrint({ patient, form }) {
  if (!patient) return null;
  const p = { ...form, ...patient };
  const printedAt = new Date().toLocaleString('fr-FR');

  return (
    <div className="print-registration-sheet">
      <header className="print-clinic-header">
        <img src={CLINIC_LOGO_URL} alt="" className="print-clinic-header__logo" width={120} height={120} />
        <p className="print-clinic-header__name">{CLINIC_PRINT_NAME}</p>
        <h1 className="print-registration-sheet__title">Fiche d&apos;enregistrement patient</h1>
      </header>

      <section className="print-registration-section">
        <h2>Identité</h2>
        <table className="print-registration-table">
          <tbody>
            <tr><th>N° dossier</th><td>{p.patient_number || p.id || '—'}</td><th>Date inscription</th><td>{formatDate(p.registration_date || form?.registration_date)}</td></tr>
            <tr><th>Nom</th><td>{p.last_name}</td><th>Prénom</th><td>{p.first_name}</td></tr>
            <tr><th>Date de naissance</th><td>{formatDate(p.date_of_birth)}</td><th>Sexe</th><td>{genderLabel(p.gender)}</td></tr>
            <tr><th>Nationalité</th><td>{p.nationality || '—'}</td><th>Profession</th><td>{p.profession || '—'}</td></tr>
            <tr><th>Téléphone</th><td>{p.phone}</td><th>Email</th><td>{p.email || '—'}</td></tr>
          </tbody>
        </table>
      </section>

      <section className="print-registration-section">
        <h2>Adresse</h2>
        <table className="print-registration-table">
          <tbody>
            <tr><th>Adresse</th><td colSpan={3}>{p.address || '—'}</td></tr>
            <tr><th>Commune / ville</th><td>{p.commune || p.city || '—'}</td><th>Région</th><td>{p.region || '—'}</td></tr>
            <tr><th>Pays</th><td colSpan={3}>{p.country || 'Guinée'}</td></tr>
          </tbody>
        </table>
      </section>

      <section className="print-registration-section">
        <h2>Personne à contacter</h2>
        <table className="print-registration-table">
          <tbody>
            <tr><th>Nom</th><td>{p.emergency_full_name || form?.emergency_full_name || '—'}</td><th>Relation</th><td>{p.emergency_relationship || form?.emergency_relationship || '—'}</td></tr>
            <tr><th>Téléphone</th><td colSpan={3}>{p.emergency_phone || form?.emergency_phone || '—'}</td></tr>
          </tbody>
        </table>
      </section>

      {p.qr_token && (
        <div className="print-registration-qr">
          <img src={`https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(p.qr_token)}`} alt="QR patient" width={100} height={100} />
          <p>Code QR : {p.qr_token}</p>
        </div>
      )}

      <footer className="print-registration-footer">
        <p>Imprimé le {printedAt}</p>
        <p>CHFMP – AASMA · Kobaya chinoiya · Tél. 613 04 94 48</p>
      </footer>
    </div>
  );
}
