import { useState } from 'react';

export default function WardConfiguration({ wards, rooms, onCreateWard, onCreateRoom, onAddBed }) {
  const [ward, setWard] = useState({ code: '', name: '', service_type: 'general', location: '' });
  const [room, setRoom] = useState({ ward_id: '', room_number: '', room_type: 'general', capacity: 1, sex_policy: 'mixed', isolation_capable: false, accessible: false });
  const [bed, setBed] = useState({ room_id: '', bed_number: '', accommodation_type: 'regular_bed', pediatric_suitable: false, newborn_suitable: false, isolation_suitable: false, accessible: false });

  return (
    <section className="ward-config" aria-labelledby="ward-config-title">
      <div className="ward-config__heading"><p>CONFIGURATION DE CAPACITÉ</p><h2 id="ward-config-title">Services, chambres et couchages</h2><span>La configuration physique reste indépendante des tarifs de facturation.</span></div>
      <div className="ward-config__steps">
        <form onSubmit={async (event) => { event.preventDefault(); await onCreateWard(ward); setWard({ ...ward, code: '', name: '' }); }}>
          <span className="ward-config__number">1</span><h3>Créer un service</h3>
          <label>Code<input value={ward.code} onChange={(event) => setWard({ ...ward, code: event.target.value.toUpperCase() })} placeholder="PED" required /></label>
          <label>Nom<input value={ward.name} onChange={(event) => setWard({ ...ward, name: event.target.value })} placeholder="Pédiatrie" required /></label>
          <label>Localisation<input value={ward.location} onChange={(event) => setWard({ ...ward, location: event.target.value })} placeholder="Étage / aile" /></label>
          <button className="clinical-btn" type="submit">Créer le service</button>
        </form>
        <form onSubmit={async (event) => { event.preventDefault(); await onCreateRoom(room); setRoom({ ...room, room_number: '' }); }}>
          <span className="ward-config__number">2</span><h3>Ajouter une chambre</h3>
          <label>Service<select value={room.ward_id} onChange={(event) => setRoom({ ...room, ward_id: event.target.value })} required><option value="">Choisir</option>{wards.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label>Numéro<input value={room.room_number} onChange={(event) => setRoom({ ...room, room_number: event.target.value })} required /></label>
          <label>Capacité<input type="number" min="1" max="20" value={room.capacity} onChange={(event) => setRoom({ ...room, capacity: Number(event.target.value) })} /></label>
          <div className="ward-config__checks"><label><input type="checkbox" checked={room.isolation_capable} onChange={(event) => setRoom({ ...room, isolation_capable: event.target.checked })} /> Isolement</label><label><input type="checkbox" checked={room.accessible} onChange={(event) => setRoom({ ...room, accessible: event.target.checked })} /> Accessible</label></div>
          <button className="clinical-btn" type="submit">Ajouter la chambre</button>
        </form>
        <form onSubmit={async (event) => { event.preventDefault(); await onAddBed(bed); setBed({ ...bed, bed_number: '' }); }}>
          <span className="ward-config__number">3</span><h3>Ajouter un couchage</h3>
          <label>Chambre<select value={bed.room_id} onChange={(event) => setBed({ ...bed, room_id: event.target.value })} required><option value="">Choisir</option>{rooms.map((item) => <option key={item.id} value={item.id}>{item.ward_name} · {item.room_number}</option>)}</select></label>
          <label>Identifiant dans la chambre<input value={bed.bed_number} onChange={(event) => setBed({ ...bed, bed_number: event.target.value })} placeholder="A" required /></label>
          <label>Type<select value={bed.accommodation_type} onChange={(event) => setBed({ ...bed, accommodation_type: event.target.value, newborn_suitable: event.target.value === 'cradle', pediatric_suitable: event.target.value === 'cradle' })}><option value="regular_bed">Lit régulier</option><option value="cradle">Berceau</option></select></label>
          <div className="ward-config__checks"><label><input type="checkbox" checked={bed.pediatric_suitable} onChange={(event) => setBed({ ...bed, pediatric_suitable: event.target.checked })} /> Pédiatrie</label><label><input type="checkbox" checked={bed.isolation_suitable} onChange={(event) => setBed({ ...bed, isolation_suitable: event.target.checked })} /> Isolement</label><label><input type="checkbox" checked={bed.accessible} onChange={(event) => setBed({ ...bed, accessible: event.target.checked })} /> Accessible</label></div>
          <button className="clinical-btn" type="submit">Ajouter le couchage</button>
        </form>
      </div>
    </section>
  );
}
