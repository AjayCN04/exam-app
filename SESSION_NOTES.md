# Exam App — Session Notes (consolidated as of 2026-08-16)

Internal exam tool: Flask + Turso (libSQL), token-based participant links,
password-protected admin console. See [README.md](README.md) for setup/deploy
and [HOW_TO_USE.md](HOW_TO_USE.md) for the plain-English day-to-day guide
(local run via ngrok, admin walkthrough, getting participant links).

## Current state

- Deployed on Render (free tier, Blueprint via `render.yaml`); Turso holds all
  data, so the app server is stateless/ephemeral.
- Local dev/demo path: `scripts/local_start.sh` / `scripts/local_stop.sh` run
  gunicorn + an ngrok tunnel together, writing logs to `.run/` (now
  gitignored) and the current public URL to `.run/public_url.txt`.
- `scripts/list_current_links.py` reprints every active participant's current
  exam link + status (not started / in progress / completed) using whatever
  public URL is currently live — needed because ngrok hands out a new URL
  each restart unless a static domain is claimed.

## Recent work (commit history, newest first)

| Date | Commit | Change |
|------|--------|--------|
| 2026-08-12 | `a6e644b` | Show answer justification in participant detail and CSV export |
| 2026-08-12 | `ebeb751` | Fix Create/Edit Exam module selection when two question sets share a module |
| 2026-08-12 | `e968b87` | Add multi-select ("select all that apply") question support |
| 2026-08-12 | `28acf1e` | Configure gunicorn worker concurrency for Render |
| 2026-08-10 | `5cb7d87` | Add a favicon |
| 2026-08-09 | `65c7bf0` | Randomize per-module question selection instead of always the first N |
| 2026-08-08 | `8bc864c` | Add Close/Edit/Archive lifecycle for exams; rename to "Exams and Results" |
| 2026-08-08 | `5e8172d` | Improve participant CSV export: named filename, headers, text wrapping |
| 2026-08-08 | `4fe6e95` | Add filter and sort controls to the exam results table |
| 2026-08-08 | `baabd1b` | Add participant CSV export and a percentage column to exam results |
| 2026-08-08 | `1a5401a` | Add Select All for participants on the Create Exam form |
| 2026-08-08 | `3a58fb0` | Add copy-link icon and friendlier status labels to exam results |
| 2026-08-08 | `849d3d0` | Restyle admin section with a dark theme |
| 2026-08-08 | `ab3014d` | Move Archive action from users list into the Edit User page |
| 2026-08-08 | `ed2665b` | Add denormalized user_name/exam_name to exam_scores, kept in sync on rename |
| 2026-08-07 | `f50bd85` | Add Result (Pass/Fail) column to per-exam results table and CSV export |
| 2026-08-07 | `9b3ca35` | Add admin console: home page, user management, exam creation, per-exam results |
| 2026-08-07 | `66e7bfd` | Fix admin dashboard to use v2 schema |
| 2026-08-07 | `2fee8d3` | Wire v2 schema into the exam-taking flow and prepare for deployment |
| 2026-08-06 | `3467fc2` | Add direct .xlsx import for questions and participants |
| 2026-08-06 | `f2fb463` | Initial exam app: Flask + Turso, token-based participant access, admin dashboard |

## Not yet committed (as of this note)

- `HOW_TO_USE.md` — plain-English guide for local/ngrok operation
- `scripts/local_start.sh`, `scripts/local_stop.sh` — local app + ngrok tunnel
  lifecycle scripts
- `scripts/list_current_links.py` — reprint current participant links/status
- `.gitignore` — added `.run/` (holds gunicorn/ngrok pid files and logs from
  the local-start scripts, and the ephemeral current public URL)

These are working-tree additions supporting local ngrok-based demoing; review
and commit when ready.
