import { formatGNF } from '../../../utils/clinicalPresentation.js';
import PharmacyMedicationAutocomplete from '../PharmacyMedicationAutocomplete.jsx';
import { FormNotice } from './PharmacyFormPrimitives.jsx';
import { medicationLineTotal, PATIENT_NOTICE } from './pharmacyDomain.js';

export default function PharmacyRequestEditor({ lines, inventory, loading, patient, requestTotal, onAddLine, onRemoveLine, onSelectStockItem, onSubmit, onUpdateLine }) {
  return (
    <section className="pharmacy-his-workflow-card" aria-labelledby="pharmacy-request-title">
      <h3 id="pharmacy-request-title">Demande de service</h3>
      {!patient && <FormNotice>{PATIENT_NOTICE}</FormNotice>}
      <div className="pharmacy-his-table-wrap" tabIndex="0" role="region" aria-label="Produits de la demande pharmaceutique">
        <table className="pharmacy-his-table">
          <thead><tr><th>Produit / Désignation</th><th>Quantité</th><th>Prix unitaire</th><th>Total</th><th aria-label="Actions" /></tr></thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={line.id}>
                <td>
                  <PharmacyMedicationAutocomplete
                    ariaLabel={`Produit ou médicament, ligne ${index + 1}`}
                    value={line.designation}
                    onChange={(value) => onUpdateLine(line.id, { designation: value, inventory_item_id: null })}
                    onSelectItem={(item) => onSelectStockItem(line.id, item)}
                    disabled={!patient}
                    inventory={inventory}
                  />
                </td>
                <td><input aria-label={`Quantité, ligne ${index + 1}`} type="number" inputMode="numeric" min="1" value={line.quantity} onChange={(event) => onUpdateLine(line.id, { quantity: event.target.value })} disabled={!patient} /></td>
                <td><input aria-label={`Prix unitaire, ligne ${index + 1}`} type="number" inputMode="numeric" min="0" step="500" value={line.unit_price_gnf} onChange={(event) => onUpdateLine(line.id, { unit_price_gnf: event.target.value })} disabled={!patient} /></td>
                <td className="pharmacy-his-total-cell">{formatGNF(medicationLineTotal(line))}</td>
                <td><button type="button" className="clinical-btn clinical-btn--secondary pharmacy-his-row-remove" onClick={() => onRemoveLine(line.id)} disabled={!patient} aria-label={`Supprimer la ligne ${index + 1}`}>×</button></td>
              </tr>
            ))}
          </tbody>
          <tfoot><tr><td colSpan={3} className="pharmacy-his-foot-label">Total</td><td colSpan={2} className="pharmacy-his-total-cell">{formatGNF(requestTotal)}</td></tr></tfoot>
        </table>
      </div>
      <div className="pharmacy-his-actions">
        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={onAddLine} disabled={!patient}>Ajouter une ligne</button>
        <button type="button" className="clinical-btn pharmacy-his-primary-action" onClick={onSubmit} disabled={loading || !patient}>
          {loading ? 'Enregistrement…' : 'Enregistrer la demande de service'}
        </button>
      </div>
    </section>
  );
}
