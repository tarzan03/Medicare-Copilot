from pydantic import BaseModel
from datetime import date, datetime


class PatientSchema(BaseModel):
    patient_id: str
    patient_name: str
    gender: bool

    email: str
    phone_number: str

    diagnosis: str
    current_medication: str

    lab_test: str
    lab_value: float
    lab_unit: str

    last_visit_date: date
    next_scheduled_visit: date
    days_since_last_visit: int
    missed_last_appointment: bool

    vitals_bp_systolic: int
    vitals_bp_diastolic: int
    vitals_heart_rate: int
    vitals_spo2: float

    notes: str
