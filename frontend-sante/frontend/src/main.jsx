import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import './lowBandwidth.css'
import App from './App.jsx'
import RouteErrorBoundary from './components/RouteErrorBoundary.jsx'
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
            <RouteErrorBoundary fallbackPath="/login">
              <App />
            </RouteErrorBoundary>
          </AppointmentProvider>
        </PatientProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)