/**
 * Guinea-focused geography for doctor discovery filters and future map / "nearby" ranking.
 * Coordinates are approximate centroids for distance sorting (Haversine-ready).
 */

export const GUINEA_REGION_OPTIONS = [
  { value: '', label: 'Toute la Guinée' },
  { value: 'Conakry', label: 'Conakry (toutes communes)' },
  { value: 'Kaloum', label: 'Conakry · Kaloum' },
  { value: 'Dixinn', label: 'Conakry · Dixinn' },
  { value: 'Ratoma', label: 'Conakry · Ratoma' },
  { value: 'Matam', label: 'Conakry · Matam' },
  { value: 'Matoto', label: 'Conakry · Matoto' },
  { value: 'Kindia', label: 'Kindia' },
];

/** Lat/lon in decimal degrees — swap map provider later (MapLibre, Google, etc.) */
export const REGION_CENTROIDS = {
  Conakry: { lat: 9.537, lon: -13.6785 },
  Kaloum: { lat: 9.5092, lon: -13.7122 },
  Dixinn: { lat: 9.5271, lon: -13.655 },
  Ratoma: { lat: 9.5766, lon: -13.6478 },
  Matam: { lat: 9.5629, lon: -13.6014 },
  Matoto: { lat: 9.5912, lon: -13.576 },
  Kindia: { lat: 10.0569, lon: -12.8658 },
};

export function doctorMatchesRegion(cityText, regionValue) {
  if (!regionValue) return true;
  const t = String(cityText || '').toLowerCase();
  const r = regionValue.toLowerCase();
  if (r === 'conakry') return t.includes('conakry');
  return t.includes(r);
}

/** Haversine distance in km (for future "near me" when browser geolocation is enabled). */
export function distanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function inferCentroidFromCity(cityText) {
  const t = String(cityText || '').toLowerCase();
  for (const key of Object.keys(REGION_CENTROIDS)) {
    if (t.includes(key.toLowerCase())) {
      return REGION_CENTROIDS[key];
    }
  }
  if (t.includes('conakry')) return REGION_CENTROIDS.Conakry;
  return null;
}

export function sortDoctorsByProximity(doctors, userLat, userLon) {
  if (userLat == null || userLon == null) return doctors;
  return [...doctors].sort((a, b) => {
    const ca = inferCentroidFromCity(a.city || a.location);
    const cb = inferCentroidFromCity(b.city || b.location);
    if (!ca && !cb) return 0;
    if (!ca) return 1;
    if (!cb) return -1;
    const da = distanceKm(userLat, userLon, ca.lat, ca.lon);
    const db = distanceKm(userLat, userLon, cb.lat, cb.lon);
    return da - db;
  });
}

export const SPECIALTY_FILTER_OPTIONS = [
  { value: '', label: 'Toutes spécialités' },
  { value: 'Pédiatrie', label: 'Pédiatrie' },
  { value: 'Médecine générale', label: 'Médecine générale' },
  { value: 'Dermatologie', label: 'Dermatologie' },
  { value: 'Cardiologie', label: 'Cardiologie' },
  { value: 'Gynécologie', label: 'Gynécologie' },
  { value: 'ORL', label: 'ORL' },
];
