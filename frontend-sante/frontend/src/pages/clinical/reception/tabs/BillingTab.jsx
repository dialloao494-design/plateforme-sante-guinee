import { formatGNF } from '../../../../utils/appointmentPresentation.js';
import {
  FIELD_HINTS,
  INVOICE_PAYMENT_NOTICE,
  PATIENT_REQUIRED_NOTICE,
  PAYMENT_METHODS,
} from '../constants.js';
import PatientContextPanel from '../components/PatientContextPanel.jsx';
import {
  AmountDisplay,
  DisplayField,
  FormNotice,
  ReadOnlyDisplay,
} from '../components/FormPrimitives.jsx';
import { invoiceStatusLabel, methodLabel } from '../utils.js';

export default function BillingTab({
  patientPayerLabel,
  activeInvoice,
  activeMeta,
  addBillingLine,
  addEmergencyConsultation,
  addImagingExam,
  addPaymentLine,
  addSpecializedConsultation,
  admissionForm,
  billingCatalog,
  billingDepartments,
  billingForm,
  billingLineItems,
  billingServiceRequestId,
  billingSubtotal,
  draftExemptionAmount,
  draftNetTotal,
  draftPaymentTotal,
  draftRemainingAfterPay,
  filteredLabTests,
  handleCreateInvoice,
  handlePayment,
  imagingExaminations,
  invoices,
  labSearchQ,
  loadServiceRequestIntoBilling,
  loading,
  loadingBillingServiceRequest,
  patientDisplayName,
  patientDossier,
  paymentLines,
  printInvoiceReceipt,
  removeBillingLine,
  removePaymentLine,
  renderSpecialtyPicker,
  selectInvoice,
  selectedImaging,
  selectedPatient,
  selectedSpecialty,
  servicePrestations,
  setBillingServiceRequestId,
  setLabSearchQ,
  setSelectedImaging,
  specializedSpecialties,
  surgicalActs,
  syncSpecialtyCode,
  updateBilling,
  updatePaymentLine,
}) {
  return (
        <section className="reception-his-panel">
          <PatientContextPanel selectedPatient={selectedPatient} patientPayerLabel={patientPayerLabel} />
          <div className="clinical-card reception-his-form-sheet">
            <h2>Facturation</h2>
            <FormNotice>{!selectedPatient ? PATIENT_REQUIRED_NOTICE : null}</FormNotice>

            {selectedPatient && invoices.length > 0 && (
              <label className="reception-his-invoice-select">
                Facture du patient
                <select value={activeInvoice?.id || ''} onChange={(e) => selectInvoice(e.target.value)}>
                  <option value="">— Nouvelle facture —</option>
                  {invoices.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.invoice_number} · {invoiceStatusLabel(i.status)}
                    </option>
                  ))}
                </select>
              </label>
            )}

            <fieldset>
              <legend>Facture</legend>
              <div className="reception-his-form-row reception-his-form-row--4">
                <DisplayField
                  label="N° facture"
                  value={activeInvoice?.invoice_number || ''}
                  hint={activeInvoice?.invoice_number ? undefined : FIELD_HINTS.invoiceNumber}
                />
                <DisplayField label="N° dossier patient" value={patientDossier} />
                <DisplayField label="Nom et prénom" value={patientDisplayName} />
                <label>
                  Date de facturation
                  {activeInvoice ? (
                    <ReadOnlyDisplay value={(activeInvoice.issued_at || activeInvoice.created_at || '').slice(0, 10)} />
                  ) : (
                    <input
                      required
                      type="date"
                      value={billingForm.billing_date}
                      onChange={(e) => updateBilling({ billing_date: e.target.value })}
                    />
                  )}
                </label>
              </div>
              <div className="reception-his-form-row">
                <label>
                  Service concerné
                  {activeInvoice ? (
                    <ReadOnlyDisplay value={activeInvoice.department || ''} />
                  ) : (
                    <select value={billingForm.department} onChange={(e) => updateBilling({ department: e.target.value })}>
                      {billingDepartments.map((d) => <option key={d} value={d}>{d}</option>)}
                    </select>
                  )}
                </label>
              </div>
              {!activeInvoice && (
                <form className="reception-his-inline-create" onSubmit={handleCreateInvoice}>
                  <fieldset className="reception-his-nested-fieldset">
                    <legend>Demande de service enregistrée</legend>
                    <p className="clinical-hint">
                      Collez le N° de demande (DSR-…) pour l&apos;ajouter au tableau Produits / Services.
                    </p>
                    <div className="reception-his-search-inline">
                      <input
                        type="text"
                        value={billingServiceRequestId}
                        onChange={(e) => setBillingServiceRequestId(e.target.value)}
                        placeholder="Ex. DSR-001-000123"
                      />
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={loadServiceRequestIntoBilling}
                        disabled={loadingBillingServiceRequest || !billingServiceRequestId.trim()}
                      >
                        {loadingBillingServiceRequest ? 'Chargement…' : 'Ajouter à la facture'}
                      </button>
                    </div>
                  </fieldset>
                  <fieldset className="reception-his-nested-fieldset">
                    <legend>Service concerné / tarification</legend>
                    <p className="clinical-hint">
                      Sélectionnez le service ci-dessus, puis la spécialité ou l&apos;examen selon la fiche de tarifs AASMA.
                    </p>
                    {(billingForm.department === 'Consultation spécialisée'
                      || String(billingForm.department || '').startsWith('Consultation spécialisée')) && (
                      <div className="reception-his-specialty-picker">
                        {renderSpecialtyPicker('billing', { required: true })}
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addSpecializedConsultation}>
                          + Consultation spécialisée
                        </button>
                      </div>
                    )}
                    {(billingForm.department === 'Consultation urgences' || billingForm.department === 'Urgences') && (
                      <div className="reception-his-specialty-picker">
                        <label htmlFor="specialty-select-emergency">
                          Spécialité (tarif urgence)
                          <select
                            id="specialty-select-emergency"
                            value={admissionForm.specialty_code || selectedSpecialty}
                            onChange={(e) => syncSpecialtyCode(e.target.value)}
                          >
                            <option value="">Tarif général urgences…</option>
                            {specializedSpecialties.map((spec) => (
                              <option key={spec.code} value={spec.code}>
                                {spec.label} · {formatGNF(spec.emergency_price_gnf || 150000)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addEmergencyConsultation}>
                          + Consultation d&apos;urgences
                        </button>
                      </div>
                    )}
                    {billingForm.department === 'Consultation externe' && (
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => {
                          const svc = (billingCatalog?.consultation_services || []).find((c) => c.code === 'outpatient_consultation');
                          addBillingLine({
                            charge_type: svc?.charge_type || 'consultation',
                            description: svc?.label || 'Consultation externe',
                            quantity: 1,
                            unit_price_gnf: svc?.price_gnf || 100000,
                            catalog_code: svc?.code || 'outpatient_consultation',
                          });
                        }}
                      >
                        + Consultation externe · {formatGNF((billingCatalog?.consultation_services || []).find((c) => c.code === 'outpatient_consultation')?.price_gnf || 100000)}
                      </button>
                    )}
                    {billingForm.department === 'Hospitalisation' && (
                      <button
                        type="button"
                        className="clinical-btn clinical-btn--secondary"
                        onClick={() => {
                          const svc = (billingCatalog?.consultation_services || []).find((c) => c.code === 'hospitalization');
                          addBillingLine({
                            charge_type: svc?.charge_type || 'hospitalization',
                            description: svc?.label || 'Hospitalisation',
                            quantity: 1,
                            unit_price_gnf: svc?.price_gnf || 350000,
                            catalog_code: svc?.code || 'hospitalization',
                          });
                        }}
                      >
                        + Hospitalisation · {formatGNF((billingCatalog?.consultation_services || []).find((c) => c.code === 'hospitalization')?.price_gnf || 350000)}
                      </button>
                    )}
                    {billingForm.department === 'Chirurgie' && surgicalActs.length > 0 && (
                      <div className="reception-his-service-options">
                        {surgicalActs.map((act) => (
                          <button
                            key={act.code}
                            type="button"
                            className="clinical-btn clinical-btn--secondary"
                            onClick={() => addBillingLine({
                              charge_type: 'procedure',
                              description: act.label,
                              quantity: 1,
                              unit_price_gnf: act.price_gnf || 0,
                              catalog_code: act.code,
                            })}
                          >
                            + {act.label} · {formatGNF(act.price_gnf || 0)}
                          </button>
                        ))}
                      </div>
                    )}
                    {(billingForm.department === 'Imagerie médicale') && imagingExaminations.length > 0 && (
                      <div className="reception-his-specialty-picker">
                        <label>
                          Imagerie médicale — examen
                          <select value={selectedImaging} onChange={(e) => setSelectedImaging(e.target.value)}>
                            <option value="">Choisir un examen…</option>
                            {imagingExaminations.map((exam) => (
                              <option key={exam.code} value={exam.code}>{exam.label} · {formatGNF(exam.price_gnf)}</option>
                            ))}
                          </select>
                        </label>
                        <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addImagingExam}>
                          + Imagerie médicale
                        </button>
                      </div>
                    )}
                    {(billingForm.department === 'Soins infirmiers') && (
                      <div className="reception-his-service-options">
                        {servicePrestations.map((svc) => (
                          <button
                            key={svc.code}
                            type="button"
                            className="clinical-btn clinical-btn--secondary"
                            onClick={() => addBillingLine({
                              charge_type: 'procedure',
                              description: svc.label,
                              quantity: 1,
                              unit_price_gnf: svc.price_gnf || 0,
                              catalog_code: svc.code,
                            })}
                          >
                            + {svc.label} · {formatGNF(svc.price_gnf || 0)}
                          </button>
                        ))}
                      </div>
                    )}
                    {(billingForm.department === 'Laboratoire' || !['Consultation spécialisée', 'Consultation urgences', 'Urgences', 'Imagerie médicale', 'Soins infirmiers'].includes(billingForm.department)) && (
                      <>
                        <label>
                          Rechercher examen laboratoire
                          <input
                            type="search"
                            value={labSearchQ}
                            onChange={(e) => setLabSearchQ(e.target.value)}
                            placeholder="Nom ou code analyse…"
                          />
                        </label>
                        {filteredLabTests.length > 0 && (
                          <ul className="reception-his-lab-search-results">
                            {filteredLabTests.map((test) => (
                              <li key={test.code}>
                                <button
                                  type="button"
                                  onClick={() => addBillingLine({
                                    charge_type: 'laboratory',
                                    description: `${test.name} (${test.code})`,
                                    quantity: 1,
                                    unit_price_gnf: test.price_gnf || 0,
                                    catalog_code: test.code,
                                  })}
                                >
                                  {test.name} · {formatGNF(test.price_gnf || 0)}
                                </button>
                              </li>
                            ))}
                          </ul>
                        )}
                      </>
                    )}
                  </fieldset>
                  <table className="reception-his-billing-lines">
                    <thead>
                      <tr>
                        <th>Produit / Service</th>
                        <th>Qté</th>
                        <th>Prix U</th>
                        <th>Total</th>
                        <th scope="col">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {billingLineItems.length === 0 ? (
                        <tr><td colSpan={5} className="reception-his-empty-row">Aucune prestation ajoutée.</td></tr>
                      ) : (
                        billingLineItems.map((line) => (
                          <tr key={line.id}>
                            <td>{line.description}</td>
                            <td>{line.quantity}</td>
                            <td>{formatGNF(line.unit_price_gnf)}</td>
                            <td>{formatGNF(Number(line.quantity || 1) * Number(line.unit_price_gnf || 0))}</td>
                            <td>
                              <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removeBillingLine(line.id)}>Retirer</button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                  <div className="reception-his-form-row reception-his-form-row--3">
                    <label>
                      Montant total
                      <AmountDisplay amountGnf={billingSubtotal || null} />
                    </label>
                    <label>
                      Exemption (%)
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="1"
                        value={billingForm.exemption_percent}
                        onChange={(e) => updateBilling({ exemption_percent: e.target.value })}
                      />
                    </label>
                    <label>
                      Montant exemption
                      <AmountDisplay amountGnf={draftExemptionAmount || null} />
                    </label>
                  </div>
                  {Number(billingForm.exemption_percent || 0) > 0 && (
                    <label>
                      Motif d&apos;exemption (obligatoire)
                      <input
                        type="text"
                        value={billingForm.exemption_reason || ''}
                        onChange={(e) => updateBilling({ exemption_reason: e.target.value })}
                        placeholder="Ex. : tarification sociale, prise en charge…"
                        required
                      />
                    </label>
                  )}
                  <div className="reception-his-form-row reception-his-form-row--2">
                    <label>
                      Nouveau total
                      <AmountDisplay amountGnf={draftNetTotal || null} />
                    </label>
                  </div>
                  <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient || billingLineItems.length === 0}>
                    {loading ? 'Enregistrement…' : 'Créer facture'}
                  </button>
                </form>
              )}
              {activeInvoice && (activeInvoice.items || []).length > 0 && (
                <table className="reception-his-billing-lines">
                  <thead>
                    <tr>
                      <th>Produit / Service</th>
                      <th>Qté</th>
                      <th>Prix U</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                {(activeInvoice.items || []).map((item, index) => (
                  <tr key={item.id || `${item.catalog_code || item.description}-${index}`}>
                        <td>{item.description}</td>
                        <td>{item.quantity}</td>
                        <td>{formatGNF(item.unit_price_gnf ?? item.unit_price ?? 0)}</td>
                        <td>{formatGNF(item.amount_gnf ?? (Number(item.quantity || 1) * Number(item.unit_price_gnf ?? item.unit_price ?? 0)))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </fieldset>

            <fieldset>
              <legend>Paiement</legend>
              {!activeInvoice && (
                <FormNotice>{INVOICE_PAYMENT_NOTICE}</FormNotice>
              )}
              <div className="reception-his-form-row reception-his-form-row--4">
                <label>
                  Montant total
                  <AmountDisplay amountGnf={activeInvoice ? activeMeta?.subtotal : (billingSubtotal || null)} />
                </label>
                <label>
                  Exemption (%)
                  <ReadOnlyDisplay value={activeInvoice ? `${activeMeta?.exemptionPercent || 0}` : String(billingForm.exemption_percent || 0)} />
                </label>
                <label>
                  Montant exemption
                  <AmountDisplay amountGnf={activeInvoice ? activeMeta?.exemptionAmount : (draftExemptionAmount || null)} />
                </label>
                <label>
                  Nouveau total
                  <AmountDisplay amountGnf={activeInvoice ? activeMeta?.total : (draftNetTotal || null)} />
                </label>
              </div>
              <div className="reception-his-form-row reception-his-form-row--3">
                <label>
                  Montant reçu
                  <AmountDisplay amountGnf={activeInvoice ? (activeMeta?.paid ?? 0) : null} />
                </label>
                <label>
                  Reste à payer
                  <AmountDisplay amountGnf={activeInvoice ? activeMeta?.remaining : null} />
                </label>
                {activeInvoice && draftPaymentTotal > 0 && (
                  <>
                    <label>
                      Total saisi (lignes)
                      <AmountDisplay amountGnf={draftPaymentTotal} />
                    </label>
                    <label>
                      Reste après saisie
                      <AmountDisplay amountGnf={draftRemainingAfterPay} />
                    </label>
                  </>
                )}
              </div>
              {activeInvoice ? (
                <form onSubmit={handlePayment}>
                  <p className="clinical-hint">Ajoutez une ou plusieurs lignes de paiement (Orange Money, Espèces, Virement, Assurance…).</p>
                  <table className="reception-his-billing-lines">
                    <thead>
                      <tr>
                        <th>Mode de paiement</th>
                        <th>Montant (GNF)</th>
                        <th>Référence</th>
                        <th scope="col">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paymentLines.map((line) => (
                        <tr key={line.id}>
                          <td>
                            <select
                              value={line.payment_method}
                              onChange={(e) => updatePaymentLine(line.id, { payment_method: e.target.value })}
                            >
                              {PAYMENT_METHODS.map((m) => (
                                <option key={m.value} value={m.value}>{m.label}</option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <input
                              type="text"
                              inputMode="numeric"
                              pattern="[0-9]*"
                              value={line.amount_gnf}
                              onChange={(e) => updatePaymentLine(line.id, { amount_gnf: e.target.value.replace(/[^\d]/g, '') })}
                              placeholder="Montant"
                            />
                          </td>
                          <td>
                            <input
                              value={line.reference}
                              onChange={(e) => updatePaymentLine(line.id, { reference: e.target.value })}
                              placeholder="N° transaction…"
                            />
                          </td>
                          <td>
                            <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => removePaymentLine(line.id)}>
                              ×
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="clinical-actions reception-his-payment-actions">
                    <button type="button" className="clinical-btn clinical-btn--secondary" onClick={addPaymentLine}>
                      + Ligne de paiement
                    </button>
                    <button type="submit" className="clinical-btn" disabled={loading || !selectedPatient}>
                      Enregistrer le(s) paiement(s)
                    </button>
                  </div>
                </form>
              ) : (
                <FormNotice>{INVOICE_PAYMENT_NOTICE}</FormNotice>
              )}
            </fieldset>

            <fieldset className="reception-his-payment-history">
              <legend>Historique des paiements</legend>
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Montant</th>
                    <th>Mode</th>
                    <th>Référence</th>
                  </tr>
                </thead>
                <tbody>
                  {(activeInvoice?.payments || []).length === 0 ? (
                    <tr>
                      <td colSpan={4} className="reception-his-empty-row">Aucun paiement enregistré.</td>
                    </tr>
                  ) : (
                    (activeInvoice.payments || []).map((p) => (
                      <tr key={p.id}>
                        <td>{new Date(p.paid_at).toLocaleString('fr-FR')}</td>
                        <td>{formatGNF(p.amount_gnf || 0)}</td>
                        <td>{methodLabel(PAYMENT_METHODS, p.payment_method)}</td>
                        <td>{p.reference || '—'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              {activeInvoice && (
                <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => printInvoiceReceipt(activeInvoice.id)}>
                  Imprimer reçu
                </button>
              )}
            </fieldset>
          </div>
        </section>
  );
}
