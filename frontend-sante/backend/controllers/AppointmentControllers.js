const Appointment = require("../models/Appointment");

const getAppointments = async (req, res) => {
  try {
    const appointments = await Appointment.find().populate("patient");
    res.json(appointments);
  } catch (error) {
    res.status(500).json({ message: "Error fetching appointments", error: error.message });
  }
};

const createAppointment = async (req, res) => {
  try {
    const { patient, date, reason } = req.body;

    const newAppointment = new Appointment({ patient, date, reason });
    const saved = await newAppointment.save();

    res.json(saved);
  } catch (error) {
    res.status(500).json({ message: "Error creating appointment", error: error.message });
  }
};

const deleteAppointment = async (req, res) => {
  try {
    await Appointment.findByIdAndDelete(req.params.id);
    res.json({ message: "Deleted" });
  } catch (error) {
    res.status(500).json({ message: "Error deleting appointment", error: error.message });
  }
};

module.exports = {
  getAppointments,
  createAppointment,
  deleteAppointment,
};