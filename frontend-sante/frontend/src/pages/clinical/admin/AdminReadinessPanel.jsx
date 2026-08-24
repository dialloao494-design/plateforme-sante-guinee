import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { MODULE_OPTIONS, PAYMENT_OPTIONS } from './adminDomain.js';

export default function AdminReadinessPanel({ onboarding, busy, onSave }) {
  const [open, setOpen] = useState(false);
  const [activeStep, setActiveStep] = useState('identity');
  const [draft, setDraft] = useState(null);

  useEffect(() => {
    if (!onboarding) return;
    setActiveStep(onboarding.current_step || 'identity');
    setDraft({ ...onboarding.identity, ...onboarding.configuration });
    if (!onboarding.is_operational) setOpen(true);
  }, [onboarding]);

  const active = useMemo(
    () => onboarding?.checklist?.find((item) => item.target === activeStep),
    [activeStep, onboarding],
  );
  if (!onboarding || !draft) return null;

  const toggleList = (field, value) => {
    const values = new Set(draft[field] || []);
    if (values.has(value)) values.delete(value); else values.add(value);
    setDraft({ ...draft, [field]: [...values] });
  };
  const save = (payload, nextStep) => onSave({ ...payload, current_step: nextStep || activeStep });

  return (
    <section className={`admin-readiness ${onboarding.is_operational ? 'is-ready' : ''}`} aria-labelledby="readiness-title">
      <div className="admin-readiness__summary">
        <div>
          <p className="clinical-eyebrow">État de préparation</p>
          <h2 id="readiness-title">{onboarding.is_operational ? 'Clinique opérationnelle' : 'Configuration à terminer'}</h2>
          <p>{onboarding.completed_count} étapes sur {onboarding.total_count} vérifiées. La préparation est enregistrée et peut être reprise plus tard.</p>
        </div>
        <div className="admin-readiness__score" aria-label={`${onboarding.percent} pour cent terminé`}>
          <strong>{onboarding.percent}%</strong>
          <span>{onboarding.is_operational ? 'prête' : 'préparée'}</span>
        </div>
        <button type="button" className="clinical-btn" onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? 'Masquer la configuration' : onboarding.is_operational ? 'Vérifier la configuration' : 'Continuer la configuration'}
        </button>
      </div>
      <div className="admin-readiness__bar" aria-hidden="true"><span style={{ width: `${onboarding.percent}%` }} /></div>

      {open && (
        <div className="admin-setup">
          <ol className="admin-setup__route" aria-label="Étapes de préparation">
            {onboarding.checklist.map((item, index) => (
              <li key={item.key} className={item.complete ? 'is-complete' : ''}>
                <button type="button" onClick={() => setActiveStep(item.target)} aria-current={activeStep === item.target ? 'step' : undefined}>
                  <span>{item.complete ? '✓' : index + 1}</span>
                  <span><strong>{item.label}</strong><small>{item.detail}</small></span>
                </button>
              </li>
            ))}
          </ol>

          <div className="admin-setup__work" aria-live="polite">
            <p className="clinical-eyebrow">Étape à vérifier</p>
            <h3>{active?.label || 'Configuration'}</h3>
            {activeStep === 'identity' && (
              <form onSubmit={(event) => { event.preventDefault(); save({ name: draft.name, address: draft.address, city: draft.city, phone: draft.phone, email: draft.email }, 'modules'); }}>
                <div className="admin-setup__fields">
                  {[['name', 'Nom de la clinique'], ['address', 'Adresse'], ['city', 'Ville'], ['phone', 'Téléphone'], ['email', 'Email']].map(([name, label]) => (
                    <label key={name}>{label}{name !== 'email' && ' *'}<input type={name === 'email' ? 'email' : 'text'} value={draft[name] || ''} onChange={(event) => setDraft({ ...draft, [name]: event.target.value })} required={name !== 'email'} /></label>
                  ))}
                </div>
                <button className="clinical-btn" disabled={busy}>Enregistrer et continuer</button>
              </form>
            )}
            {activeStep === 'modules' && (
              <form onSubmit={(event) => { event.preventDefault(); save({ enabled_modules: draft.enabled_modules }, 'staff'); }}>
                <fieldset className="admin-choice-grid"><legend>Espaces utilisés par cette clinique</legend>
                  {MODULE_OPTIONS.map(([value, label]) => <label key={value}><input type="checkbox" checked={(draft.enabled_modules || []).includes(value)} onChange={() => toggleList('enabled_modules', value)} /> <span>{label}</span></label>)}
                </fieldset>
                <button className="clinical-btn" disabled={busy}>Enregistrer et continuer</button>
              </form>
            )}
            {activeStep === 'staff' && <div className="admin-setup__instruction"><p>Créez au moins un compte de travail avec le vrai nom du membre du personnel.</p><a className="clinical-btn clinical-btn--secondary" href="#create-user">Gérer le personnel</a></div>}
            {activeStep === 'payments' && (
              <form onSubmit={(event) => { event.preventDefault(); save({ payment_methods: draft.payment_methods, receipt_format: draft.receipt_format }, 'capacity'); }}>
                <fieldset className="admin-choice-grid"><legend>Modes de paiement acceptés</legend>
                  {PAYMENT_OPTIONS.map(([value, label]) => <label key={value}><input type="checkbox" checked={(draft.payment_methods || []).includes(value)} onChange={() => toggleList('payment_methods', value)} /> <span>{label}</span></label>)}
                </fieldset>
                <label className="admin-setup__select">Format du reçu<select value={draft.receipt_format || 'a4'} onChange={(event) => setDraft({ ...draft, receipt_format: event.target.value })}><option value="a4">A4</option><option value="thermal">Imprimante thermique</option></select></label>
                <button className="clinical-btn" disabled={busy}>Enregistrer et continuer</button>
              </form>
            )}
            {activeStep === 'capacity' && <div className="admin-setup__instruction"><p>{active?.detail}</p><Link className="clinical-btn clinical-btn--secondary" to="/clinical/hospitalization">Configurer les chambres et lits</Link></div>}
            {activeStep === 'verification' && (
              <form onSubmit={(event) => { event.preventDefault(); save({ printing_tested: draft.printing_tested, offline_workstation_tested: draft.offline_workstation_tested, test_journey_completed: draft.test_journey_completed }, 'verification'); }}>
                <fieldset className="admin-verification"><legend>Vérifications sur le poste d'accueil</legend>
                  {[
                    ['printing_tested', "J'ai imprimé un reçu de test et vérifié toutes les informations."],
                    ['offline_workstation_tested', "J'ai testé le parcours hors ligne puis sa synchronisation."],
                    ['test_journey_completed', "J'ai terminé un parcours patient test jusqu'au paiement."],
                  ].map(([name, label]) => <label key={name}><input type="checkbox" checked={Boolean(draft[name])} onChange={(event) => setDraft({ ...draft, [name]: event.target.checked })} /><span>{label}</span></label>)}
                </fieldset>
                <button className="clinical-btn" disabled={busy}>{busy ? 'Enregistrement…' : 'Enregistrer les vérifications'}</button>
              </form>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
