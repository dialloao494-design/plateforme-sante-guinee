import './PatientCard.css';

const PatientCard = ({ patient, onDelete, onEdit }) => {
  return (
    <div className="patient-card">
      <div className="patient-avatar">
        <span>{patient.name?.charAt(0) || '?'}</span>
      </div>
      <div className="patient-info">
        <h3 className="patient-name">{patient.name}</h3>
        <p className="patient-age">Âge: {patient.age} ans</p>
        <p className="patient-condition">Genre: {patient.gender || patient.condition}</p>
      </div>
      {(onEdit || onDelete) && (
        <div className="patient-actions">
          {onEdit && (
            <button className="btn btn-primary" onClick={() => onEdit(patient)}>
              Modifier
            </button>
          )}
          {onDelete && (
            <button className="btn btn-secondary" onClick={onDelete}>
              Supprimer
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default PatientCard;