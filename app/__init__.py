# app/__init__.py
import os
from flask import Flask, render_template
from flask_login import LoginManager, current_user
from .config import Config
from .extensions import db, migrate, mail

# Import Blueprints
from .routes.student_routes import student_bp
from .routes.admin_routes import admin_bp
from .routes.chatbot.chatbot_routes import chatbot_bp
from .routes.general_routes import general as general_bp  # general blueprint

# Import User model for login_manager
from .models import User

# Initialize LoginManager
login_manager = LoginManager()
login_manager.login_view = "student.login"  # redirect if user not logged in
login_manager.login_message_category = "info"

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    """Given a user ID, return the associated User object."""
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    """Application factory pattern for Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Ensure ALL required folders exist ---
    upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
    registration_slip_folder = app.config.get("REGISTRATION_SLIP_FOLDER", "registration_slips")
    
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(registration_slip_folder, exist_ok=True)

    # --- Initialize extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login_manager.init_app(app)

    # --- Register Blueprints ---
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")
    app.register_blueprint(general_bp)  # no prefix; endpoints like general.forgot_password

    # --- Default Route ---
    @app.route("/")
    def index():
        """Default homepage."""
        return render_template("index.html")

    # --- Health Check Route ---
    @app.route("/ping")
    def ping():
        """Simple health check endpoint."""
        return {"status": "ok", "message": "App running fine!"}, 200

    return app