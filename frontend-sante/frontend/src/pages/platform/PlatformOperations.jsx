import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import platformApi from '../../services/platformApi.js';
import { formatApiError } from '../../utils/apiError.js';
import PageSkeleton from '../../components/ui/PageSkeleton.jsx';
import '../clinical/clinical.css';
import './PlatformOwner.css';

const dateTimeFormatter = new Intl.DateTimeFormat('fr-GN', { dateStyle: 'medium', timeStyle: 'short' });
const formatDateTime = (value) => value ? dateTimeFormatter.format(new Date(value)) : 'Jamais signalé';

export default function PlatformOperations() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    platformApi.listClinicDirectory({ category: 'production' }).then(async ({ data }) => {
      const clinics = Array.isArray(data) ? data : [];
      const results = await Promise.all(clinics.map(async (clinic) => {
        try { return { clinic, health: (await platformApi.clinicHealth(clinic.id)).data, available: true }; }
        catch { return { clinic, health: null, available: false }; }
      }));
      if (active) setRows(results);
    }).catch((err) => active && setError(formatApiError(err, 'Impossible de charger l’état des opérations.')))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);
  const totals = useMemo(() => rows.reduce((result, row) => ({
    pending: result.pending + (row.health?.sync?.pending || 0),
    conflicts: result.conflicts + (row.health?.sync?.conflicts || 0),
    unavailable: result.unavailable + (row.available ? 0 : 1),
    backups: result.backups + (row.health?.backup?.verified ? 0 : 1),
  }), { pending: 0, conflicts: 0, unavailable: 0, backups: 0 }), [rows]);

  return <main className="platform-owner-page">
    <header className="platform-admin-heading"><div><p className="clinical-eyebrow">Continuité de service</p><h1>Opérations</h1><p>Surveillez la synchronisation hors ligne, les sauvegardes et les postes des cliniques.</p></div><Link className="platform-owner-link" to="/platform/overview">Retour à la vue d’ensemble</Link></header>
    {error && <p className="clinical-error" role="alert">{error}</p>}
    {loading ? <PageSkeleton lines={8} /> : <>
      <dl className="platform-summary-strip platform-summary-strip--compact"><div><dt>Éléments en attente</dt><dd>{totals.pending}</dd></div><div><dt>Conflits ouverts</dt><dd>{totals.conflicts}</dd></div><div><dt>États indisponibles</dt><dd>{totals.unavailable}</dd></div><div><dt>Sauvegardes à vérifier</dt><dd>{totals.backups}</dd></div></dl>
      <section className="platform-operations-list" aria-labelledby="operations-title">
        <div className="platform-section-heading"><div><p className="clinical-eyebrow">État par établissement</p><h2 id="operations-title">Cliniques en production</h2></div></div>
        {rows.length === 0 ? <div className="platform-empty-state"><h2>Aucune clinique en production</h2><p>Créez ou activez une clinique pour commencer la surveillance.</p></div> : rows.map(({ clinic, health, available }) => <article key={clinic.id} className="platform-operation-row">
          <div className="platform-operation-identity"><span className={`platform-watch-dot${available && health?.status === 'ok' ? ' platform-watch-dot--ok' : ''}`} aria-hidden="true" /><div><h3>{clinic.name}</h3><p>{available ? (health.status === 'ok' ? 'Fonctionnement normal' : 'Attention requise') : 'État indisponible'}</p></div></div>
          <dl><div><dt>Synchronisation</dt><dd>{health ? `${health.sync.pending} attente · ${health.sync.conflicts} conflit` : 'Indisponible'}</dd></div><div><dt>Dernier poste vu</dt><dd>{formatDateTime(health?.workstation?.last_seen_at)}</dd></div><div><dt>Sauvegarde</dt><dd>{health?.backup?.verified ? `Vérifiée · ${formatDateTime(health.backup.last_at)}` : 'À vérifier'}</dd></div><div><dt>Base de données</dt><dd>{health?.database === 'connected' ? 'Connectée' : 'À vérifier'}</dd></div></dl>
          <Link to={`/platform/clinics/${clinic.id}?tab=overview`}>Voir la clinique</Link>
        </article>)}
      </section>
    </>}
  </main>;
}
