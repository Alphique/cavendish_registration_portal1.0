# config.py
import os

class Config:
    SECRET_KEY = "super-secret-key"  # use environment variable in production
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "site.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Folder to store uploaded payment slips
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "uploads")
