import PrintClinicHeader from '../../../../components/print/PrintClinicHeader.jsx';
import { formatGNF } from '../../../../utils/appointmentPresentation.js';
import { PAYMENT_METHODS } from '../constants.js';
import { methodLabel, patientFullName } from '../utils.js';

export default function InvoiceReceiptPrint({ invoice, patient, user }) {
  if (!invoice) return null;
  const items = invoice.items || [];
  const payments = invoice.payments || [];
  const subtotal = Number(invoice.subtotal_amount_gnf ?? invoice.subtotal_gnf ?? 0);
  const exemption = Number(invoice.exemption_amount_gnf ?? 0);
  const total = Number(invoice.total_amount_gnf ?? invoice.total_gnf ?? Math.max(0, subtotal - exemption));
  const paid = Number(invoice.paid_amount_gnf ?? payments.reduce((sum, row) => sum + Number(row.amount_gnf || 0), 0));
  const remaining = Number(invoice.remaining_balance_gnf ?? Math.max(0, total - paid));

  return (
    <article className="reception-invoice-receipt-print" aria-hidden="true">
      <PrintClinicHeader documentTitle="Reçu de paiement" compact />
      <div className="reception-invoice-receipt-print__meta">
        <p><strong>Facture :</strong> {invoice.invoice_number || 'En attente de synchronisation'}</p>
        <p><strong>Dossier :</strong> {patient?.patient_number || invoice.patient_number || patient?.id || '—'}</p>
        <p><strong>Patient :</strong> {patientFullName(patient) || invoice.patient_name || '—'}</p>
        <p><strong>Date :</strong> {invoice.issued_at || invoice.created_at ? new Date(invoice.issued_at || invoice.created_at).toLocaleString('fr-FR') : 'En attente de synchronisation'}</p>
      </div>
      <table>
        <thead><tr><th>Prestation</th><th>Qté</th><th>Prix U</th><th>Total</th></tr></thead>
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
      <div className="reception-invoice-receipt-print__totals">
        <p><strong>Sous-total :</strong> {formatGNF(subtotal)}</p>
        <p><strong>Exemption :</strong> {formatGNF(exemption)}</p>
        <p><strong>Total :</strong> {formatGNF(total)}</p>
        <p><strong>Montant reçu :</strong> {formatGNF(paid)}</p>
        <p><strong>Reste à payer :</strong> {formatGNF(remaining)}</p>
      </div>
      {payments.length > 0 && (
        <section>
          <h2>Paiements</h2>
          <ul>
            {payments.map((payment, index) => (
              <li key={payment.id || index}>
                {methodLabel(PAYMENT_METHODS, payment.payment_method)} · {formatGNF(payment.amount_gnf || 0)}
                {payment.reference ? ` · ${payment.reference}` : ''}
              </li>
            ))}
          </ul>
        </section>
      )}
      <footer>
        Imprimé par {user?.full_name || user?.email || '—'}
        {invoice._offline_queued ? ' · Document local en attente de synchronisation' : ''}
      </footer>
    </article>
  );
}
