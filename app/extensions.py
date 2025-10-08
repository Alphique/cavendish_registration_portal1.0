# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail  # ✅ add Flask-Mail

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()  # ✅ initialize Mail
