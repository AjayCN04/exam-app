from flask import abort, flash, redirect, render_template, request, url_for

from . import admin_bp
from .. import db
from ..auth import admin_required
from .queries import active_users, archived_users


def _email_taken(email, exclude_id=None):
    rs = db.execute("SELECT id FROM users WHERE lower(email) = lower(?)", [email])
    return any(row[0] != exclude_id for row in rs.rows)


@admin_bp.route("/users")
@admin_required
def users_list():
    return render_template("admin/users_list.html", users=active_users(), mode="active")


@admin_bp.route("/users/archived")
@admin_required
def users_archived():
    return render_template("admin/users_list.html", users=archived_users(), mode="archived")


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def user_new():
    error = None
    form = {"name": "", "email": ""}
    if request.method == "POST":
        form["name"] = request.form.get("name", "").strip()
        form["email"] = request.form.get("email", "").strip()
        if not form["name"] or not form["email"]:
            error = "Name and email are required."
        elif _email_taken(form["email"]):
            error = "A user with this email already exists."
        else:
            db.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)", [form["name"], form["email"]]
            )
            flash(f"Added {form['name']}.")
            return redirect(url_for("admin.users_list"))
    return render_template("admin/user_form.html", user=None, form=form, error=error)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def user_edit(user_id):
    rs = db.execute("SELECT id, name, email FROM users WHERE id = ?", [user_id])
    if not rs.rows:
        abort(404)
    user = rs.rows[0].asdict()
    form = {"name": user["name"], "email": user["email"]}

    error = None
    if request.method == "POST":
        form["name"] = request.form.get("name", "").strip()
        form["email"] = request.form.get("email", "").strip()
        if not form["name"] or not form["email"]:
            error = "Name and email are required."
        elif _email_taken(form["email"], exclude_id=user_id):
            error = "A user with this email already exists."
        else:
            db.execute(
                "UPDATE users SET name = ?, email = ? WHERE id = ?",
                [form["name"], form["email"], user_id],
            )
            flash(f"Updated {form['name']}.")
            return redirect(url_for("admin.users_list"))
    return render_template("admin/user_form.html", user=user, form=form, error=error)


@admin_bp.route("/users/<int:user_id>/archive", methods=["POST"])
@admin_required
def user_archive(user_id):
    db.execute("UPDATE users SET is_active = 0 WHERE id = ?", [user_id])
    flash("User archived.")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/<int:user_id>/reactivate", methods=["POST"])
@admin_required
def user_reactivate(user_id):
    db.execute("UPDATE users SET is_active = 1 WHERE id = ?", [user_id])
    flash("User reactivated.")
    return redirect(url_for("admin.users_archived"))
