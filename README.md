# MediSync AI Backend

Flask + Supabase backend for the Agentic AI Hackathon P1 healthcare documentation problem.

## Setup

```powershell
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
```

Put your Supabase credentials in `.env`:

```env
SUPABASE_URL=your-project-url
SUPABASE_SERVICE_ROLE_KEY=your-server-side-service-role-key
```

Never expose `SUPABASE_SERVICE_ROLE_KEY` to React/frontend or commit `.env` to GitHub.

## Run

```powershell
python app.py
```

## Endpoints

- `GET /`
- `GET /api/health`
- `GET /api/patients`
- `GET /api/patients/<patient_id>`
- `POST /api/agent/run` with `{ "patient_id": "P001" }`
- `GET /api/agent/runs`
- `GET /api/agent/runs/<run_id>`

The agent now reads patient information from Supabase and persists completed runs and agent steps.
