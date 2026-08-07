import random

from flask import Blueprint, abort, render_template, request

from . import db
from .scoring import score_attempt

exam_bp = Blueprint("exam", __name__)


def _get_access(token):
    rs = db.execute(
        """
        SELECT ea.id AS exam_access_id, u.id AS user_id, u.name, u.email,
               e.id AS exam_id, e.title AS exam_title, e.set_id, e.questions_per_module
        FROM exam_access ea
        JOIN users u ON u.id = ea.user_id
        JOIN exams e ON e.id = ea.exam_id
        WHERE ea.access_token = ?
        """,
        [token],
    )
    if not rs.rows:
        return None
    return rs.rows[0].asdict()


def _get_or_create_attempt(exam_access_id):
    rs = db.execute(
        "SELECT id, submitted_at, total_score FROM exam_attempts WHERE exam_access_id = ? "
        "AND attempt_number = 1",
        [exam_access_id],
    )
    if rs.rows:
        return rs.rows[0].asdict()

    rs = db.execute(
        "INSERT INTO exam_attempts (exam_access_id, attempt_number) VALUES (?, 1)",
        [exam_access_id],
    )
    return {"id": rs.last_insert_rowid, "submitted_at": None, "total_score": None}


def _select_question_ids(set_id, questions_per_module):
    """The exam's fixed question list: every question in the set, or (if
    questions_per_module is set) the first N — by order_index — from each module."""
    if not questions_per_module:
        rs = db.execute("SELECT id FROM questions WHERE set_id = ?", [set_id])
        return [row[0] for row in rs.rows]

    module_rs = db.execute(
        "SELECT DISTINCT module_id FROM questions WHERE set_id = ?", [set_id]
    )
    ids = []
    for (module_id,) in module_rs.rows:
        rs = db.execute(
            "SELECT id FROM questions WHERE set_id = ? AND module_id = ? "
            "ORDER BY order_index LIMIT ?",
            [set_id, module_id, questions_per_module],
        )
        ids.extend(row[0] for row in rs.rows)
    return ids


def _load_questions(set_id, questions_per_module, seed):
    question_ids = _select_question_ids(set_id, questions_per_module)
    placeholders = ",".join("?" for _ in question_ids)
    q_rs = db.execute(
        f"SELECT id, question_text FROM questions WHERE id IN ({placeholders})",
        question_ids,
    )
    questions = [q.asdict() for q in q_rs.rows]

    for q in questions:
        opt_rs = db.execute(
            "SELECT id, option_text FROM options WHERE question_id = ? ORDER BY order_index",
            [q["id"]],
        )
        q["options"] = [o.asdict() for o in opt_rs.rows]

    rng = random.Random(seed)
    rng.shuffle(questions)
    for q in questions:
        rng.shuffle(q["options"])

    return questions


@exam_bp.route("/exam/<token>", methods=["GET"])
def show_exam(token):
    access = _get_access(token)
    if not access:
        abort(404)

    attempt = _get_or_create_attempt(access["exam_access_id"])
    if attempt["submitted_at"]:
        return render_template("already_completed.html", name=access["name"])

    questions = _load_questions(
        access["set_id"], access["questions_per_module"], seed=access["exam_access_id"]
    )
    return render_template(
        "exam.html",
        name=access["name"],
        email=access["email"],
        exam_title=access["exam_title"],
        token=token,
        questions=questions,
    )


@exam_bp.route("/exam/<token>/submit", methods=["POST"])
def submit_exam(token):
    access = _get_access(token)
    if not access:
        abort(404)

    attempt = _get_or_create_attempt(access["exam_access_id"])
    if attempt["submitted_at"]:
        return render_template("already_completed.html", name=access["name"])

    question_ids = _select_question_ids(access["set_id"], access["questions_per_module"])
    placeholders = ",".join("?" for _ in question_ids)
    q_rs = db.execute(
        f"""
        SELECT q.id, q.points, ak.correct_option_id
        FROM questions q
        JOIN answer_key ak ON ak.question_id = q.id
        WHERE q.id IN ({placeholders})
        """,
        question_ids,
    )
    questions = [q.asdict() for q in q_rs.rows]

    answers = []
    for q in questions:
        selected_raw = request.form.get(f"q_{q['id']}")
        selected_id = int(selected_raw) if selected_raw else None
        is_correct = selected_id is not None and selected_id == q["correct_option_id"]
        answers.append((is_correct, q["points"]))

        db.execute(
            "INSERT INTO attempt_answers (exam_attempt_id, question_id, selected_option_id, is_correct) "
            "VALUES (?, ?, ?, ?)",
            [attempt["id"], q["id"], selected_id, 1 if is_correct else 0],
        )

    result = score_attempt(answers)

    db.execute(
        "UPDATE exam_attempts SET submitted_at = datetime('now'), total_score = ? WHERE id = ?",
        [result["score"], attempt["id"]],
    )
    db.execute(
        "INSERT INTO exam_scores (exam_attempt_id, user_id, exam_id, attempt_number, score, "
        "max_score, percentage, passed) VALUES (?, ?, ?, 1, ?, ?, ?, ?)",
        [
            attempt["id"],
            access["user_id"],
            access["exam_id"],
            result["score"],
            result["max_score"],
            result["percentage"],
            1 if result["passed"] else 0,
        ],
    )

    return render_template("already_completed.html", name=access["name"], just_submitted=True)
