import csv
import io

from flask import Response, abort, render_template

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
    return render_template("admin/exam_results.html", exam=exam, results=results_rows(exam_id))


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
    writer.writerow(["name", "email", "status", "score", "result", "submitted_at"])
    for r in rows:
        writer.writerow(
            [r["name"], r["email"] or "", r["status"], r["total_score"], r["result"], r["submitted_at"] or ""]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=exam_{exam_number}_results.csv"},
    )


@admin_bp.route("/participant/<int:participant_id>")
@admin_required
def participant_detail(participant_id):
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
        abort(404)
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

    return render_template(
        "admin/participant_detail.html",
        participant=participant,
        attempt=attempt,
        breakdown=breakdown,
    )
