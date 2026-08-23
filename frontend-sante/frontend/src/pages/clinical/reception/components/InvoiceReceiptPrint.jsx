import PrintClinicHeader from '../../../../components/print/PrintClinicHeader.jsx';
import { formatGNF } from '../../../../utils/appointmentPresentation.js';
import { PAYMENT_METHODS } from '../constants.js';
import { methodLabel, patientFullName } from '../utils.js';

export default function InvoiceReceiptPrint({ invoice, patient, user, printedAt, active = false }) {
  if (!invoice) return null;
  const items = invoice.items || [];
  const payments = invoice.payments || [];
  const subtotal = Number(invoice.subtotal_amount_gnf ?? invoice.subtotal_gnf ?? 0);
  const exemption = Number(invoice.exemption_amount_gnf ?? 0);
  const total = Number(invoice.total_amount_gnf ?? invoice.total_gnf ?? Math.max(0, subtotal - exemption));
  const paid = Number(invoice.paid_amount_gnf ?? payments.reduce((sum, row) => sum + Number(row.amount_gnf || 0), 0));
  const remaining = Number(invoice.remaining_balance_gnf ?? Math.max(0, total - paid));
  const exemptionPercent = Number(invoice.exemption_percent || 0);
  const printDate = printedAt ? new Date(printedAt) : null;

  return (
    <article className={`reception-invoice-receipt-print${active ? ' clinical-print-target' : ''}`} aria-hidden="true">
      <PrintClinicHeader documentTitle="FACTURE" compact />
      <div className="reception-invoice-receipt-print__meta">
        <div>
          <p><strong>N° facture :</strong> {invoice.invoice_number || 'En attente de synchronisation'}</p>
          <p><strong>Patient :</strong> {patientFullName(patient) || invoice.patient_name || '—'}</p>
          <p><strong>N° dossier :</strong> {patient?.patient_number || invoice.patient_number || patient?.id || '—'}</p>
        </div>
        <div className="reception-invoice-receipt-print__meta-right">
          <p><strong>Date :</strong> {printDate ? printDate.toLocaleDateString('fr-FR') : '—'}</p>
          <p><strong>Heure :</strong> {printDate ? printDate.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '—'}</p>
          <p><strong>Caissier :</strong> {user?.full_name || user?.email || '—'}</p>
        </div>
      </div>
      <h2>Détail des prestations</h2>
      <table>
        <thead><tr><th>Description</th><th>Qté</th><th>Prix unitaire</th><th>Total</th></tr></thead>
        <tbody>
          {items.map((item, index) => {
            const quantity = Number(item.quantity || 1);
            const unitPrice = Number(item.unit_price_gnf ?? item.unit_price ?? 0);
            return (
              <tr key={item.id || `${item.catalog_code || item.description}-${index}`}>
                <td>{item.description || 'Prestation'}</td>
                <td>{quantity}</td>
                <td>{formatGNF(unitPrice)}</td>
                <td>{formatGNF(item.amount_gnf ?? quantity * unitPrice)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <h2>Récapitulatif paiement</h2>
      <table className="reception-invoice-receipt-print__summary">
        <tbody>
          <tr><th>Montant total</th><td>{formatGNF(subtotal)}</td></tr>
          <tr><th>Exemption</th><td>{exemptionPercent}%{exemption ? ` (${formatGNF(exemption)})` : ''}</td></tr>
          <tr><th>Montant payé</th><td>{formatGNF(paid)}</td></tr>
          <tr><th>Reste à payer</th><td>{formatGNF(remaining)}</td></tr>
        </tbody>
      </table>
      {payments.length > 0 && (
        <section>
          <h2>Détail des paiements</h2>
          <table className="reception-invoice-receipt-print__payments"><tbody>
            {payments.map((payment, index) => (
              <tr key={payment.id || index}>
                <td>{methodLabel(PAYMENT_METHODS, payment.payment_method)}{payment.reference ? ` · ${payment.reference}` : ''}</td>
                <td>{formatGNF(payment.amount_gnf || 0)}</td>
              </tr>
            ))}
          </tbody></table>
        </section>
      )}
      <footer>
        <span>Imprimé par : {user?.full_name || user?.email || '—'}</span>
        <span>Date : {printDate ? printDate.toLocaleDateString('fr-FR') : '—'} · Heure : {printDate ? printDate.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : '—'}</span>
        <span>Page 1</span>
        {invoice._offline_queued && <strong>Document local en attente de synchronisation</strong>}
      </footer>
    </article>
  );
}
