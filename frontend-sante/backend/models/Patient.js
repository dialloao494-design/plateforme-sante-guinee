const mongoose = require('mongoose');

const PatientSchema = new mongoose.Schema(
  {
    name: { type: String, required: true, trim: true },
    age: { type: Number, required: true, min: 0 },
    condition: { type: String, required: true, trim: true },
  },
  { timestamps: true }
);

module.exports = mongoose.model('Patient', PatientSchema);
