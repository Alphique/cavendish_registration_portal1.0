# ---- app/routes/student_routes.py ----
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, session
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import db, Student, Payment, User  # Ensure User is imported
from app.utils.helpers import allowed_file

# Blueprint definition
student_bp = Blueprint('student', __name__, template_folder='../templates/student')

# ---------------- Helper Decorator ----------------
def student_required(f):
    """
    Decorator to ensure student is logged in before accessing a route.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'student_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('student.student_login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- Student Authentication ----------------
@student_bp.route('/login', methods=['GET', 'POST'])
def student_login():
    """
    Handles student login.
    """
    if request.method == 'POST':
        student_number = request.form.get('student_number')
        password = request.form.get('password')

        # Find User by username and role
        user = User.query.filter_by(username=student_number, role='student').first()
        if user and user.check_password(password):
            # Store student_id in session
            session['student_id'] = user.student_id
            flash("Login successful!", "success")
            return redirect(url_for('student.student_dashboard'))
        else:
            flash("Invalid student number or password", "danger")

    return render_template('student/login.html')

@student_bp.route('/logout')
def student_logout():
    """Logs out the student."""
    session.pop('student_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('student.student_login'))

# ---------------- Dashboard ----------------
@student_bp.route('/dashboard')
@student_required
def student_dashboard():
    """
    Shows student dashboard and payment history.
    """
    student_id = session.get('student_id')
    payments = Payment.query.filter_by(student_id=student_id).order_by(Payment.submitted_date.desc()).all()
    return render_template('student/dashboard.html', payments=payments)

# ---------------- Payment Upload ----------------
@student_bp.route('/upload_payment', methods=['GET', 'POST'])
@student_required
def upload_payment():
    """
    Handles payment slip upload.
    """
    if request.method == 'POST':
        student_number = request.form.get('student_number')
        name = request.form.get('name')
        payment_slip = request.files.get('payment_slip')

        if not all([student_number, name, payment_slip]):
            flash('Please fill in all fields and upload a payment slip.', 'danger')
            return redirect(url_for('student.upload_payment'))

        if payment_slip and allowed_file(payment_slip.filename):
            filename = secure_filename(payment_slip.filename)
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

            if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
                os.makedirs(current_app.config['UPLOAD_FOLDER'])

            payment_slip.save(upload_path)

            # Ensure student exists
            student = Student.query.filter_by(student_number=student_number).first()
            if not student:
                student = Student(student_number=student_number, name=name)
                db.session.add(student)
                db.session.commit()

            # Add payment record
            payment = Payment(slip_filename=filename, student_id=student.id)
            db.session.add(payment)
            db.session.commit()

            flash('Payment slip uploaded successfully! It is now pending approval.', 'success')
            return redirect(url_for('student.student_dashboard'))
        else:
            flash('Invalid file format. Please upload an image or PDF.', 'danger')
            return redirect(url_for('student.upload_payment'))

    return render_template('student/upload_payment.html')

@student_bp.route('/delete_payment/<int:payment_id>', methods=['POST'])
@student_required
def delete_payment(payment_id):
    """
    Delete a payment record and its associated file.
    """
    payment = Payment.query.get_or_404(payment_id)

    if payment.student_id != session.get('student_id'):
        flash("You are not authorized to delete this payment.", "danger")
        return redirect(url_for('student.student_dashboard'))

    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], payment.slip_filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(payment)
    db.session.commit()
    flash('Payment deleted successfully!', 'success')
    return redirect(url_for('student.student_dashboard'))

# ---------------- Placeholder Routes ----------------
@student_bp.route('/registration_slip')
@student_required
def registration_slip():
    """Generates registration slip PDF (placeholder)."""
    return "Registration Slip PDF will be generated here."

@student_bp.route('/timetable')
@student_required
def timetable():
    """Generates timetable PDF (placeholder)."""
    return "Timetable PDF will be generated here."

# ---------------- Student Registration ----------------
@student_bp.route('/register', methods=['GET', 'POST'])
def student_register():
    """
    Student registration linked to a Student profile.
    """
    if request.method == 'POST':
        student_number = request.form.get('student_number')
        name = request.form.get('name')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([student_number, name, password, confirm_password]):
            flash("All fields are required.", "danger")
            return redirect(url_for('student.student_register'))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('student.student_register'))

        # Ensure Student profile exists
        student = Student.query.filter_by(student_number=student_number).first()
        if not student:
            student = Student(student_number=student_number, name=name)
            db.session.add(student)
            db.session.commit()

        # Check if User already exists
        user = User.query.filter_by(student_id=student.id, role='student').first()
        if user:
            flash("This student ID is already registered.", "danger")
            return redirect(url_for('student.student_register'))

        # Create User
        user = User(
            username=student_number,
            email=f"{student_number}@cavendish.ac.zm",
            role="student",
            student_id=student.id
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("✅ Registration successful! You can now log in.", "success")
        return redirect(url_for('student.student_login'))

    return render_template('student/register.html')

# ---------------- Serve Uploaded Files ----------------
@student_bp.route("/uploads/<filename>")
@student_required
def uploaded_file(filename):
    """
    Serves uploaded payment slips securely.
    """
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
