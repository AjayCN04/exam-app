from flask import Blueprint, abort, render_template, request

from . import db

exam_bp = Blueprint("exam", __name__)


def _get_participant(token):
    rs = db.execute("SELECT id, name FROM participants WHERE access_token = ?", [token])
    if not rs.rows:
        return None
    return rs.rows[0].asdict()


def _get_attempt(participant_id):
    rs = db.execute(
        "SELECT id, started_at, submitted_at FROM attempts WHERE participant_id = ?",
        [participant_id],
    )
    return rs.rows[0].asdict() if rs.rows else None


def _load_questions():
    q_rs = db.execute("SELECT id, question_text, order_index FROM questions ORDER BY order_index")
    questions = []
    for q_row in q_rs.rows:
        q = q_row.asdict()
        opt_rs = db.execute(
            "SELECT id, option_text, order_index FROM options WHERE question_id = ? ORDER BY order_index",
            [q["id"]],
        )
        q["options"] = [o.asdict() for o in opt_rs.rows]
        questions.append(q)
    return questions


@exam_bp.route("/exam/<token>", methods=["GET"])
def show_exam(token):
    participant = _get_participant(token)
    if not participant:
        abort(404)

    attempt = _get_attempt(participant["id"])
    if attempt and attempt["submitted_at"]:
        return render_template("already_completed.html", name=participant["name"])

    if not attempt:
        db.execute("INSERT INTO attempts (participant_id) VALUES (?)", [participant["id"]])

    questions = _load_questions()
    return render_template("exam.html", name=participant["name"], token=token, questions=questions)


@exam_bp.route("/exam/<token>/submit", methods=["POST"])
def submit_exam(token):
    participant = _get_participant(token)
    if not participant:
        abort(404)

    attempt = _get_attempt(participant["id"])
    if not attempt:
        abort(400)
    if attempt["submitted_at"]:
        return render_template("already_completed.html", name=participant["name"])

    q_rs = db.execute("SELECT id, points FROM questions")
    questions = [q.asdict() for q in q_rs.rows]

    total_score = 0
    for q in questions:
        selected_raw = request.form.get(f"q_{q['id']}")
        selected_id = int(selected_raw) if selected_raw else None

        is_correct = False
        if selected_id is not None:
            opt_rs = db.execute(
                "SELECT is_correct FROM options WHERE id = ? AND question_id = ?",
                [selected_id, q["id"]],
            )
            is_correct = bool(opt_rs.rows and opt_rs.rows[0].asdict()["is_correct"])

        if is_correct:
            total_score += q["points"]

        db.execute(
            "INSERT INTO answers (attempt_id, question_id, selected_option_id, is_correct) "
            "VALUES (?, ?, ?, ?)",
            [attempt["id"], q["id"], selected_id, 1 if is_correct else 0],
        )

    db.execute(
        "UPDATE attempts SET submitted_at = datetime('now'), total_score = ? WHERE id = ?",
        [total_score, attempt["id"]],
    )

    return render_template("already_completed.html", name=participant["name"], just_submitted=True)
