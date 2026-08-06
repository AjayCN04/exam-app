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
        SELECT p.id, p.name, p.email, a.started_at, a.submitted_at, a.total_score
        FROM participants p
        LEFT JOIN attempts a ON a.participant_id = p.id
        ORDER BY p.name
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
    p_rs = db.execute("SELECT id, name, email FROM participants WHERE id = ?", [participant_id])
    if not p_rs.rows:
        abort(404)
    participant = p_rs.rows[0].asdict()

    a_rs = db.execute(
        "SELECT id, submitted_at, total_score FROM attempts WHERE participant_id = ?",
        [participant_id],
    )
    attempt = a_rs.rows[0].asdict() if a_rs.rows else None

    breakdown = []
    if attempt:
        ans_rs = db.execute(
            """
            SELECT q.id AS question_id, q.question_text,
                   ans.selected_option_id, ans.is_correct
            FROM answers ans
            JOIN questions q ON q.id = ans.question_id
            WHERE ans.attempt_id = ?
            ORDER BY q.order_index
            """,
            [attempt["id"]],
        )
        for a_row in ans_rs.rows:
            a = a_row.asdict()
            opt_rs = db.execute(
                "SELECT id, option_text, is_correct FROM options WHERE question_id = ? ORDER BY order_index",
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
