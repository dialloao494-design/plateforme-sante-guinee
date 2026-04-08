import { useState, useEffect, useMemo } from "react";
import PatientList from "../components/PatientList";
import "./Patients.css";

import {
getPatients,
addPatient,
updatePatient,
deletePatient,
} from "../api";

const Patients = () => {
const [formData, setFormData] = useState({
name: "",
age: "",
condition: "",
});

const [editingId, setEditingId] = useState(null);
const [search, setSearch] = useState("");

const [patients, setPatients] = useState([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const [success, setSuccess] = useState("");

// 🔄 FETCH PATIENTS
useEffect(() => {
const fetchPatients = async () => {
setLoading(true);
try {
const data = await getPatients();
setPatients(data);
} catch (err) {
setError("Erreur lors du chargement");
} finally {
setLoading(false);
}
};

fetchPatients();
}, []);

// ➕ SUBMIT (ADD / UPDATE)
const handleSubmit = async (e) => {
e.preventDefault();

const name = formData.name.trim();
const age = Number(formData.age);
const condition = formData.condition.trim();

if (!name || !age || !condition) return;

try {
if (editingId !== null) {
await updatePatient(editingId, { name, age, condition });

setPatients((prev) =>
prev.map((p) =>
p._id === editingId ? { ...p, name, age, condition } : p
)
);

setSuccess("Patient modifié avec succès");
} else {
const newPatient = await addPatient({ name, age, condition });

setPatients((prev) => [...prev, newPatient]);

setSuccess("Patient ajouté avec succès");
}

setFormData({ name: "", age: "", condition: "" });
setEditingId(null);
} catch (err) {
setError("Erreur lors de l'opération");
}
};

// ❌ DELETE
const handleDelete = async (id) => {
try {
await deletePatient(id);

setPatients((prev) => prev.filter((p) => p._id !== id));

setSuccess("Patient supprimé");
} catch (err) {
setError("Erreur lors de la suppression");
}
};

// ✏️ EDIT
const handleEdit = (patient) => {
setEditingId(patient._id);
setFormData({
name: patient.name,
age: String(patient.age),
condition: patient.condition,
});
};

// ❌ CANCEL EDIT
const handleCancel = () => {
setEditingId(null);
setFormData({ name: "", age: "", condition: "" });
};

// 🔍 SEARCH
const filteredPatients = useMemo(() => {
return patients.filter((p) =>
p.name.toLowerCase().includes(search.toLowerCase())
);
}, [patients, search]);

return (
<div>
<h2>Gestion des patients</h2>

{/* 🔔 MESSAGES */}
{loading && <p>Chargement...</p>}
{error && <p style={{ color: "red" }}>{error}</p>}
{success && <p style={{ color: "green" }}>{success}</p>}

{/* 🔍 SEARCH */}
<input
type="text"
placeholder="Rechercher un patient..."
value={search}
onChange={(e) => setSearch(e.target.value)}
/>

<p>Total: {filteredPatients.length}</p>

{/* 📝 FORM */}
<form onSubmit={handleSubmit}>
<input
type="text"
placeholder="Nom"
value={formData.name}
onChange={(e) =>
setFormData({ ...formData, name: e.target.value })
}
/>

<input
type="number"
placeholder="Âge"
value={formData.age}
onChange={(e) =>
setFormData({ ...formData, age: e.target.value })
}
/>

<input
type="text"
placeholder="Condition"
value={formData.condition}
onChange={(e) =>
setFormData({ ...formData, condition: e.target.value })
}
/>

<button type="submit">
{editingId ? "Mettre à jour" : "Ajouter"}
</button>

{editingId && (
<button type="button" onClick={handleCancel}>
Annuler
</button>
)}
</form>

{/* 📋 LISTE */}
<PatientList
patients={filteredPatients}
onDelete={handleDelete}
onEdit={handleEdit}
/>
</div>
);
};

export default Patients;