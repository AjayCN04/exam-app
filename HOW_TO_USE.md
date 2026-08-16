# How to Run and Use This Exam App (Plain-English Guide)

This app lets a fixed group of people take a multiple-choice exam through a
unique link each, and lets the admin create exams, manage the participant
list, and see results — all from a browser. This guide covers running it
**locally on your Mac, exposed to the internet via ngrok**, so people outside
your machine can reach it.

## 1. Starting it up

Open Terminal, then:

```bash
cd /Users/wallstreet59/Documents/exam-app
scripts/local_start.sh
```

Wait a few seconds. You'll see something like:

```
Exam app is live.
Public URL:   https://xxxx-xxxx-xxxx.ngrok-free.dev
Admin login:  https://xxxx-xxxx-xxxx.ngrok-free.dev/admin/login
```

That **Public URL** is what you share with people (with `/exam/<their token>`
appended for participants, see below). It also gets saved to `.run/public_url.txt`
if you need to find it again later without restarting.

**Important:** every time you run `local_start.sh`, ngrok gives you a
*different* random URL (unless you've claimed a static domain in your ngrok
account). If you restart, any links you already handed out will stop working
until you regenerate them with the new URL.

## 2. Stopping it

```bash
scripts/local_stop.sh
```

This shuts down both the app server and the ngrok tunnel cleanly. Do this
when you're done for the day, or before starting again.

## 3. Logging in as Admin

1. Go to `<your public URL>/admin/login`
2. Enter the admin password. This is stored in the `.env` file, under
   `ADMIN_PASSWORD=`. Open that file in a text editor if you forget it.
3. You'll land on the admin home page with three tiles:
   - **Create Exam** — pick a question set, choose modules and how many
     questions per module, pick which participants get access, and set a
     pass percentage. Submitting shows a confirmation page listing every
     participant's exam link, ready to copy and send.
   - **Manage Users** — add, edit, or archive participants. Archiving hides
     someone from active lists without deleting their history.
   - **View Exam Results** — pick an exam to see everyone's status, score,
     and submission time, with a CSV export button. Click a participant's
     row for a question-by-question breakdown of their answers.

## 4. Getting participants' links

Every participant has one link, in the form:

```
<public URL>/exam/<their unique token>
```

- **If you just created the exam**: the confirmation page right after
  submitting the Create Exam form lists every participant's link — copy from
  there.
- **If the exam already exists and you need the links again** (e.g. the
  ngrok URL changed since you last generated them), run:
  ```bash
  .venv/bin/python scripts/list_current_links.py
  ```
  This prints every active participant's current link, exam, and status
  (not started / in progress / completed), using whatever public URL is
  currently running.

Participants just open their link in any browser — no login, no password.
They see their name, all the questions, and a Submit button. Once submitted,
they can't go back in.

## 5. Adding more participants later

Use **Manage Users → Add participant** in the admin console for one-off
additions. For a bulk list (e.g. an Excel sheet of names and emails):

```bash
.venv/bin/python scripts/add_participants.py content/your_file.xlsx content/links.csv
```

Then grant them access to a specific exam so they get a link for it:

```bash
.venv/bin/python scripts/grant_exam_access.py <exam_number> <email1> <email2> ...
```

## 6. If something looks wrong

- **"Not Found" at the bare URL (no `/admin` or `/exam/...`)** — expected, this
  app has no page at `/`. Use `/admin/login` or a specific `/exam/<token>` link.
- **Links stopped working** — the ngrok URL probably changed on the last
  restart. Re-run `scripts/list_current_links.py` to get fresh ones, or ask
  for the exam to be re-shared.
- **Check what's running**: `.run/gunicorn.log` and `.run/ngrok.log` hold the
  server and tunnel logs if anything misbehaves.
