import { LAB_TEMPLATES, LAB_TEMPLATE_OPTIONS } from '../../../data/labReportTemplates.js';
import PrintClinicHeader from '../../../components/print/PrintClinicHeader.jsx';
import PrintDocumentFooter from '../../../components/print/PrintDocumentFooter.jsx';
import { ReadOnlyDisplay } from './LabPatientOverview.jsx';
import { VALIDATION_STATUSES } from './labDomain.js';

function SummaryTable({ rows }) {
  return (
    <table className="lab-his-results-table">
      <thead><tr><th>Paramètre</th><th>Résultat</th><th>Référence</th></tr></thead>
      <tbody>{rows.map((row, index) => (
        <tr key={`${row.parameter}-${index}`}><td>{row.parameter}</td><td>{row.result}</td><td>{row.reference || row.ref_male || '—'}</td></tr>
      ))}</tbody>
    </table>
  );
}

function ValidationSummary({ summary, printedBy }) {
  if (!summary) return null;
  const details = (
    <dl className="lab-his-summary-grid">
      <div><dt>Patient</dt><dd>{summary.patient} · N° {summary.patientNumber}</dd></div>
      <div><dt>Examen</dt><dd>{summary.exam}</dd></div><div><dt>Technicien</dt><dd>{summary.technician}</dd></div>
      <div><dt>Date / heure</dt><dd>{summary.date} {summary.time}</dd></div><div><dt>Statut</dt><dd>{summary.status}</dd></div>
    </dl>
  );
  return (
    <>
      <section className="lab-his-validation-summary" aria-live="polite">
        <h4>Résumé de validation</h4>{details}
        {summary.macro && <p className="lab-his-summary-macro"><strong>Aspect macroscopique :</strong> {summary.macro}</p>}
        {summary.observations && <p className="lab-his-summary-macro"><strong>Observations :</strong> {summary.observations}</p>}
        <div className="lab-his-results-wrap"><SummaryTable rows={summary.rows} /></div>
        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => window.print()}>Imprimer le résumé de validation</button>
      </section>
      <div className="lab-his-validation-summary-print" aria-hidden="true">
        <PrintClinicHeader documentTitle="Résumé de validation laboratoire" compact />{details}
        {summary.observations && <p><strong>Observations :</strong> {summary.observations}</p>}
        <SummaryTable rows={summary.rows} />
        <PrintDocumentFooter printedBy={printedBy} department="Laboratoire" />
      </div>
    </>
  );
}

export default function LabResultsWorkspace({
  activeOrder, activeTemplateId, addResultRow, applyLabTemplate, ecbuMacro, lastResultId, loading,
  onPrintReport, onSubmitResults, printedBy, removeResultRow, resultRows, selectedPatient,
  setEcbuMacro, setValidationForm, updateResultRow, validationForm, validationSummary,
}) {
  return (
    <>
      <section className="lab-his-workflow-card lab-his-workflow-card--templates">
        <h3>Modèles de rapport officiels</h3>
        <p className="clinical-hint">Sélectionnez le modèle validé par la clinique (Hémogramme, BU ou ECBU). Les paramètres et valeurs de référence se chargent automatiquement.</p>
        <div className="lab-his-template-picker" role="group" aria-label="Modèles de rapport">
          {LAB_TEMPLATE_OPTIONS.map((option) => (
            <button key={option.id} type="button" className={`clinical-btn clinical-btn--secondary lab-his-template-btn${activeTemplateId === option.id ? ' lab-his-template-btn--active' : ''}`} onClick={() => applyLabTemplate(option.id)} disabled={loading || !selectedPatient}>{option.label}</button>
          ))}
        </div>
        {!selectedPatient && <p className="reception-his-form-notice">Sélectionnez d&apos;abord un patient pour charger un modèle.</p>}
        {activeTemplateId === 'ecbu' && <label className="lab-his-ecbu-macro-field">Aspect macroscopique<textarea rows={2} value={ecbuMacro} onChange={(event) => setEcbuMacro(event.target.value)} placeholder="Ex. urine jaune clair, culot léger…" /></label>}
        {activeTemplateId === 'hemogram' && LAB_TEMPLATES.hemogram?.note && <p className="clinical-hint">{LAB_TEMPLATES.hemogram.note}</p>}
      </section>

      <section className="lab-his-workflow-card lab-his-workflow-card--results">
        <h3>Résultats</h3>
        <p className="clinical-lead lab-his-active-order">{activeOrder ? <>Examen actif : <strong>{activeOrder.test_name}</strong>{activeTemplateId && LAB_TEMPLATES[activeTemplateId] && <span className="clinical-hint"> · Modèle : {LAB_TEMPLATES[activeTemplateId].title}</span>}</> : 'Sélectionnez une commande pour saisir les résultats.'}</p>
        <div className="lab-his-results-wrap"><table className={`lab-his-results-table${activeTemplateId === 'hemogram' ? ' lab-his-results-table--hemogram' : ''}`}>
          <thead><tr><th>Paramètre</th><th>Résultat</th>{activeTemplateId === 'hemogram' ? <><th>Unités</th><th>Enfant</th><th>Homme</th><th>Femme</th></> : activeTemplateId === 'bu' ? <th>Valeurs de référence</th> : <><th>Valeurs de référence</th><th>Unité</th></>}<th scope="col">Actions</th></tr></thead>
          <tbody>{resultRows.map((row, index) => (
            <tr key={index}>
              <td><input value={row.parameter} onChange={(event) => updateResultRow(index, 'parameter', event.target.value)} placeholder="Ex. Glucose…" readOnly={Boolean(activeTemplateId)} /></td>
              <td><input value={row.result} onChange={(event) => updateResultRow(index, 'result', event.target.value)} placeholder="Valeur…" /></td>
              {activeTemplateId === 'hemogram' ? <><td><ReadOnlyDisplay value={row.unit} /></td><td><ReadOnlyDisplay value={row.ref_child} /></td><td><ReadOnlyDisplay value={row.ref_male} /></td><td><ReadOnlyDisplay value={row.ref_female} /></td></> : <>
                <td><input value={row.reference} onChange={(event) => updateResultRow(index, 'reference', event.target.value)} placeholder="Ex. 0,7 – 1,1 g/L…" readOnly={Boolean(activeTemplateId)} /></td>
                {activeTemplateId !== 'bu' && <td><input value={row.unit} onChange={(event) => updateResultRow(index, 'unit', event.target.value)} placeholder="Ex. g/L…" readOnly={Boolean(activeTemplateId)} /></td>}
              </>}
              <td>{!activeTemplateId && <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removeResultRow(index)} aria-label={`Supprimer la ligne de résultat ${index + 1}`}>×</button>}</td>
            </tr>
          ))}</tbody>
        </table></div>
        {!activeTemplateId && <button type="button" className="clinical-btn clinical-btn--secondary lab-his-add-row" onClick={addResultRow}>+ Ajouter une ligne</button>}
      </section>

      <section className="lab-his-workflow-card lab-his-workflow-card--validation">
        <h3>Validation</h3>
        <div className="reception-his-form-row reception-his-form-row--3">
          <label>Biologiste / technicien<input value={validationForm.technician} onChange={(event) => setValidationForm((previous) => ({ ...previous, technician: event.target.value }))} /></label>
          <label>Date de validation<input type="date" value={validationForm.validation_date} onChange={(event) => setValidationForm((previous) => ({ ...previous, validation_date: event.target.value }))} /></label>
          <label>Heure de validation<input type="time" value={validationForm.validation_time} onChange={(event) => setValidationForm((previous) => ({ ...previous, validation_time: event.target.value }))} /></label>
        </div>
        <div className="lab-his-status-options" role="radiogroup" aria-label="Statut">{VALIDATION_STATUSES.map((status) => <label key={status.value}><input type="radio" name="lab-status" checked={validationForm.status === status.value} onChange={() => setValidationForm((previous) => ({ ...previous, status: status.value }))} />{status.label}</label>)}</div>
        <label className="lab-his-notes-field">Observations / notes<textarea rows={3} value={validationForm.observations} onChange={(event) => setValidationForm((previous) => ({ ...previous, observations: event.target.value }))} placeholder="Notes cliniques, commentaires…" /></label>
        <div className="lab-his-validation-actions">
          <button type="button" className="clinical-btn lab-his-workflow-action" onClick={onSubmitResults} disabled={loading}>{loading ? 'Enregistrement…' : 'Enregistrer les résultats'}</button>
          {lastResultId && <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => onPrintReport(lastResultId)} disabled={loading}>Imprimer le rapport</button>}
        </div>
        <ValidationSummary summary={validationSummary} printedBy={printedBy} />
      </section>
    </>
  );
}
