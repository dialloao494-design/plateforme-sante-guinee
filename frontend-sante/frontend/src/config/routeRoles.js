/** Central route capabilities. The API remains the authorization authority. */
export const STAFF_ADMIN_ROLES = ['admin', 'clinic_admin', 'platform_admin'];
export const PLATFORM_OWNER_ROLES = ['platform_owner'];
export const PLATFORM_CLINIC_PROVISION_ROLES = ['platform_owner', 'platform_admin'];
export const CLINIC_ADMIN_ROLES = ['admin', 'clinic_admin'];
export const RECEPTION_ROLES = ['receptionist', 'cashier'];
export const BILLING_ROLES = ['receptionist', 'cashier', 'admin', 'clinic_admin'];
export const NUTRITION_ROLES = [
  'nutritionist', 'midwife', 'doctor', 'admin', 'clinic_admin',
  'platform_admin', 'pev_agent', 'nurse',
];
export const PEV_ROLES = [
  'pev_agent', 'midwife', 'receptionist', 'doctor', 'admin',
  'clinic_admin', 'platform_admin',
];
export const NURSE_DASHBOARD_ROLES = [
  'nurse', 'midwife', 'admin', 'clinic_admin', 'receptionist', 'doctor',
];
export const NURSING_ROLES = NURSE_DASHBOARD_ROLES;
export const IMMUNIZATION_ROLES = [...PEV_ROLES, 'nutritionist'];
export const HOSPITALIZATION_ROLES = [
  'admin', 'clinic_admin', 'platform_admin', 'receptionist', 'doctor', 'nurse',
];
export const PATIENT_HISTORY_ROLES = [
  'receptionist', 'cashier', 'doctor', 'lab_technician', 'pharmacist',
  'nutritionist', 'pev_agent', 'nurse', 'midwife', 'clinic_admin',
  'admin', 'platform_admin',
];
