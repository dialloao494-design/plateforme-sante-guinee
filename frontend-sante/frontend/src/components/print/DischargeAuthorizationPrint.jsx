import PrintClinicHeader from './PrintClinicHeader.jsx';
import PrintDocumentFooter from './PrintDocumentFooter.jsx';
import './print-documents.css';

const genderLabel = (g) => {
  if (g === 'F' || g === 'Féminin' || g === 'f') return 'Féminin';
  if (g === 'M' || g === 'Masculin' || g === 'm') return 'Masculin';
  return g || '—';
};

const MARK = (checked) => (checked ? '☑' : '☐');

/**
 * Printable "Autorisation de sortie de patient" — matches clinic AASMA form.
 * `data` is filled from the doctor consultation + patient identity.
 */
export default function DischargeAuthorizationPrint({ data }) {
  if (!data) return null;
  const d = data;
  const motifs = d.motifs || {};

  return (
    <div className="print-discharge-auth">
      <PrintClinicHeader documentTitle="AUTORISATION DE SORTIE DE PATIENT" compact />

      <div className="print-discharge-auth__meta">
        <p>
          <strong>Autorisation de sortie de patient N° :</strong> {d.authorization_number || '—'}
        </p>
        <p>
          <strong>N° de dossier :</strong> {d.patient_number || '—'}
        </p>
        <p>
          <strong>Date :</strong> {d.discharge_date || '____ / ____ / ________'}
        </p>
        <p>
          <strong>Heure de sortie :</strong> {d.discharge_time || '____ h ____'}
        </p>
      </div>

      <section className="print-discharge-auth__section">
        <h2>Informations du patient</h2>
        <p>
          <strong>Nom et prénom :</strong> {d.full_name || '—'}
        </p>
        <p>
          <strong>Âge :</strong> {d.age != null && d.age !== '' ? `${d.age} ans` : '—'}
          {' · '}
          <strong>Sexe :</strong> {MARK(d.gender === 'M' || d.gender === 'Masculin')} Masculin
          {'  '}
          {MARK(d.gender === 'F' || d.gender === 'Féminin')} Féminin
          {d.gender && d.gender !== 'M' && d.gender !== 'F' && d.gender !== 'Masculin' && d.gender !== 'Féminin'
            ? ` (${genderLabel(d.gender)})`
            : ''}
        </p>
        <p>
          <strong>Service :</strong> {d.service || '—'}
        </p>
        <p>
          <strong>Médecin traitant :</strong> {d.doctor_name || '—'}
        </p>
      </section>

      <section className="print-discharge-auth__section">
        <h2>Motif de la sortie</h2>
        <div className="print-discharge-auth__motifs">
          <div>
            <p>{MARK(motifs.guerison)} Guérison / Fin de traitement</p>
            <p>{MARK(motifs.stabilise)} État de santé stabilisé</p>
            <p>{MARK(motifs.contre_avis)} Sortie contre avis médical (décharge signée)</p>
            <p>
              {MARK(motifs.autre_checked || Boolean(motifs.autre))} Autre : {motifs.autre || '________________'}
            </p>
          </div>
          <div>
            <p>{MARK(motifs.transfert)} Transfert vers un autre établissement de santé</p>
            <p>{MARK(motifs.demande_patient)} À la demande du patient ou de la famille</p>
            <p>{MARK(motifs.evacuation)} Évacuation</p>
          </div>
        </div>
      </section>

      <section className="print-discharge-auth__section">
        <h2>Décision médicale</h2>
        <p>
          Je soussigné(e), Pr, Dr <strong>{d.doctor_name || '________________'}</strong>, certifie que
          le patient est autorisé à quitter la Polyclinique AASMA à la date et à l&apos;heure indiquées
          ci-dessus.
        </p>
        {d.discharge_authorization ? <p className="print-discharge-auth__notes">{d.discharge_authorization}</p> : null}
      </section>

      <section className="print-discharge-auth__section">
        <p>
          <strong>Consignes de sortie :</strong> {d.discharge_instructions || '________________________________'}
        </p>
        <p>
          <strong>Traitement prescrit :</strong> {d.prescription_text || '________________________________'}
        </p>
        <p>
          <strong>Date du prochain rendez-vous :</strong>{' '}
          {d.next_appointment || '____ / ____ / ________ à ____ h ____'}
        </p>
      </section>

      <section className="print-discharge-auth__section">
        <h2>Situation administrative</h2>
        <p>{MARK(d.admin_formalities)} Toutes les formalités administratives sont régularisées.</p>
        <p>{MARK(d.invoice_paid)} La facture a été entièrement réglée.</p>
        <p>
          {MARK(Boolean(d.balance_remaining) || d.balance_checked)} Solde restant :{' '}
          {d.balance_remaining || '_________'} GNF
        </p>
      </section>

      {d.discharge_against_advice ? (
        <section className="print-discharge-auth__section">
          <h2>Décharge — Contre avis médical</h2>
          <p className="print-discharge-auth__notes">{d.discharge_against_advice}</p>
        </section>
      ) : null}

      <section className="print-discharge-auth__signatures">
        <div>
          <p>
            <strong>Médecin traitant</strong>
          </p>
          <p>Nom : {d.doctor_name || '____________'}</p>
          <p>Signature :</p>
        </div>
        <div>
          <p>
            <strong>Patient ou représentant légal</strong>
          </p>
          <p>Nom : ____________</p>
          <p>Signature :</p>
        </div>
        <div>
          <p>
            <strong>Service Admission / Facturation</strong>
          </p>
          <p>Nom : ____________</p>
          <p>Signature :</p>
        </div>
      </section>
      <p className="print-discharge-auth__stamp">Cachet du CHFMP-Polyclinique AASMA</p>

      <PrintDocumentFooter printedBy={d.printed_by || ''} department="Médecine" />
    </div>
  );
}
