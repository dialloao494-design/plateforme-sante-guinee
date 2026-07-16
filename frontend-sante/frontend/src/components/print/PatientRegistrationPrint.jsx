import PrintClinicHeader from './PrintClinicHeader.jsx';
import PrintDocumentFooter from './PrintDocumentFooter.jsx';
import { payerTypeLabel } from '../../constants/clinicBranding.js';
import './print-documents.css';

const genderLabel = (g) => {
  if (g === 'F') return 'Féminin';
  if (g === 'M') return 'Masculin';
  return g || '—';
};

const formatDate = (d, precision = 'full') => {
  if (precision === 'unknown') return 'Date inconnue';
  if (!d) return '—';
  if (precision === 'year') return String(d).slice(0, 4);
  try {
    return new Date(d).toLocaleDateString('fr-FR');
  } catch {
    return d;
  }
};

const parsePayer = (patient, form) => {
  const raw = patient?.payer_json || patient?.payer;
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
  if (raw && typeof raw === 'object') return raw;
  if (form?.payer_type) {
    return {
      payer_type: form.payer_type,
      insurance_company: form.insurance_company,
      insurance_number: form.insurance_number,
      company_name: form.company_name,
      notes: form.payer_notes,
    };
  }
  return null;
};

/** Printable patient registration sheet — single A4 page layout. */
export default function PatientRegistrationPrint({ patient, form, printedBy = '' }) {
  if (!patient) return null;
  const p = { ...form, ...patient };
  const payer = parsePayer(patient, form);

  return (
    <div className="print-registration-sheet">
      <div className="print-registration-top">
        <div className="print-registration-top-main">
          <PrintClinicHeader documentTitle="Fiche d'enregistrement patient" compact />
        </div>
        {p.qr_token && (
          <div className="print-registration-qr-corner" aria-label="Code QR patient">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=96x96&data=${encodeURIComponent(p.qr_token)}`}
              alt="QR patient"
              width={88}
              height={88}
            />
            <p className="print-registration-qr-token">{p.qr_token}</p>
          </div>
        )}
      </div>

      <section className="print-registration-section print-registration-section--compact">
        <h2>Identité</h2>
        <table className="print-registration-table print-registration-table--compact">
          <tbody>
            <tr><th>N° dossier</th><td>{p.patient_number || p.id || '—'}</td><th>Date inscription</th><td>{formatDate(p.registration_date || form?.registration_date)}</td></tr>
            <tr><th>Nom</th><td>{p.last_name}</td><th>Prénom</th><td>{p.first_name}</td></tr>
            <tr><th>Date naissance</th><td>{formatDate(p.date_of_birth, p.date_of_birth_precision)}</td><th>Sexe</th><td>{genderLabel(p.gender)}</td></tr>
            <tr><th>Téléphone</th><td>{p.phone}</td><th>Email</th><td>{p.email || '—'}</td></tr>
          </tbody>
        </table>
      </section>

      <section className="print-registration-section print-registration-section--compact">
        <h2>Adresse &amp; contact</h2>
        <table className="print-registration-table print-registration-table--compact">
          <tbody>
            <tr><th>Adresse</th><td colSpan={3}>{p.address || '—'}</td></tr>
            <tr><th>Commune / ville</th><td>{p.commune || p.city || '—'}</td><th>Région</th><td>{p.region || '—'}</td></tr>
            <tr><th>Contact urgence</th><td>{p.emergency_full_name || form?.emergency_full_name || '—'}</td><th>Tél. contact</th><td>{p.emergency_phone || form?.emergency_phone || '—'}</td></tr>
          </tbody>
        </table>
      </section>

      {payer && (
        <section className="print-registration-section print-registration-section--compact">
          <h2>Payeur</h2>
          <table className="print-registration-table print-registration-table--compact">
            <tbody>
              <tr><th>Type de payeur</th><td colSpan={3}>{payerTypeLabel(payer.payer_type)}</td></tr>
              {payer.insurance_company && (
                <tr><th>Assurance</th><td>{payer.insurance_company}</td><th>N° assurance</th><td>{payer.insurance_number || '—'}</td></tr>
              )}
              {payer.company_name && <tr><th>Entreprise</th><td colSpan={3}>{payer.company_name}</td></tr>}
            </tbody>
          </table>
        </section>
      )}

      <PrintDocumentFooter printedBy={printedBy} department="Réception" pageLabel="Page 1 sur 1" />
    </div>
  );
}
