# ---- app/student_routes.py ----
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, session
# The 'wraps' function is crucial for decorators to preserve the original function's metadata.
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
# Import all necessary models from the application's database.
from app.models import db, Student, Payment, Registration
from app.utils.helpers import allowed_file

# Define the Blueprint for student routes.
# 'student_bp' will handle all student-related URLs.
student_bp = Blueprint('student', __name__, template_folder='../templates/student')

# --- Helper function for authentication ---
def student_required(f):
    """
    Decorator to check if a student is logged in.
    This prevents unauthorized users from accessing student-only pages.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if 'student_id' exists in the session.
        if 'student_id' not in session:
            flash("Please log in to access this page.", "warning")
            # If not logged in, redirect to the login page.
            return redirect(url_for('student.student_login'))
        # If logged in, proceed with the original function call.
        return f(*args, **kwargs)
    return decorated_function

# --- Student Authentication ---
@student_bp.route('/login', methods=['GET', 'POST'])
def student_login():
    """
    Handles student login.
    - GET request: displays the login form.
    - POST request: processes the submitted form data.
    """
    if request.method == 'POST':
        student_number = request.form['student_number']
        password = request.form['password']

        # Query the database for the student with the provided student number.
        student = Student.query.filter_by(student_number=student_number).first()

        # Check if the student exists and the password is correct using a secure hash.
        if student and check_password_hash(student.password, password):
            # Store the student's ID in the session to keep them logged in.
            session['student_id'] = student.id
            flash("Login successful!", "success")
            return redirect(url_for('student.student_dashboard'))
        else:
            flash("Invalid student number or password", "danger")

    return render_template('student/login.html')

@student_bp.route('/logout')
def student_logout():
    """Handles student logout."""
    # Remove the 'student_id' from the session to log the user out.
    session.pop('student_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('student.student_login'))

# --- Main Student Dashboard and Functionality ---
@student_bp.route('/dashboard')
@student_required
def student_dashboard():
    """
    Renders the student's dashboard, showing their payment history.
    This route now handles the functionality previously in the '/status' route.
    """
    # Get the ID of the logged-in student from the session.
    student_id = session.get('student_id')
    
    # Query for the student's payments, ordered from newest to oldest.
    payments = Payment.query.filter_by(student_id=student_id).order_by(Payment.submitted_date.desc()).all()
    
    # Pass the payments list to the template for display.
    return render_template('student/dashboard.html', payments=payments)

@student_bp.route('/upload_payment', methods=['GET', 'POST'])
def upload_payment():
    """
    Handles the payment slip upload process.
    - GET request: displays the upload form.
    - POST request: processes the file and saves it to the database.
    """
    if request.method == 'POST':
        # Get form data.
        student_number = request.form.get('student_number')
        name = request.form.get('name')
        payment_slip = request.files.get('payment_slip')

        # Basic validation for required fields.
        if not all([student_number, name, payment_slip]):
            flash('Please fill in all fields and upload a payment slip.', 'danger')
            return redirect(url_for('student.upload_payment'))

        # Check if the file is valid and allowed.
        if payment_slip and allowed_file(payment_slip.filename):
            # Sanitize the filename for security.
            filename = secure_filename(payment_slip.filename)
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure the upload directory exists before saving.
            if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
                os.makedirs(current_app.config['UPLOAD_FOLDER'])
            
            payment_slip.save(upload_path)

            # Find the student or create a new one if they don't exist.
            student = Student.query.filter_by(student_number=student_number).first()
            if not student:
                student = Student(student_number=student_number, name=name)
                db.session.add(student)
                db.session.commit()

            # Create a new payment entry in the database.
            payment = Payment(slip_filename=filename, student_id=student.id)
            db.session.add(payment)
            db.session.commit()

            flash('Payment slip uploaded successfully! It is now pending approval.', 'success')
            # Redirect to the dashboard to see the new payment's status.
            return redirect(url_for('student.student_dashboard'))
        else:
            flash('Invalid file format. Please upload an image or PDF.', 'danger')
            return redirect(url_for('student.upload_payment'))

    return render_template('student/upload_payment.html')

@student_bp.route('/delete_payment/<int:payment_id>', methods=['POST'])
@student_required
def delete_payment(payment_id):
    """
    Handles the deletion of a payment and its associated file.
    """
    payment = Payment.query.get_or_404(payment_id)

    # Check if the payment belongs to the current logged-in student.
    if payment.student_id != session.get('student_id'):
        flash("You are not authorized to delete this payment.", "danger")
        return redirect(url_for('student.student_dashboard'))
    
    # Delete the physical file from the server.
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], payment.slip_filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete the payment entry from the database.
    db.session.delete(payment)
    db.session.commit()
    flash('Payment deleted successfully!', 'success')
    return redirect(url_for('student.student_dashboard'))

# --- Placeholder Routes ---
# These routes are defined but require further implementation.
@student_bp.route('/registration_slip')
@student_required
def registration_slip():
    """Generates and serves a student's registration slip as a PDF."""
    return "Registration Slip PDF will be generated here."

@student_bp.route('/timetable')
@student_required
def timetable():
    """Generates and serves a student's timetable as a PDF."""
    return "Timetable PDF will be generated here."

# --- Serve Uploaded Files ---
@student_bp.route("/uploads/<filename>")
@student_required
def uploaded_file(filename):
    """
    Serves a specific uploaded payment slip for a logged-in student to view.
    This helps prevent unauthorized access to payment slips.
    """
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)