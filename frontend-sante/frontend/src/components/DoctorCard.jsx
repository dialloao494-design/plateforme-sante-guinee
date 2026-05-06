import './DoctorCard.css';

const DoctorCard = ({ doctor, onBook }) => {
  const fullName = `${doctor.first_name} ${doctor.last_name}`;
  const initials = `${doctor.first_name?.[0] || 'D'}${doctor.last_name?.[0] || 'D'}`.toUpperCase();

  return (
    <div className="doctor-card">
      <div className="doctor-card-header">
        {doctor.photo_url ? (
          <img src={doctor.photo_url} alt={fullName} className="doctor-photo" />
        ) : (
          <div className="doctor-avatar">{initials}</div>
        )}
      </div>

      <div className="doctor-card-content">
        <h3 className="doctor-name">{fullName}</h3>
        
        <div className="doctor-info">
          <p className="doctor-specialty">
            <span className="label">Spécialité:</span>
            <span className="value">{doctor.specialty}</span>
          </p>
          
          <p className="doctor-location">
            <span className="label">Lieu:</span>
            <span className="value">{doctor.location}</span>
          </p>

          {doctor.consultation_fee > 0 && (
            <p className="doctor-fee">
              <span className="label">Consultation:</span>
              <span className="value">{doctor.consultation_fee} GNF</span>
            </p>
          )}
        </div>
      </div>

      <div className="doctor-card-footer">
        <button 
          className="button-primary" 
          onClick={() => onBook(doctor.id)}
        >
          Prendre rendez-vous
        </button>
      </div>
    </div>
  );
};

export default DoctorCard;
