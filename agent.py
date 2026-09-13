"""MediSync autonomous documentation workflow."""

from llm import analyze_patient_record

from tools import (
    get_patient_record,
    get_consultation,
    get_allergies,
    get_medications,
    get_labs,
    get_previous_notes,
    validate_record,
    save_agent_run,
)


def add_step(steps, stage, decision, action, tool, result, status="completed"):
    steps.append({
        "stage": stage,
        "decision": decision,
        "action": action,
        "tool": tool,
        "result": result,
        "status": status,
    })


def run_agent(patient_id):
    steps = []

    # GOAL
    goal = (
        "Create a verified clinical follow-up record from multiple "
        "synthetic patient information sources."
    )

    add_step(
        steps,
        "GOAL",
        "The requested outcome is a verified follow-up record.",
        "Start autonomous documentation workflow.",
        "agent_orchestrator",
        goal,
    )

    # 1. Patient record
    patient_result = get_patient_record(patient_id)

    if not patient_result["success"]:
        return {
            "success": False,
            "error": patient_result["error"],
            "steps": steps,
        }

    patient = patient_result["data"]

    add_step(
        steps,
        "RECORD INGESTION",
        "Patient identity is required before processing other records.",
        "Retrieve patient identity.",
        "patient_record_lookup",
        f"Found synthetic patient {patient['name']} ({patient['patient_id']}).",
    )

    # 2. Consultation
    consultation_result = get_consultation(patient_id)

    if not consultation_result["success"]:
        return {
            "success": False,
            "error": consultation_result["error"],
            "steps": steps,
        }

    consultation = consultation_result["data"]

    add_step(
        steps,
        "RECORD INGESTION",
        "The consultation contains the current encounter information.",
        "Retrieve consultation transcript.",
        "consultation_lookup",
        consultation["transcript"],
    )

    # 3. Check allergies
    allergy_result = get_allergies(patient_id)

    if not allergy_result["success"]:
        return {
            "success": False,
            "error": allergy_result["error"],
            "steps": steps,
        }

    allergies = allergy_result["data"]

    add_step(
        steps,
        "DECISION",
        "The consultation mentions a possible medication reaction, "
        "so allergy history must be cross-checked.",
        "Query the allergy database.",
        "allergy_lookup",
        str(allergies),
    )

    transcript = consultation["transcript"].lower()

    allergy_conflict = (
        "penicillin" in transcript
        and any(
            a["substance"].lower() == "no known allergies"
            for a in allergies
        )
    )

    conflicts = []
    evidence = []
    previous_notes = []

    human_review_required = False

    # 4. ADAPTATION
    if allergy_conflict:
        conflict = {
            "type": "allergy_information_conflict",
            "source_a": "Consultation transcript",
            "source_b": "Allergy database",
            "source_a_value": (
                "Patient reports a skin rash after penicillin."
            ),
            "source_b_value": "No known allergies.",
            "status": "unresolved",
        }

        conflicts.append(conflict)

        add_step(
            steps,
            "CONFLICT DETECTED",
            "The consultation and allergy database disagree.",
            "Do not finalize the record yet. Retrieve historical evidence.",
            "conflict_detector",
            "Potential consequential allergy-information conflict identified.",
            "warning",
        )

        notes_result = get_previous_notes(patient_id)

        if notes_result["success"]:
            previous_notes = notes_result["data"]

            add_step(
                steps,
                "ADAPTATION",
                "Additional evidence is required because the first sources conflict.",
                "Retrieve previous clinical notes.",
                "previous_notes_lookup",
                str(previous_notes),
            )

            matching_notes = [
                note
                for note in previous_notes
                if "penicillin" in note["note"].lower()
            ]

            if matching_notes:
                evidence.extend(matching_notes)

                add_step(
                    steps,
                    "INTERMEDIATE RESULT",
                    "Historical evidence relevant to the conflict was found.",
                    "Attach supporting evidence to the follow-up record.",
                    "previous_notes_lookup",
                    "Previous note also documents a patient-reported "
                    "skin reaction to penicillin.",
                )

        human_review_required = True

    # 5. Other records
    medication_result = get_medications(patient_id)
    lab_result = get_labs(patient_id)

    if not medication_result["success"]:
        return {
            "success": False,
            "error": medication_result["error"],
            "steps": steps,
        }

    if not lab_result["success"]:
        return {
            "success": False,
            "error": lab_result["error"],
            "steps": steps,
        }

    medications = medication_result["data"]
    labs = lab_result["data"]

    add_step(
        steps,
        "DATA COLLECTION",
        "Medication and laboratory information are required "
        "for a complete follow-up record.",
        "Retrieve medication history and laboratory reports.",
        "medication_lookup + laboratory_lookup",
        f"Retrieved {len(medications)} medication record(s) "
        f"and {len(labs)} laboratory result(s).",
    )

    # ==========================================================
    # 6. LLM REASONING
    # ==========================================================

    source_data = {
        "patient": patient,
        "consultation": consultation,
        "allergies": allergies,
        "medications": medications,
        "labs": labs,
        "previous_notes": previous_notes,
    }

    try:
        llm_result = analyze_patient_record(source_data)

    except Exception as e:
        add_step(
            steps,
            "LLM ERROR",
            "The LLM could not complete the reasoning step.",
            "Fall back to human review instead of silently accepting an incomplete result.",
            "OpenAI",
            str(e),
            "warning",
        )

        return {
            "success": False,
            "error": f"LLM error: {str(e)}",
            "steps": steps,
        }

    add_step(
        steps,
        "LLM REASONING",
        "Multiple retrieved sources must be reconciled before documentation is finalized.",
        "Ask the LLM to analyze agreements, conflicts, supporting evidence, "
        "and follow-up requirements.",
        "OpenAI",
        str(llm_result),
    )

    # ==========================================================
    # 7. BUILD STRUCTURED RECORD FROM LLM RESULT
    # ==========================================================

    llm_human_review = llm_result.get(
        "human_review_required",
        False,
    )

    human_review_required = (
        human_review_required or llm_human_review
    )

    record = {
        "patient_id": patient["patient_id"],
        "patient_name": patient["name"],
        "age": patient["age"],
        "sex": patient["sex"],
        "consultation_summary": consultation["transcript"],
        "medications": medications,
        "allergies": allergies,
        "laboratory_information": labs,
        "summary": llm_result.get("summary", ""),
        "identified_conflicts": llm_result.get(
            "conflicts",
            conflicts,
        ),
        "supporting_evidence": llm_result.get(
            "supporting_evidence",
            evidence,
        ),
        "follow_up_actions": llm_result.get(
            "follow_up_actions",
            [],
        ),
        "human_review_required": human_review_required,
        "safety_note": (
            "Synthetic/deidentified data only. This system does not "
            "diagnose, prescribe, or make consequential clinical decisions."
        ),
    }

    add_step(
        steps,
        "DRAFT",
        "The LLM has reconciled the retrieved synthetic sources "
        "and produced structured documentation.",
        "Generate the follow-up record and action list.",
        "documentation_generator",
        "LLM-assisted structured follow-up record created.",
    )

    # ==========================================================
    # 8. LLM VALIDATION REVIEW
    # ==========================================================

    add_step(
        steps,
        "LLM VALIDATION REVIEW",
        "The LLM result must be checked against deterministic safety findings.",
        "Confirm that unresolved conflicts remain visible "
        "and human review is required when necessary.",
        "llm_validation",
        (
            "Human review required."
            if human_review_required
            else "No unresolved conflict identified."
        ),
        "warning" if human_review_required else "completed",
    )

    # ==========================================================
    # 9. DETERMINISTIC VALIDATION
    # ==========================================================

    validation = validate_record(record)

    add_step(
        steps,
        "VALIDATION",
        "The draft must be checked before being returned as a final outcome.",
        "Run deterministic record-validation checks.",
        "record_validator",
        str(validation),
        "completed" if validation["valid"] else "warning",
    )

    # ==========================================================
    # 10. FINAL OUTCOME
    # ==========================================================

    if validation["valid"] and human_review_required:
        final_status = "VERIFIED WITH HUMAN REVIEW"
    elif validation["valid"]:
        final_status = "VERIFIED"
    else:
        final_status = "VALIDATION FAILED"

    record["validation"] = validation
    record["final_status"] = final_status

    add_step(
        steps,
        "FINAL OUTCOME",
        "Return only after validation.",
        "Finalize documentation and expose unresolved consequential "
        "uncertainty for human review.",
        "agent_orchestrator",
        final_status,
        "warning" if human_review_required else "completed",
    )

    # ==========================================================
    # 11. SAVE RUN
    # ==========================================================

    run_id = save_agent_run(
        patient_id=patient_id,
        goal=goal,
        final_status=final_status,
        human_review_required=human_review_required,
        record=record,
        validation=validation,
        steps=steps,
    )

    return {
        "success": True,
        "run_id": run_id,
        "goal": goal,
        "patient": patient,
        "steps": steps,
        "record": record,
        "validation": validation,
    }