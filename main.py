from fastapi import FastAPI
from database import engine,Base
import models
from routers import patient, rendezvous, doctor, auth

app = FastAPI()

# Create tables
Base.metadata.create_all(bind=engine)  

# Include routers
app.include_router(patient.router)
app.include_router(rendezvous.router)
app.include_router(doctor.router)
app.include_router(auth.router) 