import {
  FIELD_HINTS,
  PATIENT_REQUIRED_NOTICE,
  REFUND_METHODS,
  REFUND_REASONS,
} from '../constants.js';
import PatientContextPanel from '../components/PatientContextPanel.jsx';
import {
  AmountDisplay,
  DisplayField,
  FormNotice,
  GeneratedIdBanner,
  PaymentMethodRadios,
  ReadOnlyDisplay,
} from '../components/FormPrimitives.jsx';
import { formatGNF } from '../../../../utils/appointmentPresentation.js';
import { methodLabel, refundStatusLabel } from '../utils.js';

export default function RefundTab({
  patientPayerLabel,
  activeInvoice,
  filteredRefunds,
  handleRefund,
  invoiceSearchQ,
  lastRefund,
  loading,
  patientDisplayName,
  patientDossier,
  printRefundReceipt,
  refundForm,
  refundInvoices,
  selectInvoice,
  selectedPatient,
  setInvoiceSearchQ,
  updateRefund,
  updateRefundStatus,
}) {
  return (
        <section className="reception-his-panel">
          <PatientContextPanel selectedPatient={selectedPatient} patientPayerLabel={patientPayerLabel} />
          <div className="clinical-card reception-his-form-sheet">
            <h2>Remboursement</h2>
            <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>
            <GeneratedIdBanner label="N° remboursement généré" value={lastRefund?.refund_number} />

            <form onSubmit={handleRefund}>
              <fieldset>
                <legend>Demande de remboursement</legend>
                <div className="reception-his-form-row reception-his-form-row--4">
                  <DisplayField
                    label="N° remboursement"
                    value={lastRefund?.refund_number || ''}
                    hint={lastRefund?.refund_number ? undefined : FIELD_HINTS.refundNumber}
                  />
                  <DisplayField label="N° dossier patient" value={patientDossier} />
                  <DisplayField label="Nom et prénom" value={patientDisplayName} />
                  <label>
                    Service payé
                    <input value={refundForm.service_paid_for} onChange={(e) => updateRefund({ service_paid_for: e.target.value })} />
                  </label>
                </div>
                <div className="reception-his-form-row reception-his-form-row--2">
                  <label>
                    Facture originale *
                    <ReadOnlyDisplay value={refundForm.invoice_id && activeInvoice ? (activeInvoice.invoice_number || '') : ''} />
                    {selectedPatient ? (
                      <>
                        <input
                          type="search"
                          placeholder="Rechercher N° facture…"
                          value={invoiceSearchQ}
                          onChange={(e) => setInvoiceSearchQ(e.target.value)}
                        />
                        <select
                          required
                          value={refundForm.invoice_id}
                          onChange={(e) => { updateRefund({ invoice_id: e.target.value }); selectInvoice(e.target.value); }}
                        >
                          <option value="">— Sélectionner —</option>
                          {refundInvoices.map((i) => (
                            <option key={i.id} value={i.id}>
                              {i.invoice_number} · payé {formatGNF(i.paid_amount_gnf || 0)}
                            </option>
                          ))}
                        </select>
                      </>
                    ) : null}
                  </label>
                  <label>
                    Motif
                    <select value={refundForm.reason} onChange={(e) => updateRefund({ reason: e.target.value })}>
                      {REFUND_REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>
                  </label>
                </div>
                <div className="reception-his-form-row reception-his-form-row--3">
                  <label>
                    Total payé
                    <AmountDisplay amountGnf={refundForm.invoice_id ? (activeInvoice?.paid_amount_gnf ?? 0) : null} />
                  </label>
                  <label>
                    Montant consommé *
                    <input required type="number" min="0" value={refundForm.amount_consumed_gnf} onChange={(e) => updateRefund({ amount_consumed_gnf: e.target.value })} />
                  </label>
                  <label>
                    Montant à rembourser *
                    <input required type="number" min="0" value={refundForm.refund_amount_gnf} onChange={(e) => updateRefund({ refund_amount_gnf: e.target.value })} />
                  </label>
                </div>
                <div className="reception-his-form-row reception-his-form-row--2">
                  <label>
                    Bénéficiaire *
                    <input required value={refundForm.recipient_name} onChange={(e) => updateRefund({ recipient_name: e.target.value })} />
                  </label>
                  <label>
                    Tél. bénéficiaire *
                    <input required value={refundForm.recipient_phone} onChange={(e) => updateRefund({ recipient_phone: e.target.value })} />
                  </label>
                </div>
                {refundForm.reason === 'other' ? (
                  <label className="reception-his-notes-field">
                    Motif (préciser) *
                    <textarea
                      required
                      rows={2}
                      value={refundForm.reason_notes}
                      onChange={(e) => updateRefund({ reason_notes: e.target.value })}
                      placeholder="Saisir le motif du remboursement…"
                    />
                  </label>
                ) : (
                  <label className="reception-his-notes-field">
                    Notes
                    <textarea rows={2} value={refundForm.reason_notes} onChange={(e) => updateRefund({ reason_notes: e.target.value })} />
                  </label>
                )}
                <fieldset className="reception-his-nested-fieldset">
                  <legend>Mode de remboursement</legend>
                  <p className="clinical-hint">Indiquez comment le remboursement sera effectué (espèces, Orange Money, virement, etc.)</p>
                  <PaymentMethodRadios
                    name="refund_method"
                    value={refundForm.refund_method}
                    onChange={(v) => updateRefund({ refund_method: v })}
                    methods={REFUND_METHODS}
                  />
                </fieldset>
              </fieldset>
              <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>Soumettre remboursement</button>
            </form>

            <fieldset className="reception-his-payment-history">
              <legend>Historique des remboursements</legend>
              <table>
                <thead>
                  <tr>
                    <th>N° remboursement</th>
                    <th>Facture</th>
                    <th>Montant</th>
                    <th>Mode</th>
                    <th>Statut</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRefunds.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="reception-his-empty-row">Aucun remboursement enregistré.</td>
                    </tr>
                  ) : (
                    filteredRefunds.map((r) => (
                      <tr key={r.id}>
                        <td>{r.refund_number}</td>
                        <td>{r.invoice_number || '—'}</td>
                        <td>{formatGNF(r.refund_amount_gnf || 0)}</td>
                        <td>{methodLabel(REFUND_METHODS, r.refund_method)}</td>
                        <td>{refundStatusLabel(r.status)}</td>
                        <td>
                          {r.status === 'pending' && (
                            <div className="reception-his-refund-actions">
                              <button type="button" className="clinical-btn" onClick={() => updateRefundStatus(r.id, 'approved')}>Approuver</button>
                              <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => updateRefundStatus(r.id, 'rejected')}>Rejeter</button>
                            </div>
                          )}
                          {r.status === 'approved' && (
                            <button type="button" className="clinical-btn" onClick={() => updateRefundStatus(r.id, 'paid')}>Marquer payé</button>
                          )}
                          {r.status === 'paid' && (
                            <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => printRefundReceipt(r.id)}>Imprimer reçu</button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </fieldset>
          </div>
        </section>
  );
}
