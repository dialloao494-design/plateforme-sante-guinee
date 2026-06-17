import DepartmentQueuePanel from './DepartmentQueuePanel.jsx';
import './clinical.css';

export default function MidwifeDashboard() {
  return (
    <div className="clinical-page">
      <h1>Tableau de bord — Sage-femme</h1>
      <p className="clinical-lead">Consultations sage-femme et suivi des parcours adultes.</p>
      <DepartmentQueuePanel department="midwife" title="File de visite — Sage-femme" />
    </div>
  );
}
