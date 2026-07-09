from sqlalchemy import *
from sqlalchemy.orm import relationship
from .db import Base
import datetime

class Patients(Base):
    __tablename__ = 'patients'

    id = Column(Integer, primary_key = True, index= True)
    name = Column(String, index=True)
    age= Column(Integer)
    gender= Column(String)
    phone= Column(VARCHAR(15))
    created_at= Column(DateTime, default=datetime.utcnow)


class Doctors(Base):
    __tablename__= "doctors"

    id= Column(Integer, primary_key = True, index= True)
    name= Column(String, index=True)
    department= Column(String)
    phone= Column(VARCHAR(15))
    available = Column(Boolean, default=True)

class Visits(Base):
    __tablename__ = "visits"
    
    id = Column(Integer)
    patient_id = Column(Integer, ForeignKey('patients.id'))
    doctor_id = Column(Integer, ForeignKey('doctors.id'))
    symptom_summary = Column(String)
    department = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Queue(Base):
    __tablename__ = "queue"

    id = Column(Integer, primary_key=True)
    visit_id = Column(Integer, ForeignKey('visits.id'))
    token_number = Column(Integer)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Triage(Base):
    __tablename__ = "triage"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('visits.id'))
    conversation_json= Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)