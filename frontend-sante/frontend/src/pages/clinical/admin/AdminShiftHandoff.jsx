import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../../services/clinicalApi.js';
import { countPendingOutbox, isBrowserOnline } from '../../../offline/index.js';
import { formatApiError } from '../../../utils/apiError.js';

const blank = { printer_ready: false, offline_ready: false, notes: '', acknowledge_unresolved: false };

export default function AdminShiftHandoff({ onFeedback }) {
  const [shift, setShift] = useState(null);
  const [history, setHistory] = useState([]);
  const [form, setForm] = useState(blank);
  const [pending, setPending] = useState(0);
  const [busy, setBusy] = useState(false);
  const online = isBrowserOnline();

  const load = useCallback(async () => {
    const pendingCount = await countPendingOutbox().catch(() => 0);
    setPending(pendingCount);
    if (!isBrowserOnline()) return;
    const [current, recent] = await Promise.all([clinicalApi.currentClinicShift(), clinicalApi.clinicShiftHistory()]);
    setShift(current.data?.shift || null);
    setHistory(recent.data || []);
  }, []);
  useEffect(() => { load().catch(() => {}); }, [load]);

  const submit = async (event) => {
    event.preventDefault();
    if (!online) { onFeedback('error', 'Reconnectez ce poste pour ouvrir ou clôturer une relève avec un état serveur fiable.'); return; }
    setBusy(true);
    try {
      if (shift) {
        await clinicalApi.closeClinicShift(shift.id, {
          printer_ready: form.printer_ready,
          offline_pending_count: pending,
          acknowledge_unresolved: form.acknowledge_unresolved,
          notes: form.notes || null,
        });
        onFeedback('message', 'Poste clôturé. Les éléments non résolus sont conservés dans la relève.');
      } else {
        await clinicalApi.openClinicShift({
          printer_ready: form.printer_ready,
          offline_ready: form.offline_ready,
          offline_pending_count: pending,
          notes: form.notes || null,
        });
        onFeedback('message', 'Poste ouvert. Les contrôles de départ ont été horodatés.');
      }
      setForm(blank);
      await load();
    } catch (err) { onFeedback('error', formatApiError(err, 'La relève n’a pas pu être enregistrée.')); }
    finally { setBusy(false); }
  };

  const unresolved = shift?.opening_snapshot?.unresolved || [];
  return <section className="admin-shift" aria-labelledby="admin-shift-title">
    <div className="admin-shift__header">
      <div><p className="clinical-eyebrow">Continuité des soins</p><h2 id="admin-shift-title">Ouverture et relève du poste</h2></div>
      <span className={`admin-shift__state ${shift ? 'is-open' : ''}`}>{shift ? 'Poste ouvert' : 'Poste fermé'}</span>
    </div>
    <p className="clinical-muted">Ce registre horodaté transmet les activités en cours. Il ne remplace pas la future clôture comptable de caisse.</p>
    {shift ? <div className="admin-shift__open-summary"><strong>Ouvert le {new Date(shift.opened_at).toLocaleString('fr-FR')}</strong><span>{unresolved.length ? `${unresolved.length} point(s) signalé(s) à l’ouverture` : 'Aucune exception à l’ouverture'}</span></div> : null}
    <form onSubmit={submit}>
      <div className="admin-shift__checks">
        <label><input type="checkbox" checked={form.printer_ready} onChange={(e) => setForm({ ...form, printer_ready: e.target.checked })} /> <span><strong>Impression vérifiée</strong><small>Une page de test ou un reçu est lisible.</small></span></label>
        {!shift ? <label><input type="checkbox" checked={form.offline_ready} onChange={(e) => setForm({ ...form, offline_ready: e.target.checked })} /> <span><strong>Mode hors ligne vérifié</strong><small>{pending ? `${pending} opération(s) attendent une synchronisation.` : 'La file hors ligne est vide.'}</small></span></label> : <div className={`admin-shift__queue ${pending ? 'has-warning' : ''}`}><strong>File hors ligne</strong><span>{pending ? `${pending} en attente` : 'Synchronisée'}</span></div>}
      </div>
      {shift ? <label className="admin-shift__ack"><input type="checkbox" checked={form.acknowledge_unresolved} onChange={(e) => setForm({ ...form, acknowledge_unresolved: e.target.checked })} /> Je confirme avoir transmis les activités et exceptions non résolues à l’équipe suivante.</label> : null}
      <label className="admin-shift__notes">Note de {shift ? 'relève' : 'prise de poste'}<textarea rows="3" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder={shift ? 'Responsable suivant, incidents, actions à poursuivre…' : 'Obligatoire si un contrôle reste incomplet…'} /></label>
      <button className="clinical-btn" disabled={busy || !online}>{busy ? 'Enregistrement…' : shift ? 'Clôturer et transmettre' : 'Ouvrir le poste'}</button>
    </form>
    {history.length ? <details className="admin-shift__history"><summary>Historique récent ({history.length})</summary><ol>{history.map((item) => <li key={item.id}><strong>{item.status === 'open' ? 'Ouvert' : 'Clôturé'}</strong><span>{new Date(item.opened_at).toLocaleString('fr-FR')}{item.closed_at ? ` → ${new Date(item.closed_at).toLocaleString('fr-FR')}` : ''}</span></li>)}</ol></details> : null}
  </section>;
}
