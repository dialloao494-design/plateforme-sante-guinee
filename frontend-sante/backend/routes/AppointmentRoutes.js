const express = require("express");
const router = express.Router();

const {
getAppointments,
createAppointment,
deleteAppointment,
} = require("../controllers/AppointmentControllers");

router.get("/", getAppointments);
router.post("/", createAppointment);
router.delete("/:id", deleteAppointment);

module.exports = router;