# app/routes/admin_routes.py
import os
from flask import (
    Blueprint, render_template, redirect, url_for, flash, 
    send_from_directory, current_app, session, request
)
from functools import wraps
from werkzeug.security import check_password_hash
from datetime import datetime
from app.models import db, User, Student, Payment, Registration, RegistrationSlip

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')

# -----------------
# Admin Authentication Decorator
# -----------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash("Please log in as admin to access this page.", "warning")
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# -----------------
# Admin Login/Logout
# -----------------
@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, role='admin').first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['role'] = user.role
            flash("Admin login successful!", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash("Invalid credentials.", "danger")

    return render_template('admin/login.html')

@admin_bp.route('/logout')
def admin_logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('admin.admin_login'))

# -----------------
# Admin Dashboard
# -----------------
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    pending_payments = Payment.query.filter_by(status='pending').all()
    approved_payments = Payment.query.filter_by(status='approved').all()
    rejected_payments = Payment.query.filter_by(status='rejected').all()
    
    # Get all students for registration slip management
    students = Student.query.all()
    
    return render_template(
        'admin/dashboard.html',
        pending_payments=pending_payments,
        approved_payments=approved_payments,
        rejected_payments=rejected_payments,
        students=students
    )

# -----------------
# Approve/Reject Payment (UPDATED)
# -----------------
@admin_bp.route('/payment/<int:payment_id>/<action>')
@admin_required
def manage_payment(payment_id, action):
    payment = Payment.query.get_or_404(payment_id)

    if action == 'approve':
        payment.status = 'approved'
        payment.approved_date = datetime.utcnow()  # Set approval timestamp
        
        # Create registration record if it doesn't exist
        registration = Registration.query.filter_by(student_id=payment.student_id).first()
        if not registration:
            registration = Registration(student_id=payment.student_id, is_registered=True)
            db.session.add(registration)
        else:
            registration.is_registered = True
            
        db.session.commit()
        flash(f'Payment for {payment.student.name} approved and student registered.', 'success')

    elif action == 'reject':
        payment.status = 'rejected'
        db.session.commit()
        flash(f'Payment for {payment.student.name} rejected.', 'warning')
    else:
        flash("Invalid action.", "danger")

    return redirect(url_for('admin.dashboard'))

# -----------------
# Registration Slip Management (NEW)
# -----------------
@admin_bp.route('/create_registration_slip/<int:student_id>')
@admin_required
def create_registration_slip(student_id):
    """Create a registration slip for a student (admin only)."""
    student = Student.query.get_or_404(student_id)
    
    # Check if student has approved payment
    approved_payment = Payment.query.filter_by(
        student_id=student_id, 
        status='approved'
    ).first()
    
    if not approved_payment:
        flash(f'Student {student.name} does not have an approved payment.', 'warning')
        return redirect(url_for('admin.dashboard'))
    
    # Check if registration slip already exists
    existing_slip = RegistrationSlip.query.filter_by(student_id=student_id).first()
    if existing_slip:
        flash(f'Registration slip already exists for {student.name}.', 'info')
        return redirect(url_for('admin.dashboard'))
    
    # Create new registration slip
    slip_number = f"RS{student_id:06d}"
    registration_slip = RegistrationSlip(
        slip_number=slip_number,
        student_id=student_id,
        issue_date=datetime.utcnow(),
        created_by=session.get('user_id', 'admin')
    )
    
    db.session.add(registration_slip)
    db.session.commit()
    
    flash(f'Registration slip created for {student.name} (Slip #: {slip_number})', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/view_registration_slips')
@admin_required
def view_registration_slips():
    """View all registration slips."""
    registration_slips = RegistrationSlip.query.all()
    return render_template('admin/registration_slips.html', slips=registration_slips)

# -----------------
# Serve Uploaded Files
# -----------------
@admin_bp.route('/uploads/<filename>')
@admin_required
def serve_uploaded_file(filename):
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        flash('File not found.', 'danger')
        return redirect(url_for('admin.dashboard'))
    return send_from_directory(
        directory=current_app.config['UPLOAD_FOLDER'],
        path=filename,
        as_attachment=False
    )

# -----------------
# Student Management (NEW)
# -----------------
@admin_bp.route('/students')
@admin_required
def view_students():
    """View all students."""
    students = Student.query.all()
    return render_template('admin/students.html', students=students)

@admin_bp.route('/student/<int:student_id>')
@admin_required
def view_student_details(student_id):
    """View student details and history."""
    student = Student.query.get_or_404(student_id)
    payments = Payment.query.filter_by(student_id=student_id).order_by(Payment.submitted_date.desc()).all()
    registration_slip = RegistrationSlip.query.filter_by(student_id=student_id).first()
    
    return render_template(
        'admin/student_details.html',
        student=student,
        payments=payments,
        registration_slip=registration_slip
    )