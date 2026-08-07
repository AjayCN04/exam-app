from flask import render_template

from . import admin_bp
from ..auth import admin_required


@admin_bp.route("/")
@admin_required
def home():
    return render_template("admin/home.html")
