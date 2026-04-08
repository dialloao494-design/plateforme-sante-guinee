# Frontend Migration Guide

This repository contains the FastAPI backend endpoint definitions and auth behavior. The frontend should use `http://127.0.0.1:8000` as the API base URL and attach the JWT token to protected requests.

## Backend base URL

- `http://127.0.0.1:8000`

## Auth endpoints

- `POST /auth/login` — login with form data (`username`, `password`)
- `GET /auth/me` — fetch current user info with `Authorization: Bearer <token>`

## Core API endpoints

- `GET /patients` — list patients
- `GET /patients/me` — get current patient profile
- `POST /rendezvous/` — create appointment
- `GET /rendezvous/` — list appointments
- `GET /rendezvous/{rdv_id}` — get appointment details
- `PATCH /rendezvous/{rdv_id}` — update appointment status
- `POST /rendezvous/{rdv_id}/cancel` — cancel appointment
- `POST /payments/create-intent/{rdv_id}` — create Stripe payment intent
- `GET /payments/{rdv_id}/status` — get payment status

## CORS

The backend now enables CORS for all origins using `CORSMiddleware` in `main.py`.

## Recommended centralized API service (React + axios)

Create a single service file such as `src/services/api.js`.

```js
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

const getToken = () => localStorage.getItem("access_token");

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

## Login logic example

FastAPI uses OAuth2 password form data for `/auth/login`, so the frontend must send `application/x-www-form-urlencoded`.

```js
import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:8000";

export async function login(email, password) {
  const payload = new URLSearchParams();
  payload.append("username", email);
  payload.append("password", password);

  const response = await axios.post(`${API_BASE_URL}/auth/login`, payload.toString(), {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  const { access_token } = response.data;
  localStorage.setItem("access_token", access_token);
  return response.data;
}
```

## Protected request example

```js
import api from "../services/api";

export async function fetchCurrentUser() {
  const response = await api.get("/auth/me");
  return response.data;
}

export async function fetchAppointments() {
  const response = await api.get("/rendezvous/");
  return response.data;
}
```

## Patient and appointment API examples

```js
export async function fetchPatients() {
  return api.get("/patients/");
}

export async function fetchPatientProfile() {
  return api.get("/patients/me");
}

export async function createAppointment(appointmentData) {
  return api.post("/rendezvous/", appointmentData);
}

export async function cancelAppointment(appointmentId) {
  return api.post(`/rendezvous/${appointmentId}/cancel`);
}
```

## Notes on request formats

- `/auth/login` expects form fields `username` and `password`, not JSON.
- All protected routes require `Authorization: Bearer <token>`.
- Appointment creation and update endpoints expect JSON bodies matching the FastAPI schemas.

## If your frontend currently uses `localhost:5000`

Replace the base URL with `http://127.0.0.1:8000` and remove any Node/Express-specific response handling.

## Suggested next step

If you want, provide the actual frontend repo or source files so I can update the real `api` service, login page, and protected request calls directly.
