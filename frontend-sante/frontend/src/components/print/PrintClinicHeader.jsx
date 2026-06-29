import { CLINIC_LOGO_URL, CLINIC_PRINT_NAME } from '../../constants/clinicBranding.js';
import './print-documents.css';

/** Centered logo + clinic name for print-only receipt/invoice layouts. */
export default function PrintClinicHeader() {
  return (
    <header className="print-clinic-header">
      <img src={CLINIC_LOGO_URL} alt="" className="print-clinic-header__logo" width={140} height={140} />
      <p className="print-clinic-header__name">{CLINIC_PRINT_NAME}</p>
    </header>
  );
}
