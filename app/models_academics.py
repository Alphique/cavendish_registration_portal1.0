#app/models_academics.py
from datetime import datetime, timezone
from .extensions import db

# =========================================================
# FACULTY
# =========================================================
class Faculty(db.Model):
    __tablename__ = "faculty"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    programs = db.relationship(
        "Program",
        back_populates="faculty"
    )

    def __repr__(self):
        return f"<Faculty {self.name}>"


# =========================================================
# ACADEMIC YEAR
# =========================================================
class AcademicYear(db.Model):
    __tablename__ = "academic_year"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to StudentRegistration
    registrations = db.relationship(
        "StudentRegistration",
        back_populates="academic_year",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<AcademicYear {self.name}>"


# =========================================================
# PROGRAM
# =========================================================
class Program(db.Model):
    __tablename__ = "program"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False)
    short_name = db.Column(db.String(50))

    duration_years = db.Column(db.Integer, nullable=False)
    total_credits = db.Column(db.Integer)

    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"))

    faculty = db.relationship("Faculty", back_populates="programs")

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    structures = db.relationship("ProgramStructure", back_populates="program")
    courses = db.relationship("ProgramCourse", back_populates="program")
    
    # Relationship to StudentRegistration
    registrations = db.relationship(
        "StudentRegistration",
        back_populates="program",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Program {self.name}>"


# =========================================================
# COURSE
# =========================================================
class Course(db.Model):
    __tablename__ = "course"

    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)

    credits = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to RegisteredCourse
    registered_courses = db.relationship(
        "RegisteredCourse",
        back_populates="course",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Course {self.code}>"


# =========================================================
# PROGRAM STRUCTURE
# =========================================================
class ProgramStructure(db.Model):
    __tablename__ = "program_structure"

    id = db.Column(db.Integer, primary_key=True)

    program_id = db.Column(
        db.Integer,
        db.ForeignKey("program.id"),
        nullable=False,
        index=True
    )

    year_level = db.Column(db.Integer, nullable=False, index=True)

    semester_type = db.Column(db.String(20), nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    is_mandatory = db.Column(db.Boolean, default=True)

    program = db.relationship(
        "Program",
        back_populates="structures"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "program_id",
            "year_level",
            "semester_type",
            name="uq_program_year_semester"
        ),
    )

    def __repr__(self):
        return f"<ProgramStructure Program={self.program_id} Year={self.year_level} Semester={self.semester_type}>"


# =========================================================
# PROGRAM COURSE
# =========================================================
class ProgramCourse(db.Model):
    __tablename__ = "program_course"

    id = db.Column(db.Integer, primary_key=True)

    program_id = db.Column(db.Integer, db.ForeignKey("program.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)

    year_level = db.Column(db.Integer, nullable=False)

    semester_type = db.Column(db.String(50), nullable=False)

    is_mandatory = db.Column(db.Boolean, default=True)

    program = db.relationship(
        "Program",
        back_populates="courses",
        lazy="joined"
    )
    
    course = db.relationship(
        "Course",
        lazy="joined"
    )

    def __repr__(self):
        return f"<ProgramCourse {self.program_id}-{self.course_id}>"


# =========================================================
# STUDENT REGISTRATION (FIXED - NO CONFLICT WITH Student.registrations)
# =========================================================
class StudentRegistration(db.Model):
    __tablename__ = "student_registration"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id"),
        nullable=False
    )

    program_id = db.Column(
        db.Integer,
        db.ForeignKey("program.id"),
        nullable=False
    )

    academic_year_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_year.id")
    )

    year_level = db.Column(db.Integer, nullable=False)

    semester_type = db.Column(
        db.String(50),
        nullable=False
    )

    registration_date = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    payment_status = db.Column(
        db.String(20),
        default="pending"
    )

    # =========================================================
    # RELATIONSHIPS (FIXED)
    # =========================================================
    
    # Student relationship - uses backref with different name to avoid conflict
    student = db.relationship(
        "Student",
        backref="academic_registrations",  # Different name = no conflict
        lazy=True
    )

    # Program relationship
    program = db.relationship(
        "Program",
        back_populates="registrations"
    )

    # Academic Year relationship
    academic_year = db.relationship(
        "AcademicYear",
        back_populates="registrations"
    )

    # Registered courses relationship
    courses = db.relationship(
        "RegisteredCourse",
        back_populates="registration",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def __repr__(self):
        return (
            f"<StudentRegistration "
            f"S{self.student_id} "
            f"Y{self.year_level}>"
        )


# =========================================================
# REGISTERED COURSES
# =========================================================
class RegisteredCourse(db.Model):
    __tablename__ = "registered_course"

    id = db.Column(db.Integer, primary_key=True)

    registration_id = db.Column(
        db.Integer,
        db.ForeignKey("student_registration.id"),
        nullable=False
    )

    course_id = db.Column(
        db.Integer,
        db.ForeignKey("course.id"),
        nullable=False
    )

    registration = db.relationship(
        "StudentRegistration",
        back_populates="courses"
    )

    course = db.relationship(
        "Course",
        back_populates="registered_courses"
    )

    def __repr__(self):
        return (
            f"<RegisteredCourse "
            f"R{self.registration_id} "
            f"C{self.course_id}>"
        )