import PatientCard from './PatientCard';
import './PatientList.css';

const PatientList = ({ patients, onDelete, onEdit }) => {
  return (
    <div className="patient-list">
      <h2>Mes Patients</h2>
      <div className="patients-grid">
        {patients.map((patient) => (
          <PatientCard
            key={patient.id}
            patient={patient}
            onDelete={onDelete ? () => onDelete(patient.id) : undefined}
            onEdit={onEdit}
          />
        ))}
      </div>
      {patients.length === 0 && (
        <div className="no-patients">
          <p>Aucun patient enregistré pour le moment.</p>
        </div>
      )}
    </div>
  );
};

export default PatientList;
