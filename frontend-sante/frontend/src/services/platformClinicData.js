/**
 * Clinic-first platform data — uses /platform APIs when available, else /clinical fallbacks.
 */
import clinicalApi from './clinicalApi';
import platformApi from './platformApi';
import { filterProductionClinics, isTestStaffEmail } from '../utils/clinicProductionFilter.js';

const ROLE_LABELS = {
  receptionist: 'Réception',
  cashier: 'Caisse',
  doctor: 'Médecins',
  lab_technician: 'Laboratoire',
  pharmacist: 'Pharmacie',
  nutritionist: 'Nutrition',
  pev_agent: 'PEV',
  nurse: 'Soins infirmiers',
  clinic_admin: 'Admin clinique',
  admin: 'Admin',
};

export const CLINIC_MODULES = [
  { id: 'reception', label: 'Réception', roles: ['receptionist', 'cashier'], createRole: 'receptionist' },
  { id: 'doctor', label: 'Médecins', roles: ['doctor'], createRole: 'doctor' },
  { id: 'lab', label: 'Laboratoire', roles: ['lab_technician'], createRole: 'lab_technician' },
  { id: 'pharmacy', label: 'Pharmacie', roles: ['pharmacist'], createRole: 'pharmacist' },
  { id: 'admin', label: 'Administration', roles: ['clinic_admin', 'admin'], createRole: 'clinic_admin' },
];

function buildRoleBreakdown(staff) {
  const counts = {};
  for (const member of staff) {
    counts[member.role] = (counts[member.role] || 0) + 1;
  }
  return Object.entries(counts)
    .map(([role, count]) => ({
      role,
      label: ROLE_LABELS[role] || role,
      count,
    }))
    .sort((a, b) => b.count - a.count || a.role.localeCompare(b.role));
}

function buildDetailFromClinical(clinic, staff) {
  const productionStaff = staff.filter((m) => !isTestStaffEmail(m.email));
  const admin = productionStaff.find((m) => m.role === 'clinic_admin' || m.role === 'admin');
  return {
    id: clinic.id,
    name: clinic.name,
    address: clinic.address,
    city: clinic.city,
    phone: clinic.phone,
    email: clinic.email,
    is_active: clinic.is_active,
    status: clinic.is_active ? 'Active' : 'Archivée',
    category: 'production',
    created_at: clinic.created_at || null,
    admin_email: admin?.email || null,
    admin_name: null,
    staff_count: productionStaff.length,
    patient_count: null,
    consultation_count: null,
    monthly_consultations: null,
    last_activity_at: null,
    role_breakdown: buildRoleBreakdown(productionStaff),
    module_usage: null,
  };
}

function enrichSummaryFromStaff(clinic, staff) {
  const productionStaff = staff.filter((m) => !isTestStaffEmail(m.email));
  const admin = productionStaff.find((m) => m.role === 'clinic_admin' || m.role === 'admin');
  return {
    id: clinic.id,
    name: clinic.name,
    city: clinic.city,
    is_active: clinic.is_active,
    status: clinic.is_active ? 'Active' : 'Archivée',
    category: 'production',
    created_at: clinic.created_at || null,
    staff_count: productionStaff.length,
    patient_count: clinic.patient_count ?? null,
    consultation_count: clinic.consultation_count ?? 0,
    last_activity_at: clinic.last_activity_at ?? null,
    admin_email: clinic.admin_email || admin?.email || null,
  };
}

async function listStaffForClinic(clinicId) {
  try {
    const { data } = await platformApi.listClinicStaff(clinicId);
    return Array.isArray(data) ? data.filter((m) => !isTestStaffEmail(m.email)) : [];
  } catch {
    const { data } = await clinicalApi.listStaff(clinicId);
    return (Array.isArray(data) ? data : []).filter((m) => !isTestStaffEmail(m.email));
  }
}

export async function loadClinicDirectory({ category = 'production', search = '' } = {}) {
  try {
    const { data } = await platformApi.listClinicDirectory({
      category,
      search: search.trim() || undefined,
    });
    let rows = Array.isArray(data) ? data : [];
    if (category === 'production') {
      rows = filterProductionClinics(rows);
    }
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (c) =>
        String(c.name || '').toLowerCase().includes(q)
        || String(c.id) === q
        || String(c.city || '').toLowerCase().includes(q)
        || String(c.admin_email || '').toLowerCase().includes(q)
    );
  } catch {
    const { data } = await clinicalApi.listClinics({ forceRefresh: true });
    let rows = filterProductionClinics(data || []);
    if (category === 'archived') rows = (data || []).filter((c) => !c.is_active);
    else if (category !== 'production' && category !== 'all') rows = [];

    const enriched = await Promise.all(
      rows.map(async (clinic) => {
        try {
          const staff = await listStaffForClinic(clinic.id);
          return enrichSummaryFromStaff(clinic, staff);
        } catch {
          return enrichSummaryFromStaff(clinic, []);
        }
      })
    );

    const q = search.trim().toLowerCase();
    if (!q) return enriched;
    return enriched.filter(
      (c) =>
        String(c.name || '').toLowerCase().includes(q)
        || String(c.id) === q
        || String(c.city || '').toLowerCase().includes(q)
        || String(c.admin_email || '').toLowerCase().includes(q)
    );
  }
}

export async function loadClinicDetail(clinicId) {
  const id = Number(clinicId);
  try {
    const { data } = await platformApi.getClinicDetail(id);
    return data;
  } catch {
    const { data: clinics } = await clinicalApi.listClinics({ forceRefresh: true });
    const clinic = (clinics || []).find((c) => c.id === id);
    if (!clinic) throw new Error('Clinique introuvable');
    const staff = await listStaffForClinic(id);
    return buildDetailFromClinical(clinic, staff);
  }
}

export async function loadClinicStaff(clinicId) {
  return listStaffForClinic(Number(clinicId));
}

export function getModuleById(sectionId) {
  return CLINIC_MODULES.find((m) => m.id === sectionId) || null;
}

export function filterStaffByModule(staff, module) {
  if (!module) return staff;
  return staff.filter((m) => module.roles.includes(m.role));
}

export async function createClinicStaff({ clinicId, email, password, role }) {
  const { data } = await clinicalApi.createStaff({
    email,
    password,
    role,
    clinic_id: Number(clinicId),
  });
  return data;
}

export async function deactivateClinicStaff({ clinicId, userId, reason }) {
  return platformApi.deactivateStaff(Number(clinicId), userId, reason);
}

export async function reactivateClinicStaff({ clinicId, userId, reason }) {
  return platformApi.reactivateStaff(Number(clinicId), userId, reason);
}

export async function resetClinicStaffPassword({ clinicId, userId, newPassword }) {
  try {
    return await platformApi.resetStaffPassword(Number(clinicId), userId, newPassword);
  } catch {
    return clinicalApi.resetStaffPassword(userId, {
      clinic_id: Number(clinicId),
      new_password: newPassword,
    });
  }
}

export { ROLE_LABELS };
