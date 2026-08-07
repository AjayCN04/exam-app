import hmac

from flask import current_app, redirect, render_template, request, session, url_for

from . import admin_bp


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if hmac.compare_digest(password, current_app.config["ADMIN_PASSWORD"]):
            session["is_admin"] = True
            return redirect(url_for("admin.home"))
        error = "Incorrect password"
    return render_template("admin/login.html", error=error)


@admin_bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin.login"))
