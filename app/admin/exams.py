import os
import secrets

from flask import abort, flash, redirect, render_template, request, url_for
from werkzeug.datastructures import MultiDict

from . import admin_bp
from .. import db
from ..auth import admin_required
from .queries import active_users, exam_has_attempts

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
                if not request.form.get(f"module_{set_id}_{module['id']}"):
                    continue
                count_raw = request.form.get(f"count_{set_id}_{module['id']}", "").strip()
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
        exam=None,
        content_locked=False,
        granted={},
        pinned=[],
        locked_modules=[],
        current_set_name="",
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


@admin_bp.route("/exams/<int:exam_id>/edit", methods=["GET", "POST"])
@admin_required
def exam_edit(exam_id):
    exam_rs = db.execute(
        "SELECT id, exam_number, title, set_id, passing_percentage FROM exams WHERE id = ?",
        [exam_id],
    )
    if not exam_rs.rows:
        abort(404)
    exam = exam_rs.rows[0].asdict()

    content_locked = exam_has_attempts(exam_id)
    sets = _question_sets_with_modules()
    users = active_users()

    module_counts_by_id = {
        mid: cnt
        for mid, cnt in db.execute(
            "SELECT module_id, question_count FROM exam_module_config WHERE exam_id = ?",
            [exam_id],
        ).rows
    }
    locked_modules = [
        {"name": name, "count": count}
        for name, count in db.execute(
            """
            SELECT m.name, emc.question_count
            FROM exam_module_config emc
            JOIN exam_modules m ON m.id = emc.module_id
            WHERE emc.exam_id = ?
            ORDER BY m.order_index
            """,
            [exam_id],
        ).rows
    ]
    current_set_name = next((s["name"] for s in sets if s["id"] == exam["set_id"]), "")

    granted = {
        user_id: {"name": name, "email": email, "started": bool(started)}
        for user_id, name, email, started in db.execute(
            """
            SELECT ea.user_id, u.name, u.email,
                   EXISTS(SELECT 1 FROM exam_attempts WHERE exam_access_id = ea.id) AS started
            FROM exam_access ea
            JOIN users u ON u.id = ea.user_id
            WHERE ea.exam_id = ?
            ORDER BY u.name
            """,
            [exam_id],
        ).rows
    }

    error = None

    if request.method == "POST":
        exam_number = request.form.get("exam_number", "").strip()
        title = request.form.get("title", "").strip()
        passing_percentage = request.form.get("passing_percentage", type=int)
        checked_user_ids = {int(v) for v in request.form.getlist("user_ids")}
        # Already-started participants are pinned via hidden inputs in the
        # template, but guard here too so a started participant's access can
        # never be silently dropped even if the form is tampered with.
        for user_id, info in granted.items():
            if info["started"]:
                checked_user_ids.add(user_id)

        chosen_set = None
        module_counts = module_counts_by_id
        if not content_locked:
            set_id = request.form.get("set_id", type=int)
            chosen_set = next((s for s in sets if s["id"] == set_id), None)
            module_counts = {}
            if chosen_set:
                for module in chosen_set["modules"]:
                    if not request.form.get(f"module_{set_id}_{module['id']}"):
                        continue
                    count_raw = request.form.get(f"count_{set_id}_{module['id']}", "").strip()
                    if count_raw.isdigit() and int(count_raw) > 0:
                        module_counts[module["id"]] = min(int(count_raw), module["available"])

        if not exam_number or not title:
            error = "Exam number and title are required."
        elif not content_locked and not chosen_set:
            error = "Choose a question set."
        elif not content_locked and not module_counts:
            error = "Select at least one module and a question count for it."
        elif passing_percentage not in PASS_PERCENTAGE_CHOICES:
            error = "Choose a pass percentage."
        elif not checked_user_ids:
            error = "Select at least one participant."
        else:
            dup = db.execute(
                "SELECT id FROM exams WHERE exam_number = ? AND id != ?", [exam_number, exam_id]
            )
            if dup.rows:
                error = f'Exam number "{exam_number}" is already in use.'

        if error is None:
            db.execute(
                "UPDATE exams SET exam_number = ?, title = ?, passing_percentage = ? WHERE id = ?",
                [exam_number, title, passing_percentage, exam_id],
            )

            if not content_locked:
                db.execute("UPDATE exams SET set_id = ? WHERE id = ?", [chosen_set["id"], exam_id])
                db.execute("DELETE FROM exam_module_config WHERE exam_id = ?", [exam_id])
                for module_id, count in module_counts.items():
                    db.execute(
                        "INSERT INTO exam_module_config (exam_id, module_id, question_count) "
                        "VALUES (?, ?, ?)",
                        [exam_id, module_id, count],
                    )

            for user_id in checked_user_ids:
                if user_id not in granted:
                    token = secrets.token_urlsafe(32)
                    db.execute(
                        "INSERT INTO exam_access (user_id, exam_id, access_token) VALUES (?, ?, ?)",
                        [user_id, exam_id, token],
                    )

            # Only ever remove a participant who was actually a checkbox on
            # this form (an active user) — a granted participant who was
            # archived in Manage Users since being invited has no checkbox
            # here to control, so leave their access untouched rather than
            # silently dropping it just because it's absent from the post.
            removable_candidates = {u["id"] for u in users}
            for user_id, info in granted.items():
                if (
                    user_id in removable_candidates
                    and user_id not in checked_user_ids
                    and not info["started"]
                ):
                    db.execute(
                        "DELETE FROM exam_access WHERE exam_id = ? AND user_id = ?",
                        [exam_id, user_id],
                    )

            flash(f"Updated exam {exam_number}.")
            return redirect(url_for("admin.exams_list"))

    if request.method == "POST":
        form_data = request.form
    else:
        pairs = [
            ("exam_number", exam["exam_number"]),
            ("title", exam["title"]),
            ("set_id", str(exam["set_id"])),
            (
                "passing_percentage",
                str(int(exam["passing_percentage"])) if exam["passing_percentage"] is not None else "",
            ),
        ]
        for mid, cnt in module_counts_by_id.items():
            pairs.append((f"module_{exam['set_id']}_{mid}", "on"))
            pairs.append((f"count_{exam['set_id']}_{mid}", str(cnt)))
        for user_id in granted:
            pairs.append(("user_ids", str(user_id)))
        form_data = MultiDict(pairs)

    return render_template(
        "admin/exam_form.html",
        error=error,
        sets=sets,
        users=users,
        pass_choices=PASS_PERCENTAGE_CHOICES,
        form=form_data,
        exam=exam,
        content_locked=content_locked,
        granted=granted,
        pinned=[(uid, info) for uid, info in granted.items() if info["started"]],
        locked_modules=locked_modules,
        current_set_name=current_set_name,
    )


@admin_bp.route("/exams/<int:exam_id>/close", methods=["POST"])
@admin_required
def exam_close(exam_id):
    db.execute("UPDATE exams SET is_closed = 1 WHERE id = ?", [exam_id])
    flash("Exam closed.")
    return redirect(url_for("admin.exams_list"))


@admin_bp.route("/exams/<int:exam_id>/reopen", methods=["POST"])
@admin_required
def exam_reopen(exam_id):
    db.execute("UPDATE exams SET is_closed = 0 WHERE id = ?", [exam_id])
    flash("Exam reopened.")
    return redirect(url_for("admin.exams_list"))


@admin_bp.route("/exams/<int:exam_id>/archive", methods=["POST"])
@admin_required
def exam_archive(exam_id):
    db.execute("UPDATE exams SET is_active = 0 WHERE id = ?", [exam_id])
    flash("Exam archived.")
    return redirect(url_for("admin.exams_list"))


@admin_bp.route("/exams/<int:exam_id>/reactivate", methods=["POST"])
@admin_required
def exam_reactivate(exam_id):
    db.execute("UPDATE exams SET is_active = 1 WHERE id = ?", [exam_id])
    flash("Exam reactivated.")
    return redirect(url_for("admin.exams_archived"))
