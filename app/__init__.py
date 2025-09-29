from flask import Flask, render_template  # <-- added render_template
from .config import Config
from .extensions import db, migrate
from .routes.student_routes import student_bp
from .routes.admin_routes import admin_bp
import os


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload folder exists
    upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")  # fallback to 'uploads'
    os.makedirs(upload_folder, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Default route
    @app.route("/")
    def index():
        return render_template("index.html")

    return app
