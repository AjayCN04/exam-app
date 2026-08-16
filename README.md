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

Recommended: author content in Excel. Run once to generate starting templates:
```bash
python scripts/make_content_templates.py
```
This creates `content/questions_template.xlsx` and `content/participants_template.xlsx`
(the `content/` folder is gitignored — it's meant to hold your real, unpublished exam data).

1. **Questions** — open `questions_template.xlsx` and fill in one row per question:
   - `question_text`, `points` (optional, defaults to 1)
   - `option_1`, `option_2`, `option_3`, `option_4`, ... — as many option columns as needed;
     leave a cell blank if a question has fewer options than the widest row
   - `correct_option` — the **column number** of the correct option (e.g. `2` means `option_2`
     is correct), not its position among filled-in options

   Then: `python scripts/seed_questions.py content/questions_template.xlsx`

   The script validates every row before writing anything — a blank `question_text`, fewer than
   2 filled options, or a `correct_option` that doesn't match a filled column aborts with the
   offending row numbers and touches the database only once everything checks out.

   (A raw JSON file also still works, if you'd rather hand-write it:
   `[{"question_text": "...", "points": 1, "options": [...], "correct_index": 0}, ...]`,
   `correct_index` is 0-based here — different from the xlsx `correct_option`.)

2. **Participants** — open `participants_template.xlsx` and fill in `name` (required) and
   `email` (optional), one row per participant. Then:
   ```bash
   python scripts/add_participants.py content/participants_template.xlsx content/links.csv
   ```
   `links.csv` contains each participant's unique exam link — distribute these.
   Set `BASE_URL` in `.env` (e.g. `https://your-deployed-domain`) before running this so the
   generated links point at the right host. Safe to re-run for late joiners.

   (A CSV with header row `name,email` also still works instead of `.xlsx`.)

3. **Dry run** — `python scripts/seed_dummy.py` inserts 3 sample questions and 2 test
   participants for a test pass before loading real content (matches PRD Section 13, step 4).

Word documents are intentionally not supported — free-form text can't be parsed reliably enough
for something correctness-sensitive like an answer key.

## Adding another question set

To add a new Question Set (its own entry in the admin "Create Exam" dropdown, with its own
modules and questions), use `scripts/import_master_question_list.py` instead of the scripts above.
It expects a `.xlsx` or `.csv` with columns `Module, Question, Answer Choice 1-4, Correct Choice
Number, Correct Choice, Justification` (one row per question; `Correct Choice Number`/`Correct
Choice` may be `;`-separated for multi-select "select all that apply" questions) — see
`app/exam_content/Claude_Architect_Foundations_Master_Question_List.xlsx` for the exact format.

```bash
python scripts/import_master_question_list.py path/to/file.xlsx --set-name "Your Question Set Name"
```

This creates the `question_sets` row if it doesn't exist yet, reuses any `exam_modules` that
already match by name (modules are shared globally across sets) or creates new ones from the
file's `Module` column, and validates every row before writing anything. The set then shows up
automatically in the admin Create Exam dropdown — no code changes needed.

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

## Deploying

Deployed on [Render](https://render.com)'s free Web Service tier via the `render.yaml` Blueprint at
the repo root. Since the database lives on Turso, the app server itself is fully
ephemeral/stateless — no local SQLite file, no persistence risk on redeploy.

To deploy: push this repo to GitHub, then in Render **New → Blueprint** and select it. Render reads
`render.yaml` for the build/start commands and prompts for the secret env vars
(`TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, `FLASK_SECRET_KEY`, `ADMIN_PASSWORD`) at deploy time —
copy these from your local `.env`; they're never committed.

Note: the free tier sleeps after 15 minutes of inactivity (~30-60s cold start on the next request).

Once deployed, set `BASE_URL` to the Render-assigned URL when generating links locally:
```bash
BASE_URL=https://your-service.onrender.com python scripts/grant_exam_access.py <exam_number> <email>
```
