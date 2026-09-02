import { useCallback, useEffect, useMemo, useState } from 'react';
import clinicalApi from '../../../services/clinicalApi.js';
import { useConfirm } from '../../../contexts/ConfirmContext.jsx';
import { formatApiError } from '../../../utils/apiError.js';
import { formatClinicalDate, formatGNF } from '../../../utils/clinicalPresentation.js';

const initialDetails = { refund_method: 'cash', reason: 'returned', reason_notes: '', recipient_name: '', recipient_phone: '' };
const reasonLabels = { returned: 'Produit retourné', billing_error: 'Erreur de facturation', duplicate: 'Paiement en double', quality_issue: 'Problème de qualité', other: 'Autre motif' };

export default function PharmacyRefundsTab() {
  const confirm = useConfirm();
  const [eligible, setEligible] = useState([]);
  const [history, setHistory] = useState([]);
  const [selected, setSelected] = useState(null);
  const [lines, setLines] = useState([]);
  const [details, setDetails] = useState(initialDetails);
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(false);
  const [printingId, setPrintingId] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setError('');
    try {
      const [eligibleResponse, historyResponse] = await Promise.all([
        clinicalApi.pharmacyRefundEligible(), clinicalApi.pharmacyRefunds(),
      ]);
      setEligible(eligibleResponse.data || []);
      setHistory(historyResponse.data || []);
    } catch (err) { setError(formatApiError(err, 'Chargement des remboursements impossible')); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) return eligible;
    return eligible.filter((row) => `${row.patient_name} ${row.request_number}`.toLowerCase().includes(value));
  }, [eligible, query]);
  const previewAmount = useMemo(() => {
    if (!selected) return 0;
    const gross = lines.filter((line) => line.selected).reduce((sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_price_gnf || 0), 0);
    const invoiceGross = selected.items.reduce((sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_price_gnf || 0), 0);
    return invoiceGross ? Math.min(selected.refundable_gnf, Math.round(gross * selected.paid_amount_gnf / invoiceGross)) : 0;
  }, [lines, selected]);

  const chooseInvoice = (row) => {
    setSelected(row);
    setLines(row.items.map((item, index) => ({ ...item, key: `${item.inventory_item_id || item.product_name}-${index}`, selected: false, maxQuantity: Number(item.quantity || 1), quantity: 1, return_to_stock: false })));
    setDetails(initialDetails); setError(''); setMessage('');
  };
  const updateLine = (key, patch) => setLines((current) => current.map((line) => line.key === key ? { ...line, ...patch } : line));

  const submit = async (event) => {
    event.preventDefault();
    const items = lines.filter((line) => line.selected).map((line) => ({ inventory_item_id: line.inventory_item_id || null, product_name: line.product_name, quantity: Number(line.quantity), return_to_stock: Boolean(line.return_to_stock) }));
    if (!items.length) { setError('Sélectionnez au moins un produit à rembourser.'); return; }
    if (!details.reason_notes.trim() || !details.recipient_name.trim() || !details.recipient_phone.trim()) { setError('Renseignez le motif détaillé et la personne qui reçoit le remboursement.'); return; }
    const accepted = await confirm({ title: 'Confirmer le remboursement', message: `${selected.patient_name} recevra environ ${formatGNF(previewAmount)}. Cette opération financière sera enregistrée dans l’audit.`, confirmLabel: `Rembourser ${formatGNF(previewAmount)}`, cancelLabel: 'Vérifier', tone: 'danger' });
    if (!accepted) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const { data } = await clinicalApi.createPharmacyRefund({ charge_id: selected.charge_id, items, ...details });
      setMessage(`Remboursement ${data.refund_number} enregistré : ${formatGNF(data.amount_gnf)}.`);
      setSelected(null); setLines([]); await load();
    } catch (err) { setError(formatApiError(err, 'Remboursement impossible')); }
    finally { setBusy(false); }
  };
  const printReceipt = async (row) => {
    setPrintingId(row.id); setError('');
    try { await clinicalApi.downloadPharmacyRefundReceipt(row.id, `remboursement-${row.refund_number}.pdf`); }
    catch (err) { setError(formatApiError(err, 'Impression du reçu impossible')); }
    finally { setPrintingId(null); }
  };

  return <section className="pharmacy-refunds" aria-labelledby="pharmacy-refunds-title">
    <div className="pharmacy-panel-header"><div><p className="pharmacy-section-kicker">Contrôle financier</p><h2 id="pharmacy-refunds-title">Remboursements patients</h2><p>Retrouvez une facture payée, vérifiez les produits, puis confirmez le remboursement.</p></div></div>
    {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}
    {message && <p className="clinical-message clinical-message--ok" role="status">{message}</p>}
    <ol className="pharmacy-refund-steps" aria-label="Étapes du remboursement"><li className={!selected ? 'is-active' : 'is-done'}><span>1</span>Facture</li><li className={selected ? 'is-active' : ''}><span>2</span>Produits et motif</li><li><span>3</span>Confirmation</li></ol>

    {!selected ? <article className="pharmacy-panel pharmacy-refund-picker"><label>Rechercher une facture payée<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Patient ou N° demande…" /></label><div className="pharmacy-refund-invoices">{filtered.length ? filtered.map((row) => <button type="button" key={row.charge_id} onClick={() => chooseInvoice(row)}><span><strong>{row.patient_name}</strong><small>{row.request_number} · {formatClinicalDate(row.created_at)}</small></span><span><small>Disponible</small><strong>{formatGNF(row.refundable_gnf)}</strong></span></button>) : <p className="pharmacy-empty">Aucune facture payée remboursable.</p>}</div></article> :
      <form className="pharmacy-panel pharmacy-refund-form" onSubmit={submit}>
        <header><div><p className="pharmacy-section-kicker">Facture sélectionnée</p><h3>{selected.patient_name}</h3><p>{selected.request_number} · remboursable : <strong>{formatGNF(selected.refundable_gnf)}</strong></p></div><button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => setSelected(null)}>Changer de facture</button></header>
        <fieldset><legend>Produits à rembourser</legend>{lines.map((line) => <div className="pharmacy-refund-line" key={line.key}><label className="pharmacy-refund-check"><input type="checkbox" checked={line.selected} onChange={(event) => updateLine(line.key, { selected: event.target.checked })}/><span><strong>{line.product_name}</strong><small>{formatGNF(line.unit_price_gnf)} / unité · acheté : {line.maxQuantity}</small></span></label><label>Quantité<input type="number" min="1" max={line.maxQuantity} value={line.quantity} disabled={!line.selected} onChange={(event) => updateLine(line.key, { quantity: Math.max(1, Math.min(line.maxQuantity, Number(event.target.value) || 1)) })}/></label><label className="pharmacy-refund-stock"><input type="checkbox" checked={line.return_to_stock} disabled={!line.selected || !line.inventory_item_id} onChange={(event) => updateLine(line.key, { return_to_stock: event.target.checked })}/>Remettre en stock (scellé et réutilisable)</label></div>)}</fieldset>
        <div className="pharmacy-refund-fields"><label>Motif<select value={details.reason} onChange={(event) => setDetails({ ...details, reason: event.target.value })}>{Object.entries(reasonLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label>Mode de remboursement<select value={details.refund_method} onChange={(event) => setDetails({ ...details, refund_method: event.target.value })}><option value="cash">Espèces</option><option value="orange_money">Orange Money</option><option value="bank_transfer">Virement</option><option value="card">Carte</option><option value="insurance">Assurance</option></select></label><label>Nom du bénéficiaire<input required value={details.recipient_name} onChange={(event) => setDetails({ ...details, recipient_name: event.target.value })}/></label><label>Téléphone du bénéficiaire<input required value={details.recipient_phone} onChange={(event) => setDetails({ ...details, recipient_phone: event.target.value })}/></label><label className="pharmacy-refund-notes">Explication détaillée<textarea required minLength="3" value={details.reason_notes} onChange={(event) => setDetails({ ...details, reason_notes: event.target.value })}/></label></div>
        <footer><div><small>Montant estimé</small><strong>{formatGNF(previewAmount)}</strong><p>Le serveur recalcule le montant exact et bloque tout dépassement.</p></div><button className="clinical-btn clinical-btn--danger" type="submit" disabled={busy || previewAmount <= 0}>{busy ? 'Enregistrement…' : 'Vérifier et rembourser'}</button></footer>
      </form>}

    <article className="pharmacy-panel"><h3>Historique des remboursements</h3><div className="pharmacy-table-wrap" role="region" aria-label="Historique des remboursements" tabIndex="0"><table className="pharmacy-table"><thead><tr><th>N°</th><th>Date</th><th>Patient</th><th>Montant</th><th>Motif</th><th>Reçu</th></tr></thead><tbody>{history.length ? history.map((row) => <tr key={row.id}><td><strong>{row.refund_number}</strong></td><td>{formatClinicalDate(row.created_at)}</td><td>{row.patient_name}</td><td>{formatGNF(row.amount_gnf)}</td><td>{reasonLabels[row.reason] || row.reason}</td><td><button type="button" className="clinical-btn clinical-btn--secondary pharmacy-compact-action" disabled={printingId === row.id} onClick={() => printReceipt(row)}>{printingId === row.id ? 'Ouverture…' : 'Imprimer le reçu'}</button></td></tr>) : <tr><td colSpan="6" className="pharmacy-empty">Aucun remboursement enregistré.</td></tr>}</tbody></table></div></article>
  </section>;
}
