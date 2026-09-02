import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import platformApi from '../../services/platformApi.js';
import { formatApiError } from '../../utils/apiError.js';
import PageSkeleton from '../../components/ui/PageSkeleton.jsx';
import '../clinical/clinical.css';
import './PlatformOwner.css';

const dateFormatter = new Intl.DateTimeFormat('fr-GN', { dateStyle: 'medium' });
function formatDate(value) { if (!value) return 'Aucune activité enregistrée'; const date = new Date(value); return Number.isNaN(date.getTime()) ? 'Date indisponible' : dateFormatter.format(date); }
function isStale(value) { return !value || Date.now() - new Date(value).getTime() > 7 * 86400000; }

export default function PlatformOwnerDashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null); const [clinics, setClinics] = useState([]);
  const [loading, setLoading] = useState(true); const [error, setError] = useState('');
  useEffect(() => { let active = true; Promise.all([platformApi.getSummary('production'), platformApi.listClinicDirectory({ category: 'production' })]).then(([sumRes, dirRes]) => { if (active) { setSummary(sumRes.data); setClinics(Array.isArray(dirRes.data) ? dirRes.data : []); } }).catch((requestError) => active && setError(formatApiError(requestError, 'Le pilotage plateforme est momentanément indisponible. Actualisez la page.'))).finally(() => active && setLoading(false)); return () => { active = false; }; }, []);
  const attentionItems = useMemo(() => { const items = []; clinics.forEach((clinic) => { if (!clinic.is_active) items.push({ clinic, label: 'Accès clinique suspendu', level: 'critical', tab: 'overview' }); if (!clinic.admin_email) items.push({ clinic, label: 'Aucun administrateur actif identifié', level: 'critical', tab: 'staff' }); if (clinic.is_active && isStale(clinic.last_activity_at)) items.push({ clinic, label: 'Aucune activité récente', level: 'warning', tab: 'overview' }); }); return items; }, [clinics]);
  const healthyCount = Math.max(0, clinics.length - new Set(attentionItems.map((item) => item.clinic.id)).size);
  return <main className="platform-owner-page platform-command-center">
    <header className="platform-command-hero"><div><p className="clinical-eyebrow">Pilotage du réseau de soins</p><h1>Vue d’ensemble</h1><p>Bonjour {user?.full_name || user?.email}. Commencez par les situations qui nécessitent une décision.</p></div><div className="platform-network-pulse" aria-label={`${healthyCount} cliniques sans alerte visible sur ${clinics.length}`}><span aria-hidden="true" /><strong>{healthyCount} / {clinics.length}</strong><small>cliniques sans alerte visible</small></div></header>
    {error && <p className="clinical-error" role="alert">{error}</p>}
    {loading ? <PageSkeleton lines={7} /> : <>
      <section className="platform-priority-panel" aria-labelledby="priority-title"><div className="platform-priority-heading"><div><p className="clinical-eyebrow">À traiter maintenant</p><h2 id="priority-title">Priorités opérationnelles</h2></div><strong className={attentionItems.length ? 'platform-priority-count platform-priority-count--alert' : 'platform-priority-count'}>{attentionItems.length}</strong></div>
        {attentionItems.length === 0 ? <div className="platform-clear-state"><span aria-hidden="true">✓</span><div><strong>Aucune priorité détectée</strong><p>Les cliniques de production ont un administrateur et une activité récente.</p></div></div> : <ol className="platform-priority-list">{attentionItems.slice(0, 8).map((item) => <li key={`${item.clinic.id}-${item.label}`}><span className={`platform-priority-marker platform-priority-marker--${item.level}`} aria-hidden="true" /><div><strong>{item.label}</strong><span>{item.clinic.name} · Clinique #{item.clinic.id}</span></div><Link to={`/platform/clinics/${item.clinic.id}?tab=${item.tab}`}>Examiner</Link></li>)}</ol>}
      </section>
      <section className="platform-network-summary" aria-labelledby="network-title"><div className="platform-section-heading"><div><p className="clinical-eyebrow">Aujourd’hui</p><h2 id="network-title">Réseau en production</h2></div><Link to="/platform/clinics">Voir toutes les cliniques</Link></div><dl className="platform-summary-strip"><div><dt>Cliniques actives</dt><dd>{summary?.active_clinics ?? 0}</dd></div><div><dt>Personnel</dt><dd>{summary?.total_staff ?? 0}</dd></div><div><dt>Patients</dt><dd>{summary?.total_patients ?? 0}</dd></div><div><dt>Consultations ce mois</dt><dd>{summary?.monthly_consultations ?? 0}</dd></div></dl></section>
      <section className="platform-clinic-watch" aria-labelledby="watch-title"><div className="platform-section-heading"><div><p className="clinical-eyebrow">Surveillance</p><h2 id="watch-title">Dernière activité par clinique</h2></div><Link to="/platform/system">Ouvrir les opérations</Link></div><div className="platform-watch-list">{clinics.slice(0, 6).map((clinic) => <Link key={clinic.id} to={`/platform/clinics/${clinic.id}`} className="platform-watch-row"><span className={`platform-watch-dot${clinic.is_active && !isStale(clinic.last_activity_at) ? ' platform-watch-dot--ok' : ''}`} aria-hidden="true" /><div><strong>{clinic.name}</strong><span>{clinic.city || 'Ville non renseignée'} · {clinic.staff_count} membre(s)</span></div><time dateTime={clinic.last_activity_at || undefined}>{formatDate(clinic.last_activity_at)}</time></Link>)}</div></section>
      <nav className="platform-owner-shortcuts" aria-label="Actions de pilotage"><Link to="/platform/clinics"><strong>Cliniques</strong><span>Personnel, configuration et données</span></Link><Link to="/platform/accounts"><strong>Comptes & accès</strong><span>Identités à examiner et sessions</span></Link><Link to="/platform/settings"><strong>Sécurité</strong><span>MFA, verrouillages et accès actifs</span></Link></nav>
    </>}
  </main>;
}
