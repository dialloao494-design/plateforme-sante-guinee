/**
 * Planned payment rails — UI copy and flags only (no provider keys in frontend).
 * Wire Orange Money / MTN when backend endpoints are ready.
 */

export const PAYMENT_CHANNELS = [
  {
    id: 'orange_money_gn',
    label: 'Orange Money Guinée',
    status: 'planned',
    description: 'Paiement mobile direct depuis le numéro Orange du patient.',
  },
  {
    id: 'mtn_momo',
    label: 'MTN Mobile Money',
    status: 'planned',
    description: 'Flux Momo pour consultations et téléconsultations.',
  },
  {
    id: 'stripe_card',
    label: 'Carte bancaire (Stripe)',
    status: 'beta',
    description: 'Déjà utilisé pour certains parcours — extension possible.',
  },
];

export function getPaymentReadinessSummary() {
  return {
    headline: 'Paiements cabinet & patient',
    sub:
      'Les statuts de paiement sont suivis sur chaque rendez-vous. L’intégration Orange Money / MTN sera branchée sur les mêmes statuts sans changer votre workflow.',
  };
}
