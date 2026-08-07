import csv
import io
import os
import re
import textwrap

from flask import Response, abort, render_template, request

from . import admin_bp
from .. import db
from ..auth import admin_required
from .queries import list_exams_with_status, results_rows


@admin_bp.route("/exams")
@admin_required
def exams_list():
    return render_template("admin/exams_list.html", exams=list_exams_with_status())


@admin_bp.route("/exams/<int:exam_id>/results")
@admin_required
def exam_results(exam_id):
    exam_rs = db.execute("SELECT id, exam_number, title FROM exams WHERE id = ?", [exam_id])
    if not exam_rs.rows:
        abort(404)
    exam = exam_rs.rows[0].asdict()
    base_url = os.environ.get("BASE_URL", request.host_url.rstrip("/"))
    return render_template(
        "admin/exam_results.html", exam=exam, results=results_rows(exam_id), base_url=base_url
    )


@admin_bp.route("/exams/<int:exam_id>/export.csv")
@admin_required
def exam_export_csv(exam_id):
    exam_rs = db.execute("SELECT exam_number FROM exams WHERE id = ?", [exam_id])
    if not exam_rs.rows:
        abort(404)
    exam_number = exam_rs.rows[0][0]

    rows = results_rows(exam_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "email", "status", "score", "percentage", "result", "submitted_at"])
    for r in rows:
        writer.writerow(
            [
                r["name"],
                r["email"] or "",
                r["status"],
                r["total_score"],
                r["percentage"],
                r["result"],
                r["submitted_at"] or "",
            ]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=exam_{exam_number}_results.csv"},
    )


def _participant_breakdown(participant_id):
    """Returns (participant, attempt, breakdown) for the given exam_access id,
    or None if it doesn't exist. Shared by the detail page and its CSV export
    so both always show exactly the same data."""
    p_rs = db.execute(
        """
        SELECT ea.id, ea.exam_id, u.name, u.email
        FROM exam_access ea
        JOIN users u ON u.id = ea.user_id
        WHERE ea.id = ?
        """,
        [participant_id],
    )
    if not p_rs.rows:
        return None
    participant = p_rs.rows[0].asdict()

    a_rs = db.execute(
        "SELECT id, submitted_at, total_score FROM exam_attempts "
        "WHERE exam_access_id = ? AND attempt_number = 1",
        [participant_id],
    )
    attempt = a_rs.rows[0].asdict() if a_rs.rows else None

    breakdown = []
    if attempt:
        ans_rs = db.execute(
            """
            SELECT q.id AS question_id, q.question_text,
                   aa.selected_option_id, aa.is_correct
            FROM attempt_answers aa
            JOIN questions q ON q.id = aa.question_id
            WHERE aa.exam_attempt_id = ?
            ORDER BY q.order_index
            """,
            [attempt["id"]],
        )
        for a_row in ans_rs.rows:
            a = a_row.asdict()
            opt_rs = db.execute(
                """
                SELECT o.id, o.option_text,
                       CASE WHEN o.id = ak.correct_option_id THEN 1 ELSE 0 END AS is_correct
                FROM options o
                LEFT JOIN answer_key ak ON ak.question_id = o.question_id
                WHERE o.question_id = ?
                ORDER BY o.order_index
                """,
                [a["question_id"]],
            )
            a["options"] = [o.asdict() for o in opt_rs.rows]
            breakdown.append(a)

    return participant, attempt, breakdown


@admin_bp.route("/participant/<int:participant_id>")
@admin_required
def participant_detail(participant_id):
    result = _participant_breakdown(participant_id)
    if result is None:
        abort(404)
    participant, attempt, breakdown = result

    return render_template(
        "admin/participant_detail.html",
        participant=participant,
        attempt=attempt,
        breakdown=breakdown,
    )


def _safe_filename(text):
    """Strip characters that are awkward or invalid in a downloaded filename,
    collapsing whitespace so names/titles with odd spacing still read cleanly."""
    text = re.sub(r'[\\/:*?"<>|,]', "", text)
    return re.sub(r"\s+", " ", text).strip()


def _wrap(text):
    return textwrap.fill(text, width=60) if text else text


@admin_bp.route("/participant/<int:participant_id>/export.csv")
@admin_required
def participant_export_csv(participant_id):
    result = _participant_breakdown(participant_id)
    if result is None:
        abort(404)
    participant, _attempt, breakdown = result

    exam_rs = db.execute("SELECT title FROM exams WHERE id = ?", [participant["exam_id"]])
    exam_title = exam_rs.rows[0][0] if exam_rs.rows else ""

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Question", "Selected Option", "Correct Option", "Result"])
    for a in breakdown:
        selected = next((o for o in a["options"] if o["id"] == a["selected_option_id"]), None)
        correct = next((o for o in a["options"] if o["is_correct"]), None)
        writer.writerow(
            [
                _wrap(a["question_text"]),
                _wrap(selected["option_text"] if selected else ""),
                _wrap(correct["option_text"] if correct else ""),
                "Correct" if a["is_correct"] else "Incorrect",
            ]
        )

    filename = _safe_filename(f"{participant['name']} Results for {exam_title}") + ".csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
