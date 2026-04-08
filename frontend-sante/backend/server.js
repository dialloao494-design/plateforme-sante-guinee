require('dotenv').config();
const express = require('express');
const cors = require('cors');
const connectDB = require('./config/db');
const patientRoutes = require('./routes/patientRoutes');
const appointmentRoutes = require('./routes/AppointmentRoutes');
const app = express();
const PORT = process.env.PORT || 5001;

connectDB();

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
  res.send('API patient management is running');
});

app.use('/api/patients', patientRoutes);
app.use('/api/appointments', appointmentRoutes);

app.use((req, res) => {
  res.status(404).json({ message: 'Route non trouvée' });
});

app.use((err, req, res, next) => {
  console.error('App error: ', err);
  res.status(500).json({ message: 'Erreur serveur interne' });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});