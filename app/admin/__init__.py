from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

from . import login, home, users, exams, results  # noqa: E402,F401
