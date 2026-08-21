from sqlalchemy import *
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .db import Base
import datetime


class Patients(Base):
    __tablename__ = 'patients'

    id = Column(Integer, primary_key = True, index= True)
    hospital_id= Column(Integer,default=1,nullable=False)
    name = Column(String, index=True)
    age= Column(Integer)
    gender= Column(String)
    phone= Column(VARCHAR(15))
    created_at= Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))


class Doctors(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, default=1, nullable=False)
    name = Column(String, index=True)
    department = Column(String)
    phone = Column(VARCHAR(15))
    available = Column(Boolean, default=True)


class DoctorSchedules(Base):
    __tablename__ = "doctor_schedules"
    id = Column(Integer, primary_key=True)
    hospital_id = Column(Integer, default=1, nullable=False)
    doctor_id = Column(Integer, ForeignKey('doctors.id'), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # Monday=0 ... Sunday=6, matches Python's datetime.weekday()
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)


class Visits(Base):
    __tablename__ = "visits"
    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, default=1, nullable=False)
    kiosk_id = Column(Integer, default = 1, nullable = True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey('doctors.id'), nullable=False, index=True)
    symptom_summary = Column(String)
    department = Column(String)
    icd_code = Column(String)
    ai_impression = Column(String)
    status = Column(String, default="waiting")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))


class Queue(Base):
    __tablename__ = "queue"
    id = Column(Integer, primary_key=True)
    hospital_id = Column(Integer, default=1, nullable=False)
    visit_id = Column(Integer, ForeignKey('visits.id'), nullable=False, index=True)
    token_number = Column(Integer)
    status = Column(String, default="waiting", index=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))


class Triage(Base):
    __tablename__ = "triage"
    id = Column(Integer, primary_key=True)
    hospital_id = Column(Integer, default=1, nullable=False)
    visit_id = Column(Integer, ForeignKey('visits.id'), nullable=False, index=True)
    conversation_json = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))


class ICDCodes(Base):
    __tablename__ = "icd_codes"
    id = Column(Integer, primary_key=True)
    hospital_id = Column(Integer, default=1, nullable=False)
    code = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)
    department = Column(String, nullable=False)
    embedding = Column(Vector(512))  # Adjust the dimension based on your embedding model

