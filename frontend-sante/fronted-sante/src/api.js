const API_URL = "http://localhost:5000/api/patients";

export const getPatients = async () => {
const res = await fetch(API_URL);
return res.json();
};

export const addPatient = async (patient) => {
const res = await fetch(API_URL, {
method: "POST",
headers: {
"Content-Type": "application/json",
},
body: JSON.stringify(patient),
});
return res.json();
};

export const updatePatient = async (id, patient) => {
const res = await fetch(`${API_URL}/${id}`, {
method: "PUT",
headers: {
"Content-Type": "application/json",
},
body: JSON.stringify(patient),
});
return res.json();
};

export const deletePatient = async (id) => {
await fetch(`${API_URL}/${id}`, {
method: "DELETE",
});
};