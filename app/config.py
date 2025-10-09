import os

class Config:
    SECRET_KEY = "super-secret-key"  # TODO: Use env var in production

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "cavendish_registration.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Folder to store uploaded payment slips
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    
    # NEW: Folder to store registration slip PDFs
    REGISTRATION_SLIP_FOLDER = os.path.join(BASE_DIR, "registration_slips")