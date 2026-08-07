import csv
import hmac
import io

from flask import Blueprint, Response, abort, current_app, redirect, render_template, request, session, url_for

from . import db
from .auth import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if hmac.compare_digest(password, current_app.config["ADMIN_PASSWORD"]):
            session["is_admin"] = True
            return redirect(url_for("admin.dashboard"))
        error = "Incorrect password"
    return render_template("admin_login.html", error=error)


@admin_bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin.login"))


def _results_rows():
    rs = db.execute(
        """
        SELECT ea.id, u.name, u.email, eat.started_at, eat.submitted_at, eat.total_score
        FROM exam_access ea
        JOIN users u ON u.id = ea.user_id
        LEFT JOIN exam_attempts eat ON eat.exam_access_id = ea.id AND eat.attempt_number = 1
        ORDER BY u.name
        """
    )
    rows = []
    for row in rs.rows:
        r = row.asdict()
        if r["submitted_at"]:
            r["status"] = "completed"
        elif r["started_at"]:
            r["status"] = "in_progress"
        else:
            r["status"] = "not_started"
        rows.append(r)
    return rows


@admin_bp.route("/")
@admin_required
def dashboard():
    return render_template("admin_dashboard.html", results=_results_rows())


@admin_bp.route("/participant/<int:participant_id>")
@admin_required
def participant_detail(participant_id):
    p_rs = db.execute(
        """
        SELECT ea.id, u.name, u.email
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
        "admin_detail.html", participant=participant, attempt=attempt, breakdown=breakdown
    )


@admin_bp.route("/export.csv")
@admin_required
def export_csv():
    rows = _results_rows()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "email", "status", "score", "submitted_at"])
    for r in rows:
        writer.writerow(
            [r["name"], r["email"] or "", r["status"], r["total_score"], r["submitted_at"] or ""]
        )
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=exam_results.csv"},
    )
