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

# IMPORTANT: Add this import - this was causing NameError
from app.models_academics import (
    Faculty,
    Program,
    Course,
    ProgramCourse,
    ProgramStructure,
    AcademicYear,
    StudentRegistration,      # ADDED - fixes NameError
    RegisteredCourse          # ADDED - for future use
)

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
# Payment Management (FIXED - with StudentRegistration sync)
# -----------------
# -----------------
# Payment Management (FIXED - with StudentRegistration sync)
# -----------------
@admin_bp.route('/payment/<int:payment_id>/<action>')
@admin_required
def manage_payment(payment_id, action):
    """Approve or reject payments with full registration sync and email notifications"""
    
    payment = Payment.query.get_or_404(payment_id)
    student = Student.query.get(payment.student_id)
    
    # =========================
    # APPROVE PAYMENT
    # =========================
    if action == 'approve':
        payment.status = 'approved'
        payment.approved_date = datetime.utcnow()
        
        student_id = payment.student_id
        
        # -------------------------------------------------
        # 1. FIND EXISTING REGISTRATION FOR THIS STUDENT
        # -------------------------------------------------
        registration = StudentRegistration.query.filter_by(
            student_id=student_id,
            payment_status='pending'
        ).order_by(StudentRegistration.id.desc()).first()
        
        # If no pending registration, check for any registration
        if not registration:
            registration = StudentRegistration.query.filter_by(
                student_id=student_id
            ).order_by(StudentRegistration.id.desc()).first()
        
        if registration:
            # UPDATE EXISTING REGISTRATION TO APPROVED
            registration.payment_status = 'approved'
            flash(f'Registration payment_status updated to approved for student ID {student_id}', 'info')
        else:
            # CREATE NEW REGISTRATION IF NONE EXISTS
            flash("No registration application found. Creating one automatically.", "warning")
            
            registration = StudentRegistration(
                student_id=student_id,
                program_id=payment.student.program_id if hasattr(payment.student, "program_id") else None,
                year_level=payment.student.year_of_study if hasattr(payment.student, "year_of_study") else None,
                semester_type="SEM1",
                payment_status="approved"
            )
            db.session.add(registration)
            db.session.flush()
        
        # -------------------------------------------------
        # 2. GENERATE REGISTRATION SLIP (ONLY ONCE)
        # -------------------------------------------------
        existing_slip = RegistrationSlip.query.filter_by(
            student_id=student_id
        ).first()
        
        registration_slip = None
        
        if not existing_slip:
            slip_number = f"RS{student_id:06d}-{datetime.now().strftime('%Y%m%d')}"
            
            registration_slip = RegistrationSlip(
                slip_number=slip_number,
                student_id=student_id,
                program_name=payment.student.program or "To be assigned",
                faculty_name=payment.student.faculty or "To be assigned",
                academic_year="2024/2025",
                semester="Semester 1",
                issue_date=datetime.utcnow(),
                created_by=session.get('user_id', 'admin')
            )
            
            db.session.add(registration_slip)
            db.session.flush()
            
            # Generate PDF
            from app.utils.helpers import generate_registration_slip_pdf
            success = generate_registration_slip_pdf(registration_slip)
            
            if success:
                flash(f'Payment approved & registration completed for {payment.student.name}', 'success')
            else:
                flash(f'Payment approved but slip PDF generation failed for {payment.student.name}', 'warning')
        else:
            registration_slip = existing_slip
            flash(f'Payment approved for {payment.student.name}', 'success')
        
        db.session.commit()
        
        # ==========================================
        # SEND PAYMENT APPROVAL EMAIL
        # ==========================================
        try:
            if student and student.email:
                from app.utils.email import send_payment_approval_email
                send_payment_approval_email(student, registration_slip, payment)
        except Exception as email_error:
            print(f"PAYMENT APPROVAL EMAIL ERROR: {email_error}")
    
    # =========================
    # REJECT PAYMENT
    # =========================
    elif action == 'reject':
        payment.status = 'rejected'
        payment.approved_date = datetime.utcnow()
        
        # Optionally update registration status if exists
        registration = StudentRegistration.query.filter_by(
            student_id=payment.student_id,
            payment_status='pending'
        ).order_by(StudentRegistration.id.desc()).first()
        
        if registration:
            registration.payment_status = 'rejected'
        
        db.session.commit()
        flash(f'Payment for {payment.student.name} rejected.', 'warning')
        
        # ==========================================
        # SEND PAYMENT REJECTION EMAIL
        # ==========================================
        try:
            if student and student.email:
                from app.utils.email import send_payment_rejection_email
                send_payment_rejection_email(student, payment, reason="Payment slip could not be verified. Please upload a clear copy.")
        except Exception as email_error:
            print(f"PAYMENT REJECTION EMAIL ERROR: {email_error}")
    
    else:
        flash("Invalid action.", "danger")
    
    return redirect(url_for('admin.dashboard'))

# -----------------
# Payment Preview
# -----------------
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

# -----------------view all registration slips with statistics-----------------
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

#-------------------------------------------------------------------------
# ----------------- EMAIL NOTIFICATIONS (FIXED - with proper sender format and error handling)
#-------------------------------------------------------------------------
@admin_bp.route('/edit_registration_slip/<int:slip_id>', methods=['GET', 'POST'])
@admin_required
def edit_registration_slip(slip_id):
    """Edit an existing registration slip with live academic data"""
    slip = RegistrationSlip.query.get_or_404(slip_id)
    
    # Get live academic registration data
    academic_registration = StudentRegistration.query.filter_by(
        student_id=slip.student_id
    ).order_by(StudentRegistration.id.desc()).first()
    
    # Get registered courses
    registered_courses = []
    if academic_registration:
        registered_courses = RegisteredCourse.query.filter_by(
            registration_id=academic_registration.id
        ).all()
    
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
    
    return render_template(
        'admin/edit_registration_slip.html', 
        slip=slip,
        academic_registration=academic_registration,
        registered_courses=registered_courses
    )
    
# ----------------- EMAIL NOTIFICATIONS (FIXED - with proper sender format and error handling) -----------------   
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

# ----------------- EMAIL NOTIFICATIONS (FIXED - with proper sender format and error handling) -----------------
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

# -----------------
# View Student Details (with registration & payment history)
@admin_bp.route('/student/<int:student_id>')
@admin_required
def view_student_details(student_id):

    student = Student.query.get_or_404(student_id)

    payments = Payment.query.filter_by(
        student_id=student_id
    ).order_by(
        Payment.submitted_date.desc()
    ).all()

    registration_slip = RegistrationSlip.query.filter_by(
        student_id=student_id
    ).first()

    registration = StudentRegistration.query.filter_by(
        student_id=student_id
    ).order_by(
        StudentRegistration.id.desc()
    ).first()

    program = None
    faculty = None
    academic_year = None
    registered_courses = []

    if registration:

        program = Program.query.get(
            registration.program_id
        )

        if registration.academic_year_id:
            academic_year = AcademicYear.query.get(
                registration.academic_year_id
            )

        if program and program.faculty_id:
            faculty = Faculty.query.get(
                program.faculty_id
            )

        registered_courses = (
            RegisteredCourse.query
            .filter_by(
                registration_id=registration.id
            )
            .all()
        )

    return render_template(
        'admin/student_details.html',
        student=student,
        payments=payments,
        registration_slip=registration_slip,
        registration=registration,
        program=program,
        faculty=faculty,
        academic_year=academic_year,
        registered_courses=registered_courses
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

#----
#-----------------
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
    
# -----------------
# Academic Management (Faculties, Programs, Courses)
# -----------------

@admin_bp.route('/program/create', methods=['GET', 'POST'])
@admin_required
def create_program():
    faculties = Faculty.query.all()

    if request.method == 'POST':
        name = request.form.get('name')
        short_name = request.form.get('short_name')
        duration_years = int(request.form.get('duration_years') or 0)
        total_credits = request.form.get('total_credits')
        faculty_id = request.form.get('faculty_id')

        # ---------------- VALIDATION ----------------
        if not name or duration_years <= 0:
            flash("Program name and valid duration are required.", "danger")
            return redirect(url_for('admin.create_program'))

        existing = Program.query.filter_by(name=name).first()
        if existing:
            flash("Program already exists.", "warning")
            return redirect(url_for('admin.create_program'))

        # ---------------- CREATE PROGRAM ----------------
        program = Program(
            name=name,
            short_name=short_name,
            duration_years=duration_years,
            total_credits=int(total_credits) if total_credits else None,
            faculty_id=faculty_id
        )

        db.session.add(program)
        db.session.flush()  # get program.id

        # ---------------- AUTO BUILD STRUCTURE ----------------
        semester_types = ["SEM1", "SEM2"]

        for year_level in range(1, duration_years + 1):
            for sem in semester_types:
                structure = ProgramStructure(
                    program_id=program.id,
                    year_level=year_level,
                    semester_type=sem,
                    is_active=True,
                    is_mandatory=True
                )
                db.session.add(structure)

        db.session.commit()

        flash("Program created successfully!", "success")
        return redirect(url_for('admin.program_builder', program_id=program.id))

    return render_template('admin/create_program.html', faculties=faculties)

# -----------------
# View Programs
# -----------------
@admin_bp.route('/programs')
@admin_required
def view_programs():
    programs = Program.query.all()
    return render_template('admin/view_program.html', programs=programs)

# -----------------
# Edit Program
# -----------------
@admin_bp.route('/program/edit/<int:program_id>', methods=['GET', 'POST'])
@admin_required
def edit_program(program_id):
    program = Program.query.get_or_404(program_id)
    faculties = Faculty.query.all()

    if request.method == 'POST':
        new_duration = int(request.form.get('duration_years') or 0)

        # ---------------- SAFETY CHECK ----------------
        if new_duration < program.duration_years:
            flash("You cannot reduce program duration (data integrity risk).", "danger")
            return redirect(url_for('admin.edit_program', program_id=program.id))

        program.name = request.form.get('name')
        program.short_name = request.form.get('short_name')
        program.total_credits = int(request.form.get('total_credits') or 0)
        program.faculty_id = request.form.get('faculty_id')

        # ONLY allow extension
        if new_duration > program.duration_years:
            for year in range(program.duration_years + 1, new_duration + 1):
                new_structure = ProgramStructure(
                    program_id=program.id,
                    year=year,
                    has_semester_1=True,
                    has_semester_2=True,
                    has_summer_semester=False,
                    has_industrial_attachment=False,
                    industrial_attachment_mandatory=False
                )
                db.session.add(new_structure)

            program.duration_years = new_duration

        db.session.commit()

        flash("Program updated safely!", "success")
        return redirect(url_for('admin.view_programs'))

    return render_template('admin/create_program.html', program=program, faculties=faculties)


# -----------------
# Delete Program
# -----------------
@admin_bp.route('/program/delete/<int:program_id>')
@admin_required
def delete_program(program_id):
    program = Program.query.get_or_404(program_id)

    # HARD SAFETY CHECKS
    if program.program_courses:
        flash("Cannot delete program: courses assigned.", "danger")
        return redirect(url_for('admin.view_programs'))

    if hasattr(program, "students") and program.students:
        flash("Cannot delete program: students enrolled.", "danger")
        return redirect(url_for('admin.view_programs'))

    if program.program_structures:
        for s in program.program_structures:
            db.session.delete(s)

    db.session.delete(program)
    db.session.commit()

    flash("Program deleted successfully!", "success")
    return redirect(url_for('admin.view_programs'))

# ==========================================
# PROGRAM BUILDER
# ==========================================

@admin_bp.route('/program/<int:program_id>/builder')
@admin_required
def program_builder(program_id):

    program = Program.query.get_or_404(program_id)

    curriculum = ProgramCourse.query.filter_by(
        program_id=program.id
    ).order_by(
        ProgramCourse.year_level,
        ProgramCourse.semester_type
    ).all()

    return render_template(
        'admin/program_builder.html',
        program=program,
        curriculum=curriculum
    )


# ==========================================
# ADD COURSE TO PROGRAM
# ==========================================

@admin_bp.route(
    '/program/<int:program_id>/add-course',
    methods=['POST']
)
@admin_required
def add_course_to_program(program_id):

    program = Program.query.get_or_404(program_id)

    code = request.form.get('course_code', '').strip().upper()
    title = request.form.get('course_title', '').strip()
    credits = request.form.get('credits') or 0

    year_level = int(request.form.get('year_level'))
    semester_type = request.form.get('semester_type')

    # -----------------------
    # Validation
    # -----------------------

    if not code:
        flash("Course code required.", "danger")
        return redirect(
            url_for(
                'admin.program_builder',
                program_id=program.id
            )
        )

    if not title:
        flash("Course title required.", "danger")
        return redirect(
            url_for(
                'admin.program_builder',
                program_id=program.id
            )
        )

    # -----------------------
    # Reuse Existing Course
    # -----------------------

    course = Course.query.filter_by(code=code).first()

    if course:

        # Ensure same code doesn't carry
        # a different title

        if course.title.lower() != title.lower():

            flash(
                f"Course code {code} already exists as "
                f"'{course.title}'.",
                "danger"
            )

            return redirect(
                url_for(
                    'admin.program_builder',
                    program_id=program.id
                )
            )

    else:

        course = Course(
            code=code,
            title=title,
            credits=int(credits)
        )

        db.session.add(course)
        db.session.flush()

    # -----------------------
    # Prevent duplicate assignment
    # -----------------------

    existing_assignment = ProgramCourse.query.filter_by(
        program_id=program.id,
        course_id=course.id,
        year_level=year_level,
        semester_type=semester_type
    ).first()

    if existing_assignment:

        flash(
            "Course already assigned to this semester.",
            "warning"
        )

        return redirect(
            url_for(
                'admin.program_builder',
                program_id=program.id
            )
        )

    # -----------------------
    # Assign Course
    # -----------------------

    assignment = ProgramCourse(
        program_id=program.id,
        course_id=course.id,
        year_level=year_level,
        semester_type=semester_type,
        is_mandatory=True
    )

    db.session.add(assignment)
    db.session.commit()

    flash(
        f"{code} added successfully.",
        "success"
    )

    return redirect(
        url_for(
            'admin.program_builder',
            program_id=program.id
        )
    )


# ==========================================
# REMOVE COURSE
# ==========================================

@admin_bp.route(
    '/program-course/delete/<int:id>'
)
@admin_required
def remove_program_course(id):

    assignment = ProgramCourse.query.get_or_404(id)

    program_id = assignment.program_id

    db.session.delete(assignment)
    db.session.commit()

    flash(
        "Course removed successfully.",
        "success"
    )

    return redirect(
        url_for(
            'admin.program_builder',
            program_id=program_id
        )
    )


# ==========================================
# ADMIN: VIEW ALL REGISTRATIONS
# ==========================================
@admin_bp.route('/registrations')
@admin_required
def view_registrations():
    """View all student registrations"""
    registrations = StudentRegistration.query.order_by(
        StudentRegistration.registration_date.desc()
    ).all()
    
    return render_template(
        'admin/registrations.html',
        registrations=registrations
    )


# ==========================================
# ADMIN: UPDATE REGISTRATION STATUS MANUALLY
# ==========================================
@admin_bp.route('/registration/<int:reg_id>/update-status/<status>')
@admin_required
def update_registration_status(reg_id, status):
    """Manually update registration payment status"""
    registration = StudentRegistration.query.get_or_404(reg_id)
    
    if status in ['approved', 'pending', 'rejected']:
        registration.payment_status = status
        db.session.commit()
        flash(f'Registration #{reg_id} status updated to {status}', 'success')
    else:
        flash('Invalid status', 'danger')
    
    return redirect(url_for('admin.view_registrations'))

# ==========================================
# ADMIN: DASHBOARD PREVIEW - RECENT PROGRAMS
@admin_bp.route('/recent-programs')
@admin_required
def recent_programs():
    """Get recent programs for dashboard preview"""
    programs = Program.query.order_by(Program.id.desc()).limit(5).all()
    return jsonify({
        'programs': [{
            'name': p.name,
            'duration_years': p.duration_years,
            'faculty_name': p.faculty.name if p.faculty else None,
            'created_at': p.created_at.strftime('%Y-%m-%d') if p.created_at else None
        } for p in programs]
    })