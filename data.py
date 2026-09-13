"""Synthetic patient data for the MediSync AI hackathon MVP.
No real patient information is used.
"""

PATIENTS = {
    "P001": {
        "patient_id": "P001",
        "name": "Rahul Sharma",
        "age": 42,
        "sex": "Male",
        "consultation": {
            "date": "2026-09-13",
            "transcript": (
                "Patient reports that he developed a skin rash after taking penicillin "
                "several years ago. He is here for a routine follow-up. "
                "No current emergency symptoms are reported."
            ),
        },
        "allergies": [
            {"substance": "No known allergies", "status": "active", "source": "allergy_database"}
        ],
        "medications": [
            {"name": "Metformin", "dose": "500 mg", "frequency": "twice daily", "status": "active"}
        ],
        "labs": [
            {"test": "HbA1c", "value": "7.1", "unit": "%", "date": "2026-09-10"},
            {"test": "Creatinine", "value": "0.9", "unit": "mg/dL", "date": "2026-09-10"},
        ],
        "previous_notes": [
            {
                "date": "2025-11-04",
                "author": "Synthetic Clinician",
                "note": (
                    "Patient previously reported a skin reaction after penicillin. "
                    "No formal allergy classification recorded."
                ),
            }
        ],
    },
    "P002": {
        "patient_id": "P002",
        "name": "Ananya Patel",
        "age": 29,
        "sex": "Female",
        "consultation": {
            "date": "2026-09-13",
            "transcript": (
                "Routine follow-up. Patient reports no new medication reactions "
                "and says current medications are unchanged."
            ),
        },
        "allergies": [
            {"substance": "No known allergies", "status": "active", "source": "allergy_database"}
        ],
        "medications": [
            {"name": "Vitamin D3", "dose": "1000 IU", "frequency": "daily", "status": "active"}
        ],
        "labs": [
            {"test": "Vitamin D", "value": "32", "unit": "ng/mL", "date": "2026-09-09"}
        ],
        "previous_notes": [
            {
                "date": "2026-05-12",
                "author": "Synthetic Clinician",
                "note": "Routine follow-up. No medication changes documented.",
            }
        ],
    },
}


def get_patient(patient_id):
    return PATIENTS.get(patient_id)
