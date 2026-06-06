import os
from flask import Flask, render_template
from flask_login import LoginManager

from .config import Config
from .extensions import db, migrate, mail

# -----------------------------
# BLUEPRINTS
# -----------------------------
from .routes.student_routes import student_bp
from .routes.admin_routes import admin_bp
from .routes.chatbot.chatbot_routes import chatbot_bp
from .routes.general_routes import general as general_bp

# -----------------------------
# MODELS (IMPORTANT FIX)
# -----------------------------
from .models import User

# 👉 THIS IS THE CRITICAL FIX (ACADEMIC MODELS)
from .models_academics import (
    Faculty,
    Program,
    Course,
    ProgramCourse,
    ProgramStructure,
    AcademicYear,
    StudentRegistration,
    RegisteredCourse
)

# -----------------------------
# LOGIN MANAGER
# -----------------------------
login_manager = LoginManager()
login_manager.login_view = "student.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -----------------------------
# APP FACTORY
# -----------------------------
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure folders exist
    upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
    registration_slip_folder = app.config.get(
        "REGISTRATION_SLIP_FOLDER",
        "registration_slips"
    )

    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(registration_slip_folder, exist_ok=True)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")
    app.register_blueprint(general_bp)

    # -----------------------------
    # DEFAULT ROUTES
    # -----------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/ping")
    def ping():
        return {
            "status": "ok",
            "message": "App running fine!"
        }, 200

    return app