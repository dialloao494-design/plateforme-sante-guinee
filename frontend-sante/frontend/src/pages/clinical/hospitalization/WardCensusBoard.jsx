const STATE = {
  available: ['Disponible', 'success'], reserved: ['Réservé', 'info'], occupied: ['Occupé', 'occupied'],
  cleaning: ['À nettoyer', 'warning'], maintenance: ['Maintenance', 'danger'], unavailable: ['Indisponible', 'muted'],
};

function BedCell({ bed, canManageBeds, onSelectAdmission, onMarkReady }) {
  const [label, tone] = STATE[bed.status] || [bed.status, 'muted'];
  return (
    <article className={`ward-bed ward-bed--${tone}`} data-bed-status={bed.status}>
      <div className="ward-bed__topline">
        <strong>{bed.accommodation_type === 'cradle' ? 'Berceau' : 'Lit'} {bed.bed_number}</strong>
        <span>{label}</span>
      </div>
      <small className="ward-bed__code">{bed.stable_code}</small>
      {bed.patient ? (
        <button type="button" className="ward-bed__patient" onClick={() => onSelectAdmission?.(bed.patient.admission_id)}>
          <strong>{bed.patient.name}</strong>
          <span>{bed.patient.admission_number}</span>
          <span>{bed.patient.expected_discharge_at ? `Sortie prévue ${new Date(bed.patient.expected_discharge_at).toLocaleDateString('fr-FR')}` : 'Sortie non planifiée'}</span>
        </button>
      ) : (
        <p className="ward-bed__empty">
          {bed.status === 'reserved' ? 'En attente du patient' : bed.status === 'cleaning' ? 'Turnover requis' : 'Aucun patient'}
        </p>
      )}
      <div className="ward-bed__traits" aria-label="Caractéristiques du lit">
        {bed.newborn_suitable && <span>Nouveau-né</span>}
        {!bed.newborn_suitable && bed.pediatric_suitable && <span>Pédiatrie</span>}
        {bed.isolation_suitable && <span>Isolement</span>}
        {bed.accessible && <span>Accessible</span>}
      </div>
      {canManageBeds && bed.status === 'cleaning' && (
        <button type="button" className="ward-bed__ready" onClick={() => onMarkReady(bed)}>Marquer propre et disponible</button>
      )}
    </article>
  );
}

export default function WardCensusBoard({ board, canManageBeds, onSelectAdmission, onMarkReady }) {
  const wards = board?.wards || [];
  return (
    <section className="ward-board" aria-labelledby="ward-board-title">
      <div className="ward-board__heading">
        <div><p className="ward-board__eyebrow">CENSUS EN TEMPS RÉEL</p><h2 id="ward-board-title">Occupation par service</h2></div>
        <div className="ward-board__legend" aria-label="Légende">
          {Object.entries(STATE).map(([key, [label]]) => <span key={key} data-state={key}>{label}</span>)}
        </div>
      </div>
      {wards.length === 0 && <div className="ward-board__empty"><strong>Aucun service configuré</strong><span>Commencez par créer un service, puis ses chambres et lits.</span></div>}
      {wards.map((ward) => (
        <section key={ward.id} className="ward-row">
          <header className="ward-row__header"><div><span>{ward.code}</span><h3>{ward.name}</h3></div><small>{ward.location || ward.service_type}</small></header>
          <div className="ward-row__rooms">
            {ward.rooms.map((room) => (
              <section key={room.id} className="ward-room">
                <header><strong>Chambre {room.room_number}</strong><span>{room.beds.filter((bed) => bed.status === 'occupied').length}/{room.beds.length} occupés</span></header>
                <div className="ward-room__beds">
                  {room.beds.map((bed) => <BedCell key={bed.id} bed={bed} canManageBeds={canManageBeds} onSelectAdmission={onSelectAdmission} onMarkReady={onMarkReady} />)}
                </div>
              </section>
            ))}
          </div>
        </section>
      ))}
    </section>
  );
}
