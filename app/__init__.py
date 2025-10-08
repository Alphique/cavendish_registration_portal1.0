# app/__init__.py
import os
from flask import Flask, render_template
from .config import Config
from .extensions import db, migrate, mail

# Import Blueprints
from .routes.student_routes import student_bp
from .routes.admin_routes import admin_bp
from .routes.chatbot.chatbot_routes import chatbot_bp
from .routes.general_routes import general as general_bp  # general blueprint

def create_app(config_class=Config):
    """Application factory pattern for Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Ensure upload folder exists ---
    upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    # --- Initialize extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # --- Register Blueprints ---
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")
    app.register_blueprint(general_bp)  # no prefix; endpoints like general.forgot_password

    # --- Default Route ---
    @app.route("/")
    def index():
        """Default homepage. Modify as needed."""
        return render_template("index.html")

    # --- Health Check Route ---
    @app.route("/ping")
    def ping():
        """Simple health check endpoint."""
        return {"status": "ok", "message": "App running fine!"}, 200

    return app
