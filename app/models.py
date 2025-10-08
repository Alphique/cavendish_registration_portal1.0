# app/models.py
import datetime
from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------
# USER MODEL (login)
# --------------------
class User(db.Model, UserMixin):
    __tablename__ = "user"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="student")  # "student" or "admin"

    # Optional: link user to a student profile (only if role=student)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=True)

    # Password reset fields
    reset_token = db.Column(db.String(128), unique=True, nullable=True, index=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    # Relationships
    student_profile = db.relationship("Student", back_populates="user", uselist=False)

    # Password methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"

# --------------------
# STUDENT MODEL
# --------------------
class Student(db.Model):
    __tablename__ = "student"
    
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="student_profile", uselist=False)
    payments = db.relationship("Payment", backref="student", lazy=True)
    registration = db.relationship("Registration", uselist=False, backref="student", lazy=True)

    def __repr__(self):
        return f"<Student {self.student_number} - {self.name}>"

# --------------------
# PAYMENT MODEL
# --------------------
class Payment(db.Model):
    __tablename__ = "payment"
    
    id = db.Column(db.Integer, primary_key=True)
    slip_filename = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Pending, Approved, Rejected
    submitted_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)

    def __repr__(self):
        return f"<Payment {self.id} - {self.status}>"

# --------------------
# CHATBOT MESSAGE MODEL
# --------------------
class ChatbotMessage(db.Model):
    __tablename__ = "chatbot_message"
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), unique=True, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<ChatbotMessage {self.id}>"

# --------------------
# REGISTRATION MODEL
# --------------------
class Registration(db.Model):
    __tablename__ = "registration"
    
    id = db.Column(db.Integer, primary_key=True)
    semester = db.Column(db.String(50), default="Current Semester")
    registration_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_registered = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), unique=True, nullable=False)

    def __repr__(self):
        return f"<Registration {self.student_id} - {self.semester}>"
