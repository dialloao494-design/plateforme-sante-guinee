import {
  CLINIC_ADDRESS,
  CLINIC_COUNTRY,
  CLINIC_EMAIL,
  CLINIC_LOGO_URL,
  CLINIC_MINISTRY,
  CLINIC_MOTTO,
  CLINIC_PHONE,
  CLINIC_PRINT_NAME,
} from '../../constants/clinicBranding.js';
import './print-documents.css';

/** Official clinic header for all printable documents. */
export default function PrintClinicHeader({ documentTitle = null, compact = false }) {
  return (
    <header className={`print-clinic-header${compact ? ' print-clinic-header--compact' : ''}`}>
      <img src={CLINIC_LOGO_URL} alt="" className="print-clinic-header__logo" width={compact ? 72 : 120} height={compact ? 72 : 120} />
      <p className="print-clinic-header__country">{CLINIC_COUNTRY}</p>
      <p className="print-clinic-header__motto">{CLINIC_MOTTO}</p>
      <p className="print-clinic-header__ministry">{CLINIC_MINISTRY}</p>
      <p className="print-clinic-header__name">{CLINIC_PRINT_NAME}</p>
      <p className="print-clinic-header__contact">{CLINIC_ADDRESS}</p>
      <p className="print-clinic-header__contact">
        Tél. {CLINIC_PHONE} · {CLINIC_EMAIL}
      </p>
      <div className="print-clinic-header__separator" aria-hidden="true" />
      {documentTitle ? <h1 className="print-clinic-header__doc-title">{documentTitle}</h1> : null}
    </header>
  );
}
