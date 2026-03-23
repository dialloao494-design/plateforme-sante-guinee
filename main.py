from dotenv import load_dotenv 
load_dotenv()

from fastapi import FastAPI
from database import engine, Base
import models
from routers import patient, rendezvous, doctor, auth, payments, teleconsultation, notifications
import os


app = FastAPI()

# Create tables
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(patient.router)
app.include_router(rendezvous.router)
app.include_router(doctor.router)
app.include_router(auth.router)
app.include_router(payments.router)
app.include_router(teleconsultation.router)
app.include_router(notifications.router) 