import os
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in .env")

client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = """
You are MediSync AI, an autonomous clinical documentation and
information-reconciliation assistant.

IMPORTANT SAFETY RULES:
- Work ONLY with synthetic/deidentified patient information.
- Do NOT diagnose diseases.
- Do NOT prescribe medications.
- Do NOT make consequential clinical decisions.
- Do NOT invent patient facts.
- When sources conflict, explicitly identify the conflict.
- Unresolved consequential conflicts MUST be escalated for human review.
- Your job is documentation, reconciliation, evidence organization,
  validation support, and follow-up action generation.

You are given information retrieved from multiple synthetic sources:
patient record, consultation, allergies, medications, laboratory reports,
and previous clinical notes.

Analyze the information and return a structured follow-up documentation
result.

Your reasoning should answer:
1. What information agrees across sources?
2. What information conflicts?
3. What additional evidence helps resolve the conflict?
4. Is the conflict actually resolved?
5. What should be documented?
6. Does human review remain necessary?

Never convert an uncertain or patient-reported statement into a confirmed
clinical diagnosis or allergy classification.
"""


def analyze_patient_record(source_data):
    """
    Send reconciled synthetic patient information to the LLM.
    The LLM performs documentation/reconciliation reasoning only.
    """

    prompt = f"""
Create a verified synthetic clinical follow-up documentation record.

PATIENT:
{json.dumps(source_data.get("patient"), indent=2)}

CONSULTATION:
{json.dumps(source_data.get("consultation"), indent=2)}

ALLERGIES:
{json.dumps(source_data.get("allergies"), indent=2)}

MEDICATIONS:
{json.dumps(source_data.get("medications"), indent=2)}

LABORATORY REPORTS:
{json.dumps(source_data.get("labs"), indent=2)}

PREVIOUS NOTES:
{json.dumps(source_data.get("previous_notes"), indent=2)}

Return ONLY valid JSON with this structure:

{{
  "summary": "string",
  "agreements": ["string"],
  "conflicts": [
    {{
      "type": "string",
      "description": "string",
      "sources": ["string"],
      "resolution": "resolved | unresolved"
    }}
  ],
  "supporting_evidence": ["string"],
  "follow_up_actions": ["string"],
  "human_review_required": true,
  "final_status": "VERIFIED | VERIFIED WITH HUMAN REVIEW"
}}

If there is a consequential unresolved conflict, human_review_required
must be true and final_status must be "VERIFIED WITH HUMAN REVIEW".
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=SYSTEM_PROMPT,
        input=prompt,
    )

    text = response.output_text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "summary": text,
            "agreements": [],
            "conflicts": [],
            "supporting_evidence": [],
            "follow_up_actions": [
                "Review the generated documentation manually."
            ],
            "human_review_required": True,
            "final_status": "VERIFIED WITH HUMAN REVIEW",
        }