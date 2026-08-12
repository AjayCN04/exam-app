import random

from flask import Blueprint, abort, render_template, request

from . import db
from .scoring import score_attempt

exam_bp = Blueprint("exam", __name__)


def _get_access(token):
    rs = db.execute(
        """
        SELECT ea.id AS exam_access_id, u.id AS user_id, u.name, u.email,
               e.id AS exam_id, e.title AS exam_title, e.set_id,
               e.questions_per_module, e.passing_percentage, e.is_closed
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


def _select_question_ids(exam_id, set_id, questions_per_module):
    """The exam's fixed question list. Exams created via the admin UI have
    per-module counts in exam_module_config — for those, a random subset of
    each module's question pool is chosen, seeded by exam_id so the pick is
    unpredictable but identical on every call for that exam (both when the
    exam is shown and again when it's graded) and identical for every
    participant — presentation order is the pool's own order_index, kept
    stable so it doesn't vary by sampling order. Exams that predate this
    feature have no exam_module_config rows and fall back to the legacy
    behavior: every question in the set, or (if questions_per_module is set)
    the first N — by order_index — from each module, applied uniformly."""
    config_rs = db.execute(
        "SELECT module_id, question_count FROM exam_module_config WHERE exam_id = ? "
        "ORDER BY module_id",
        [exam_id],
    )
    if config_rs.rows:
        rng = random.Random(exam_id)
        ids = []
        for module_id, question_count in config_rs.rows:
            rs = db.execute(
                "SELECT id FROM questions WHERE set_id = ? AND module_id = ? "
                "ORDER BY order_index",
                [set_id, module_id],
            )
            pool = [row[0] for row in rs.rows]
            chosen = set(rng.sample(pool, min(question_count, len(pool))))
            ids.extend(qid for qid in pool if qid in chosen)
        return ids

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


def _load_questions(exam_id, set_id, questions_per_module, seed):
    question_ids = _select_question_ids(exam_id, set_id, questions_per_module)
    placeholders = ",".join("?" for _ in question_ids)
    q_rs = db.execute(
        f"SELECT id, question_text, is_multi_select FROM questions WHERE id IN ({placeholders})",
        question_ids,
    )
    # WHERE ... IN (...) doesn't guarantee row order matches question_ids —
    # rebuild in that exact order so presentation order is deterministic
    # (module order, then order_index within module) now that it's no
    # longer scrambled by a per-participant shuffle.
    by_id = {q["id"]: q for q in (row.asdict() for row in q_rs.rows)}
    questions = [by_id[qid] for qid in question_ids]

    for q in questions:
        opt_rs = db.execute(
            "SELECT id, option_text FROM options WHERE question_id = ? ORDER BY order_index",
            [q["id"]],
        )
        q["options"] = [o.asdict() for o in opt_rs.rows]

    # Question set and order are the same for every participant of this exam
    # (chosen deterministically in _select_question_ids); only each
    # question's answer-choice order is randomized per participant.
    rng = random.Random(seed)
    for q in questions:
        rng.shuffle(q["options"])

    return questions


@exam_bp.route("/exam/<token>", methods=["GET"])
def show_exam(token):
    access = _get_access(token)
    if not access:
        abort(404)
    if access["is_closed"]:
        return render_template("already_completed.html", name=access["name"], closed=True)

    attempt = _get_or_create_attempt(access["exam_access_id"])
    if attempt["submitted_at"]:
        return render_template("already_completed.html", name=access["name"])

    questions = _load_questions(
        access["exam_id"], access["set_id"], access["questions_per_module"],
        seed=access["exam_access_id"],
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
    if access["is_closed"]:
        return render_template("already_completed.html", name=access["name"], closed=True)

    attempt = _get_or_create_attempt(access["exam_access_id"])
    if attempt["submitted_at"]:
        return render_template("already_completed.html", name=access["name"])

    question_ids = _select_question_ids(
        access["exam_id"], access["set_id"], access["questions_per_module"]
    )
    placeholders = ",".join("?" for _ in question_ids)
    q_rs = db.execute(
        f"SELECT id, points, is_multi_select FROM questions WHERE id IN ({placeholders})",
        question_ids,
    )
    questions = [q.asdict() for q in q_rs.rows]

    # Authoritative correct-option set per question, from options.is_correct
    # (supports 1..N correct options; answer_key.correct_option_id is no
    # longer read here — see schema migration notes).
    opts_rs = db.execute(
        f"SELECT question_id, id AS option_id FROM options "
        f"WHERE question_id IN ({placeholders}) AND is_correct = 1",
        question_ids,
    )
    correct_ids_by_question = {}
    for row in opts_rs.rows:
        d = row.asdict()
        correct_ids_by_question.setdefault(d["question_id"], set()).add(d["option_id"])

    answers = []
    for q in questions:
        correct_ids = correct_ids_by_question.get(q["id"], set())
        if q["is_multi_select"]:
            raw_values = request.form.getlist(f"q_{q['id']}")
        else:
            single = request.form.get(f"q_{q['id']}")
            raw_values = [single] if single else []

        selected_ids = set()
        for v in raw_values:
            try:
                selected_ids.add(int(v))
            except (TypeError, ValueError):
                pass

        is_correct = bool(selected_ids) and selected_ids == correct_ids
        answers.append((is_correct, q["points"]))

        # selected_option_id (legacy scalar) is only meaningful for
        # single-select; selected_option_ids covers both, going forward.
        selected_option_id = (
            next(iter(selected_ids)) if (not q["is_multi_select"] and selected_ids) else None
        )
        selected_option_ids_text = ",".join(str(i) for i in sorted(selected_ids)) or None

        db.execute(
            "INSERT INTO attempt_answers "
            "(exam_attempt_id, question_id, selected_option_id, is_correct, selected_option_ids) "
            "VALUES (?, ?, ?, ?, ?)",
            [attempt["id"], q["id"], selected_option_id, 1 if is_correct else 0, selected_option_ids_text],
        )

    result = score_attempt(answers, passing_percentage_override=access["passing_percentage"])

    db.execute(
        "UPDATE exam_attempts SET submitted_at = datetime('now'), total_score = ? WHERE id = ?",
        [result["score"], attempt["id"]],
    )
    db.execute(
        "INSERT INTO exam_scores (exam_attempt_id, user_id, exam_id, attempt_number, score, "
        "max_score, percentage, passed, user_name, exam_name) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)",
        [
            attempt["id"],
            access["user_id"],
            access["exam_id"],
            result["score"],
            result["max_score"],
            result["percentage"],
            1 if result["passed"] else 0,
            access["name"],
            access["exam_title"],
        ],
    )

    return render_template("already_completed.html", name=access["name"], just_submitted=True)
