import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import { PatientProvider } from './contexts/PatientContext.jsx'
import { AppointmentProvider } from './contexts/AppointmentContext.jsx'
import { AuthProvider } from './contexts/AuthContext.jsx'
import 'react-toastify/dist/ReactToastify.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <PatientProvider>
          <AppointmentProvider>
            <App />
          </AppointmentProvider>
        </PatientProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)