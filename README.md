# Internal Examination App

Flask + Turso (libSQL) exam tool for a fixed group of participants, per `PRD_Exam_Application.pdf`.

## Stack
- Flask (server-rendered Jinja templates)
- Turso (hosted libSQL, SQLite-compatible) via `libsql-client`
- Token-based participant access, password-protected admin dashboard

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` (already created, gitignored) holds:
- `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` — from `turso db show exam-app-db` / `turso db tokens create exam-app-db`
- `FLASK_SECRET_KEY` — session signing key
- `ADMIN_PASSWORD` — admin dashboard login

Apply the schema once (safe to re-run — uses `CREATE TABLE IF NOT EXISTS`):
```bash
python scripts/init_db.py
```

## Loading real content

1. **Questions** — write a JSON file:
   ```json
   [
     {"question_text": "...", "points": 1, "options": ["A", "B", "C", "D"], "correct_index": 0}
   ]
   ```
   Then: `python scripts/seed_questions.py questions.json`

2. **Participants** — write a CSV with a header row `name,email` (email optional), then:
   ```bash
   python scripts/add_participants.py participants.csv links_out.csv
   ```
   `links_out.csv` contains each participant's unique exam link — distribute these.
   Set `BASE_URL` in `.env` (e.g. `https://your-deployed-domain`) before running this so the
   generated links point at the right host. Safe to re-run for late joiners.

3. **Dry run** — `python scripts/seed_dummy.py` inserts 3 sample questions and 2 test
   participants for a test pass before loading real content (matches PRD Section 13, step 4).

## Running locally

```bash
python run.py
```
Visit `http://127.0.0.1:5000/exam/<token>` for a participant, `http://127.0.0.1:5000/admin` for the
admin dashboard.

## Answer key corrections

If a question's correct answer needs fixing after the exam has been taken:
1. Fix it directly in the DB (`turso db shell exam-app-db`) or via a small script.
2. Run `python scripts/rescore.py` to recompute `is_correct`/`total_score` for every submitted attempt.

## Deploying (not done yet)

A `Procfile` (`web: gunicorn "app:create_app()"`) is ready for Render or a similar host. Since the
database already lives on Turso, the app server itself can be fully ephemeral/stateless — no local
SQLite file, no persistence risk on redeploy.
