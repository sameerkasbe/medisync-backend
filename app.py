from flask import Flask, jsonify, request
from flask_cors import CORS

from db import supabase
from agent import run_agent

app = Flask(__name__)
CORS(app)


@app.get("/")
def home():
    return jsonify({
        "name": "MediSync AI",
        "message": "Autonomous Clinical Documentation & Follow-up Agent API",
        "status": "running",
        "environment": "synthetic",
        "database": "supabase",
    })


@app.get("/api/patients")
def patients():
    response = (
        supabase.table("patients")
        .select("id,name,age,gender")
        .order("id")
        .execute()
    )

    result = [
        {
            "patient_id": row["id"],
            "name": row["name"],
            "age": row["age"],
            "sex": row["gender"],
        }
        for row in response.data
    ]

    return jsonify(result)


@app.get("/api/patients/<patient_id>")
def patient(patient_id):
    response = (
        supabase.table("patients")
        .select("id,name,age,gender,created_at")
        .eq("id", patient_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return jsonify({"error": "Patient not found"}), 404

    patient_data = response.data[0]

    return jsonify({
        "patient_id": patient_data["id"],
        "name": patient_data["name"],
        "age": patient_data["age"],
        "sex": patient_data["gender"],
    })


@app.post("/api/agent/run")
def agent_run():
    body = request.get_json(silent=True) or {}
    patient_id = body.get("patient_id")

    if not patient_id:
        return jsonify({
            "success": False,
            "error": "patient_id is required"
        }), 400

    try:
        result = run_agent(patient_id)
    except Exception as exc:
        app.logger.exception("Agent run failed")
        return jsonify({
            "success": False,
            "error": str(exc),
        }), 500

    if not result["success"]:
        return jsonify(result), 404

    return jsonify(result)


@app.get("/api/agent/runs")
def agent_runs():
    response = (
        supabase.table("agent_runs")
        .select("id,patient_id,goal,final_status,human_review_required,created_at")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return jsonify(response.data)


@app.get("/api/agent/runs/<int:run_id>")
def agent_run_detail(run_id):
    run_response = (
        supabase.table("agent_runs")
        .select("*")
        .eq("id", run_id)
        .limit(1)
        .execute()
    )

    if not run_response.data:
        return jsonify({"error": "Agent run not found"}), 404

    steps_response = (
        supabase.table("agent_steps")
        .select("*")
        .eq("agent_run_id", run_id)
        .order("step_number")
        .execute()
    )

    return jsonify({
        "run": run_response.data[0],
        "steps": steps_response.data,
    })


@app.get("/api/health")
def health():
    try:
        supabase.table("patients").select("id").limit(1).execute()
        database_status = "connected"
    except Exception:
        database_status = "error"

    return jsonify({
        "status": "healthy" if database_status == "connected" else "degraded",
        "service": "medisync-backend",
        "database": database_status,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
