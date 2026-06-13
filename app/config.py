# config.py - Place this in your project root directory

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-key-change-in-production')

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'cavendish_registration.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Folder to store uploaded payment slips
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    
    # Create uploads folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Folder to store registration slip PDFs
    REGISTRATION_SLIP_FOLDER = os.path.join(BASE_DIR, "registration_slips")
    
    # Create registration_slips folder if it doesn't exist
    if not os.path.exists(REGISTRATION_SLIP_FOLDER):
        os.makedirs(REGISTRATION_SLIP_FOLDER)

    # Email Configuration for cPanel
    MAIL_SERVER = "mail.tukakula.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    
    MAIL_USERNAME = "cavendishregistrationportal@tukakula.com"
    MAIL_PASSWORD = "Admin@Cuz"  # CHANGE THIS to your actual password
    
    # Set sender email (fixed format)
    MAIL_DEFAULT_SENDER = ("Cavendish University", "cavendishregistrationportal@tukakula.com")
    
    # Maximum file size for uploads (5MB)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

    # Base URL for the application
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    MAIL_SUPPRESS_SEND = True  # Don't send emails during tests


# Dictionary to easily switch between configurations
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}