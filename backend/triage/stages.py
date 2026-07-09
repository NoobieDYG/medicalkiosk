from enum import Enum


class TriageStage(str, Enum):
    GREETING = "greeting"
    COLLECTING_SYMPTOMS = "collecting_symptoms"
    IDENTIFYING_PATIENT = "identifying_patient"
    COLLECTING_NEW_PATIENT_NAME = "collecting_new_patient_name"
    COLLECTING_NEW_PATIENT_AGE = "collecting_new_patient_age"
    COLLECTING_NEW_PATIENT_GENDER = "collecting_new_patient_gender"
    RECOMMENDING_DOCTOR = "recommending_doctor"
    AWAITING_DOCTOR_CHOICE = "awaiting_doctor_choice"
    READY_TO_FINALIZE = "ready_to_finalize"
    DONE = "done"