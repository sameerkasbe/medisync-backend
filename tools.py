"""Database-backed tools available to the autonomous documentation agent."""

from db import supabase


def get_patient_record(patient_id):
    response = (
        supabase.table("patients")
        .select("id,name,age,gender")
        .eq("id", patient_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return {"success": False, "error": f"Patient {patient_id} not found"}

    patient = response.data[0]
    return {
        "success": True,
        "tool": "patient_record_lookup",
        "data": {
            "patient_id": patient["id"],
            "name": patient["name"],
            "age": patient["age"],
            "sex": patient["gender"],
        },
    }


def get_consultation(patient_id):
    response = (
        supabase.table("consultations")
        .select("id,patient_id,consultation_text,created_at")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return {"success": False, "error": "Consultation not found"}

    row = response.data[0]
    return {
        "success": True,
        "tool": "consultation_lookup",
        "data": {
            "date": row.get("created_at"),
            "transcript": row["consultation_text"],
        },
    }


def get_allergies(patient_id):
    response = (
        supabase.table("allergies")
        .select("id,allergy_name,reaction,status,source,created_at")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .execute()
    )

    allergies = [
        {
            "substance": row.get("allergy_name"),
            "reaction": row.get("reaction"),
            "status": row.get("status"),
            "source": row.get("source"),
        }
        for row in response.data
    ]

    return {
        "success": True,
        "tool": "allergy_lookup",
        "data": allergies,
    }


def get_medications(patient_id):
    response = (
        supabase.table("medications")
        .select("id,medication_name,dosage,frequency,status,created_at")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .execute()
    )

    medications = [
        {
            "name": row["medication_name"],
            "dose": row.get("dosage"),
            "frequency": row.get("frequency"),
            "status": row.get("status"),
        }
        for row in response.data
    ]

    return {
        "success": True,
        "tool": "medication_lookup",
        "data": medications,
    }


def get_labs(patient_id):
    response = (
        supabase.table("laboratory_reports")
        .select("id,test_name,result,unit,reference_range,reported_at")
        .eq("patient_id", patient_id)
        .order("reported_at", desc=True)
        .execute()
    )

    labs = [
        {
            "test": row["test_name"],
            "value": row.get("result"),
            "unit": row.get("unit"),
            "reference_range": row.get("reference_range"),
            "date": row.get("reported_at"),
        }
        for row in response.data
    ]

    return {
        "success": True,
        "tool": "laboratory_lookup",
        "data": labs,
    }


def get_previous_notes(patient_id):
    response = (
        supabase.table("previous_notes")
        .select("id,note_text,created_at")
        .eq("patient_id", patient_id)
        .order("created_at", desc=True)
        .execute()
    )

    notes = [
        {
            "date": row.get("created_at"),
            "author": "Synthetic Clinician",
            "note": row["note_text"],
        }
        for row in response.data
    ]

    return {
        "success": True,
        "tool": "previous_notes_lookup",
        "data": notes,
    }


def validate_record(record):
    """Simple deterministic validation layer for the MVP."""
    required = [
        "patient_id",
        "patient_name",
        "consultation_summary",
        "medications",
        "allergies",
        "laboratory_information",
        "identified_conflicts",
        "follow_up_actions",
    ]

    missing = [field for field in required if not record.get(field)]

    checks = {
        "required_fields_present": len(missing) == 0,
        "patient_identity_present": bool(record.get("patient_id") and record.get("patient_name")),
        "source_conflicts_documented": "identified_conflicts" in record,
        "human_review_flag_present": "human_review_required" in record,
    }

    return {
        "valid": not missing and all(checks.values()),
        "missing_fields": missing,
        "checks": checks,
    }


def save_agent_run(patient_id, goal, final_status, human_review_required, record, validation, steps):
    """Persist the completed agent run and its trace in Supabase."""
    run_response = (
        supabase.table("agent_runs")
        .insert({
            "patient_id": patient_id,
            "goal": goal,
            "final_status": final_status,
            "human_review_required": human_review_required,
            "final_record": record,
            "validation": validation,
        })
        .execute()
    )

    if not run_response.data:
        raise RuntimeError("Agent run could not be saved")

    run_id = run_response.data[0]["id"]

    rows = []
    for index, step in enumerate(steps, start=1):
        rows.append({
            "agent_run_id": run_id,
            "step_number": index,
            "step_type": step.get("stage"),
            "title": step.get("decision"),
            "description": step.get("action"),
            "result": {
                "tool": step.get("tool"),
                "result": step.get("result"),
                "status": step.get("status"),
            },
        })

    if rows:
        supabase.table("agent_steps").insert(rows).execute()

    return run_id
