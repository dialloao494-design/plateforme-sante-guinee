const Patient = require('../models/Patient');

exports.getAllPatients = async (req, res) => {
  try {
    const patients = await Patient.find().sort({ createdAt: -1 });
    res.json(patients);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Impossible de récupérer les patients' });
  }
};

exports.createPatient = async (req, res) => {
  try {
    const { name, age, condition } = req.body;
    if (!name || age == null || !condition) {
      return res.status(400).json({ message: 'Nom, âge et condition sont requis' });
    }

    const patient = new Patient({ name, age, condition });
    const savedPatient = await patient.save();
    res.status(201).json(savedPatient);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Erreur lors de la création du patient' });
  }
};

exports.updatePatient = async (req, res) => {
  try {
    const { id } = req.params;
    const { name, age, condition } = req.body;
    if (!name || age == null || !condition) {
      return res.status(400).json({ message: 'Nom, âge et condition sont requis' });
    }

    const patient = await Patient.findByIdAndUpdate(
      id,
      { name, age, condition },
      { new: true, runValidators: true }
    );

    if (!patient) {
      return res.status(404).json({ message: 'Patient non trouvé' });
    }

    res.json(patient);
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Erreur lors de la mise à jour du patient' });
  }
};

exports.deletePatient = async (req, res) => {
  try {
    const { id } = req.params;
    const patient = await Patient.findByIdAndDelete(id);
    if (!patient) {
      return res.status(404).json({ message: 'Patient non trouvé' });
    }
    res.json({ message: 'Patient supprimé' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Erreur lors de la suppression du patient' });
  }
};
