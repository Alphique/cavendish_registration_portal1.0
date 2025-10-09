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
# Payment Management
# -----------------
@admin_bp.route('/payment/<int:payment_id>/<action>')
@admin_required
def manage_payment(payment_id, action):
    """Approve or reject payments with auto-registration slip creation"""
    payment = Payment.query.get_or_404(payment_id)

    if action == 'approve':
        payment.status = 'approved'
        payment.approved_date = datetime.utcnow()
        
        # Create registration record
        registration = Registration.query.filter_by(student_id=payment.student_id).first()
        if not registration:
            registration = Registration(student_id=payment.student_id, is_registered=True)
            db.session.add(registration)
        else:
            registration.is_registered = True
        
        # AUTO-CREATE REGISTRATION SLIP
        existing_slip = RegistrationSlip.query.filter_by(student_id=payment.student_id).first()
        if not existing_slip:
            slip_number = f"RS{payment.student_id:06d}-{datetime.now().strftime('%Y%m%d')}"
            registration_slip = RegistrationSlip(
                slip_number=slip_number,
                student_id=payment.student_id,
                program_name=payment.student.program or "To be assigned",
                faculty_name=payment.student.faculty or "To be assigned",
                academic_year="2024/2025",
                semester="Semester 1",
                issue_date=datetime.utcnow(),
                created_by=session.get('user_id', 'admin')
            )
            db.session.add(registration_slip)
            db.session.commit()
            
            # Generate PDF
            from app.utils.helpers import generate_registration_slip_pdf
            if generate_registration_slip_pdf(registration_slip):
                db.session.commit()
                flash(f'Payment approved and registration slip created for {payment.student.name}!', 'success')
            else:
                flash(f'Payment approved but PDF generation failed for {payment.student.name}.', 'warning')
        else:
            # Slip already exists, just approve payment
            db.session.commit()
            flash(f'Payment for {payment.student.name} approved.', 'success')

    elif action == 'reject':
        payment.status = 'rejected'
        db.session.commit()
        flash(f'Payment for {payment.student.name} rejected.', 'warning')
    else:
        flash("Invalid action.", "danger")

    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/payment/<int:payment_id>/preview')
@admin_required
def preview_payment(payment_id):
    """Preview payment details before approval."""
    payment = Payment.query.get_or_404(payment_id)
    return render_template('admin/payment_preview.html', payment=payment)

# -----------------
# Registration Slip Management
# -----------------
@admin_bp.route('/create_registration_slip_form', methods=['GET', 'POST'])
@admin_required
def create_registration_slip_form():
    """Handle the complex registration form (manual creation)"""
    if request.method == 'POST':
        try:
            student_number = request.form.get('student_number')
            
            # Find student
            student = Student.query.filter_by(student_number=student_number).first()
            if not student:
                flash('Student not found!', 'danger')
                return redirect(url_for('admin.create_registration_slip_form'))
            
            # Check if slip already exists
            existing_slip = RegistrationSlip.query.filter_by(student_id=student.id).first()
            if existing_slip:
                flash(f'Registration slip already exists for {student.name}.', 'info')
                return redirect(url_for('admin.view_registration_slips'))
            
            # Create registration slip with form data
            slip_number = f"RS{student.id:06d}-{datetime.now().strftime('%Y%m%d')}"
            registration_slip = RegistrationSlip(
                slip_number=slip_number,
                student_id=student.id,
                program_name=request.form.get('program_name'),
                faculty_name=request.form.get('faculty_name', student.faculty),
                academic_year="2024/2025",
                semester="Semester 1",
                issue_date=datetime.utcnow(),
                created_by=session.get('user_id', 'admin')
            )
            
            db.session.add(registration_slip)
            db.session.commit()
            
            # Generate PDF
            from app.utils.helpers import generate_registration_slip_pdf
            if generate_registration_slip_pdf(registration_slip):
                db.session.commit()
                flash(f'Registration slip created for {student.name}!', 'success')
            else:
                flash(f'Registration slip created but PDF generation failed for {student.name}.', 'warning')
                
            return redirect(url_for('admin.view_registration_slips'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating registration slip: {str(e)}', 'danger')
            return redirect(url_for('admin.create_registration_slip_form'))
    
    return render_template('admin/registration_slip.html')

@admin_bp.route('/view_registration_slips')
@admin_required
def view_registration_slips():
    """View all registration slips with statistics"""
    registration_slips = RegistrationSlip.query.order_by(RegistrationSlip.issue_date.desc()).all()
    
    # Calculate statistics
    today = datetime.utcnow().date()
    today_count = len([slip for slip in registration_slips if slip.issue_date.date() == today])
    
    return render_template('admin/view_registration_slips.html', 
                         slips=registration_slips,
                         today_count=today_count)

@admin_bp.route('/edit_registration_slip/<int:slip_id>', methods=['GET', 'POST'])
@admin_required
def edit_registration_slip(slip_id):
    """Edit an existing registration slip"""
    slip = RegistrationSlip.query.get_or_404(slip_id)
    
    if request.method == 'POST':
        try:
            # Update slip information
            slip.program_name = request.form.get('program_name', slip.program_name)
            slip.faculty_name = request.form.get('faculty_name', slip.faculty_name)
            slip.academic_year = request.form.get('academic_year', slip.academic_year)
            slip.semester = request.form.get('semester', slip.semester)
            
            # Regenerate PDF with updated information
            from app.utils.helpers import generate_registration_slip_pdf
            if generate_registration_slip_pdf(slip):
                db.session.commit()
                flash('Registration slip updated successfully!', 'success')
            else:
                flash('Slip updated but PDF regeneration failed.', 'warning')
                
            return redirect(url_for('admin.view_registration_slips'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating registration slip: {str(e)}', 'danger')
    
    return render_template('admin/edit_registration_slip.html', slip=slip)

@admin_bp.route('/regenerate_slip_pdf/<int:slip_id>')
@admin_required
def regenerate_slip_pdf(slip_id):
    """Regenerate PDF for a registration slip"""
    slip = RegistrationSlip.query.get_or_404(slip_id)
    
    try:
        from app.utils.helpers import generate_registration_slip_pdf
        if generate_registration_slip_pdf(slip):
            db.session.commit()
            flash('PDF regenerated successfully!', 'success')
        else:
            flash('PDF regeneration failed.', 'warning')
    except Exception as e:
        flash(f'Error regenerating PDF: {str(e)}', 'danger')
    
    return redirect(url_for('admin.view_registration_slips'))

@admin_bp.route('/delete_registration_slip/<int:slip_id>')
@admin_required
def delete_registration_slip(slip_id):
    """Delete a registration slip"""
    slip = RegistrationSlip.query.get_or_404(slip_id)
    student_name = slip.student.name
    
    try:
        # Delete PDF file if it exists
        if slip.pdf_filename:
            pdf_path = os.path.join(current_app.config['REGISTRATION_SLIP_FOLDER'], slip.pdf_filename)
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        
        db.session.delete(slip)
        db.session.commit()
        flash(f'Registration slip for {student_name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting registration slip: {str(e)}', 'danger')
    
    return redirect(url_for('admin.view_registration_slips'))

@admin_bp.route('/registration_slips/<filename>')
@admin_required
def serve_registration_slip(filename):
    """Serve registration slip PDF files"""
    return send_from_directory(
        current_app.config['REGISTRATION_SLIP_FOLDER'],
        filename,
        as_attachment=False
    )

# -----------------
# Student Management
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

# -----------------
# Admin Management
# -----------------
@admin_bp.route('/create_admin', methods=['GET', 'POST'])
@admin_required
def create_admin():
    """Create a new admin account."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validation
        if not all([username, email, password, confirm_password]):
            flash("All fields are required.", "danger")
            return redirect(url_for('admin.create_admin'))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('admin.create_admin'))

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for('admin.create_admin'))

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for('admin.create_admin'))

        # Create admin user
        admin_user = User(
            username=username,
            email=email,
            role='admin'
        )
        admin_user.set_password(password)
        
        db.session.add(admin_user)
        db.session.commit()

        flash(f"Admin account for {username} created successfully!", "success")
        return redirect(url_for('admin.manage_admins'))

    return render_template('admin/create_admin.html')

@admin_bp.route('/manage_admins')
@admin_required
def manage_admins():
    """View and manage all admin accounts."""
    admins = User.query.filter_by(role='admin').all()
    return render_template('admin/manage_admins.html', admins=admins)

@admin_bp.route('/reset_admin_password/<int:admin_id>', methods=['GET', 'POST'])
@admin_required
def reset_admin_password(admin_id):
    """Reset password for an admin account."""
    admin_user = User.query.filter_by(id=admin_id, role='admin').first_or_404()
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password:
            flash("New password is required.", "danger")
            return redirect(url_for('admin.reset_admin_password', admin_id=admin_id))

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('admin.reset_admin_password', admin_id=admin_id))

        # Update password
        admin_user.set_password(new_password)
        db.session.commit()

        flash(f"Password for {admin_user.username} has been reset successfully!", "success")
        return redirect(url_for('admin.manage_admins'))

    return render_template('admin/reset_admin_password.html', admin_user=admin_user)

@admin_bp.route('/delete_admin/<int:admin_id>')
@admin_required
def delete_admin(admin_id):
    """Delete an admin account (cannot delete yourself)."""
    if admin_id == session.get('user_id'):
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for('admin.manage_admins'))

    admin_user = User.query.filter_by(id=admin_id, role='admin').first_or_404()
    username = admin_user.username
    
    db.session.delete(admin_user)
    db.session.commit()

    flash(f"Admin account for {username} has been deleted.", "success")
    return redirect(url_for('admin.manage_admins'))

# -----------------
# File Serving
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