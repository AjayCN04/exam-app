import os

from dotenv import load_dotenv
from flask import Flask


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ["FLASK_SECRET_KEY"]
    app.config["ADMIN_PASSWORD"] = os.environ["ADMIN_PASSWORD"]

    from .routes_admin import admin_bp
    from .routes_exam import exam_bp

    app.register_blueprint(exam_bp)
    app.register_blueprint(admin_bp)

    return app
