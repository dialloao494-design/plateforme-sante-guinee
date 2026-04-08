const mongoose = require("mongoose");

const appointmentSchema = new mongoose.Schema(
{
patient: {
type: mongoose.Schema.Types.ObjectId,
ref: "Patient",
required: true,
},
date: {
type: Date,
required: true,
},
reason: {
type: String,
required: true,
},
},
{ timestamps: true }
);

module.exports = mongoose.model("Appointment", appointmentSchema);