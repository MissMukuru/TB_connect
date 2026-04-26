# ShieldTB Kenya FastAPI Backend

## Setup

From repo root:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r apps/backend/requirements.txt
```

Ensure `.env` (repo root) contains:
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (service role; keep private)

## Run

```bash
uvicorn main:app --reload --port 8000
```

Open:
- Docs: `http://localhost:8000/api/docs`

