const PAYMENTS_STORAGE_KEY = 'payments';

const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

export const loadSimulatedPayments = () => {
  try {
    const raw = localStorage.getItem(PAYMENTS_STORAGE_KEY);
    if (!raw) {
      return {};
    }

    const parsed = JSON.parse(raw);
    if (!isObject(parsed)) {
      return {};
    }

    const normalized = {};
    Object.entries(parsed).forEach(([appointmentId, isPaid]) => {
      if (isPaid === true) {
        normalized[String(appointmentId)] = true;
      }
    });

    return normalized;
  } catch {
    return {};
  }
};

export const saveSimulatedPayments = (paymentsMap) => {
  try {
    if (!isObject(paymentsMap)) {
      localStorage.removeItem(PAYMENTS_STORAGE_KEY);
      return;
    }

    localStorage.setItem(PAYMENTS_STORAGE_KEY, JSON.stringify(paymentsMap));
  } catch {
    // Ignore localStorage quota or serialization errors.
  }
};

export { PAYMENTS_STORAGE_KEY };
