const express = require('express');
const router = express.Router();
const {
  getAllPatients,
  createPatient,
  updatePatient,
  deletePatient,
} = require('../controllers/patientController');

router.get('/', getAllPatients);
router.post('/', createPatient);
router.put('/:id', updatePatient);
router.delete('/:id', deletePatient);

module.exports = router;
