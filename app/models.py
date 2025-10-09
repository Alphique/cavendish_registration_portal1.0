# app/models.py
from datetime import datetime, timezone
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

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    student_profile = db.relationship("Student", back_populates="user", uselist=False, foreign_keys=[student_id])

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
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    program = db.Column(db.String(50), nullable=True)
    faculty = db.Column(db.String(100), nullable=True)  # NEW: Added faculty field
    intake_year = db.Column(db.Integer, nullable=True)
    year_of_study = db.Column(db.Integer, nullable=True)
    semester = db.Column(db.String(20), nullable=True)  # NEW: Added semester field
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="student_profile", uselist=False, foreign_keys=[User.student_id])
    payments = db.relationship("Payment", back_populates="student", lazy=True, cascade="all, delete-orphan")
    registrations = db.relationship("Registration", back_populates="student", lazy=True, cascade="all, delete-orphan")
    registration_slips = db.relationship("RegistrationSlip", back_populates="student", lazy=True, cascade="all, delete-orphan")

    @property
    def registration_slip(self):
        """Convenience property to get the latest registration slip"""
        return self.registration_slips[0] if self.registration_slips else None

    def __repr__(self):
        return f"<Student {self.student_number} - {self.name}>"

# --------------------
# PAYMENT MODEL (UPDATED)
# --------------------
class Payment(db.Model):
    __tablename__ = "payment"
    
    id = db.Column(db.Integer, primary_key=True)
    slip_filename = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending, approved, rejected
    description = db.Column(db.Text, nullable=True)
    submitted_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    approved_date = db.Column(db.DateTime, nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    
    # Payment details (for registration slip)
    amount = db.Column(db.Float, nullable=True)
    method = db.Column(db.String(50), nullable=True)
    reference = db.Column(db.String(100), nullable=True, unique=True)  # Made unique
    receipt_image = db.Column(db.String(255), nullable=True)  # NEW: Store receipt image filename

    # Relationships
    student = db.relationship("Student", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id} - {self.status} - {self.reference}>"

# --------------------
# REGISTRATION SLIP MODEL (UPDATED)
# --------------------
class RegistrationSlip(db.Model):
    __tablename__ = "registration_slip"
    
    id = db.Column(db.Integer, primary_key=True)
    slip_number = db.Column(db.String(50), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    issue_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    pdf_filename = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.String(100), nullable=True)
    created_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Additional fields for slip content
    academic_year = db.Column(db.String(20), nullable=True)
    semester = db.Column(db.String(20), nullable=True)
    program_name = db.Column(db.String(100), nullable=True)
    faculty_name = db.Column(db.String(100), nullable=True)

    # Relationships
    student = db.relationship("Student", back_populates="registration_slips")

    def __repr__(self):
        return f"<RegistrationSlip {self.slip_number} - {self.student.name}>"

# --------------------
# CHATBOT MESSAGE MODEL
# --------------------
class ChatbotMessage(db.Model):
    __tablename__ = "chatbot_message"
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='unknown')
    is_known_response = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<ChatbotMessage {self.question}>'

# --------------------
# REGISTRATION MODEL (UPDATED)
# --------------------
class Registration(db.Model):
    __tablename__ = "registration"
    
    id = db.Column(db.Integer, primary_key=True)
    semester = db.Column(db.String(50), default="Current Semester")
    academic_year = db.Column(db.String(20), nullable=True)  # NEW: Added academic year
    registration_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_registered = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)

    # Relationships
    student = db.relationship("Student", back_populates="registrations")

    def __repr__(self):
        return f"<Registration {self.student_id} - {self.semester}>"

# --------------------
# SYSTEM LOG MODEL (NEW - for admin activity tracking)
# --------------------
class SystemLog(db.Model):
    __tablename__ = "system_log"
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    admin = db.relationship("User")

    def __repr__(self):
        return f"<SystemLog {self.action} - {self.created_at}>"