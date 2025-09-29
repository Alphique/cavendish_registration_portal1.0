import datetime
from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------
# USER MODEL (login)
# --------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="student")  # "student" or "admin"

    # Optional: link user to a student profile (only if role=student)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=True)

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
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

    # Relationships
    payments = db.relationship("Payment", backref="student", lazy=True)
    registration = db.relationship("Registration", uselist=False, backref="student", lazy=True)

    # Backref to user login (if linked)
    user = db.relationship("User", backref="student_profile", uselist=False)

    def __repr__(self):
        return f"<Student {self.student_number} - {self.name}>"

# --------------------
# PAYMENT MODEL
# --------------------
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slip_filename = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Pending, Approved, Rejected
    submitted_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)

    def __repr__(self):
        return f"<Payment {self.id} - {self.status}>"

# --------------------
# REGISTRATION MODEL
# --------------------
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    semester = db.Column(db.String(50), default="Current Semester")
    registration_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_registered = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), unique=True, nullable=False)

    def __repr__(self):
        return f"<Registration {self.student_id} - {self.semester}>"
