import os
import secrets

from flask import abort, flash, redirect, render_template, request, url_for

from . import admin_bp
from .. import db
from ..auth import admin_required
from .queries import active_users

PASS_PERCENTAGE_CHOICES = [50, 60, 70, 80, 90]


def _question_sets_with_modules():
    sets_rs = db.execute("SELECT id, name FROM question_sets ORDER BY name")
    sets = []
    for set_id, set_name in sets_rs.rows:
        modules_rs = db.execute(
            """
            SELECT m.id, m.name, COUNT(q.id) AS available
            FROM exam_modules m
            JOIN questions q ON q.module_id = m.id AND q.set_id = ?
            GROUP BY m.id, m.name, m.order_index
            ORDER BY m.order_index
            """,
            [set_id],
        )
        modules = [
            {"id": mid, "name": mname, "available": available}
            for mid, mname, available in modules_rs.rows
        ]
        sets.append({"id": set_id, "name": set_name, "modules": modules})
    return sets


@admin_bp.route("/exams/new", methods=["GET", "POST"])
@admin_required
def exam_new():
    error = None
    sets = _question_sets_with_modules()
    users = active_users()
    form = request.form

    if request.method == "POST":
        exam_number = request.form.get("exam_number", "").strip()
        title = request.form.get("title", "").strip()
        set_id = request.form.get("set_id", type=int)
        passing_percentage = request.form.get("passing_percentage", type=int)
        user_ids = [int(v) for v in request.form.getlist("user_ids")]

        chosen_set = next((s for s in sets if s["id"] == set_id), None)
        module_counts = {}
        if chosen_set:
            for module in chosen_set["modules"]:
                if not request.form.get(f"module_{module['id']}"):
                    continue
                count_raw = request.form.get(f"count_{module['id']}", "").strip()
                if count_raw.isdigit() and int(count_raw) > 0:
                    module_counts[module["id"]] = min(int(count_raw), module["available"])

        if not exam_number or not title:
            error = "Exam number and title are required."
        elif not chosen_set:
            error = "Choose a question set."
        elif not module_counts:
            error = "Select at least one module and a question count for it."
        elif passing_percentage not in PASS_PERCENTAGE_CHOICES:
            error = "Choose a pass percentage."
        elif not user_ids:
            error = "Select at least one participant."
        else:
            existing = db.execute("SELECT id FROM exams WHERE exam_number = ?", [exam_number])
            if existing.rows:
                error = f'Exam number "{exam_number}" is already in use.'

        if error is None:
            rs = db.execute(
                "INSERT INTO exams (exam_number, title, set_id, start_time, end_time, "
                "passing_percentage) VALUES (?, ?, ?, datetime('now'), datetime('now', '+30 days'), ?)",
                [exam_number, title, set_id, passing_percentage],
            )
            exam_id = rs.last_insert_rowid

            for module_id, count in module_counts.items():
                db.execute(
                    "INSERT INTO exam_module_config (exam_id, module_id, question_count) "
                    "VALUES (?, ?, ?)",
                    [exam_id, module_id, count],
                )

            for user_id in user_ids:
                existing_access = db.execute(
                    "SELECT id FROM exam_access WHERE user_id = ? AND exam_id = ?",
                    [user_id, exam_id],
                )
                if not existing_access.rows:
                    token = secrets.token_urlsafe(32)
                    db.execute(
                        "INSERT INTO exam_access (user_id, exam_id, access_token) VALUES (?, ?, ?)",
                        [user_id, exam_id, token],
                    )

            flash(f"Created exam {exam_number}.")
            return redirect(url_for("admin.exam_created", exam_id=exam_id))

    return render_template(
        "admin/exam_form.html",
        error=error,
        sets=sets,
        users=users,
        pass_choices=PASS_PERCENTAGE_CHOICES,
        form=form,
    )


@admin_bp.route("/exams/<int:exam_id>/created")
@admin_required
def exam_created(exam_id):
    exam_rs = db.execute("SELECT id, exam_number, title FROM exams WHERE id = ?", [exam_id])
    if not exam_rs.rows:
        abort(404)
    exam = exam_rs.rows[0].asdict()

    links_rs = db.execute(
        """
        SELECT u.name, u.email, ea.access_token
        FROM exam_access ea
        JOIN users u ON u.id = ea.user_id
        WHERE ea.exam_id = ?
        ORDER BY u.name
        """,
        [exam_id],
    )
    base_url = os.environ.get("BASE_URL", request.host_url.rstrip("/"))
    links = [
        {"name": name, "email": email, "url": f"{base_url}/exam/{token}"}
        for name, email, token in links_rs.rows
    ]
    return render_template("admin/exam_created.html", exam=exam, links=links)
