# ---- app/routes/student_routes.py ----
import os
import io
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, 
    current_app, send_from_directory, session, make_response, send_file, jsonify
)
from functools import wraps
from werkzeug.utils import secure_filename
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from app.models import db, Student, Payment, User, RegistrationSlip
from app.models_academics import ProgramStructure, Program, ProgramCourse, StudentRegistration, RegisteredCourse, Course
from app.utils.helpers import allowed_file

# Blueprint definition
student_bp = Blueprint('student', __name__)

# ---------------- Helper Decorator ----------------
def student_required(f):
    """Decorator to ensure student is logged in before accessing a route."""
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
    if request.method == 'POST':
        student_number = request.form.get('student_number')
        password = request.form.get('password')

        user = User.query.filter_by(
            username=student_number,
            role='student'
        ).first()

        if not user:
            flash("Account not found", "danger")
            return render_template('student/login.html')

        if not user.check_password(password):
            flash("Wrong password", "danger")
            return render_template('student/login.html')

        # 🔥 IMPORTANT: verify student exists
        student = Student.query.get(user.student_id)
        if not student:
            flash("Student profile missing. Contact admin.", "danger")
            return render_template('student/login.html')

        session['student_id'] = student.id
        flash("Login successful!", "success")
        return redirect(url_for('student.student_dashboard'))

    return render_template('student/login.html')

@student_bp.route('/logout')
def student_logout():
    session.pop('student_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('student.student_login'))

# ---------------- Dashboard ----------------
@student_bp.route('/dashboard')
@student_required
def student_dashboard():
    student_id = session.get('student_id')
    student = Student.query.get(student_id)
    payments = Payment.query.filter_by(student_id=student_id).order_by(Payment.submitted_date.desc()).all()
    
    # Check for approved payment and registration slip
    approved_payment = Payment.query.filter_by(
        student_id=student_id, 
        status='approved'
    ).first()
    
    # Check if registration slip exists for this student
    registration_slip = RegistrationSlip.query.filter_by(
        student_id=student_id
    ).first()
    
    return render_template('student/dashboard.html', 
                         payments=payments, 
                         student=student,
                         approved_payment=approved_payment,
                         registration_slip=registration_slip)

# ---------------- Payment Upload (Traditional - keeps existing functionality) ----------------
@student_bp.route('/upload_payment', methods=['GET', 'POST'])
@student_required
def upload_payment():
    if request.method == 'POST':
        student_id = session.get('student_id')
        student = Student.query.get(student_id)
        
        if not student:
            flash('Student not found.', 'danger')
            return redirect(url_for('student.student_dashboard'))
            
        payment_slip = request.files.get('payment_slip')

        if not payment_slip:
            flash('Please upload a payment slip.', 'danger')
            return redirect(url_for('student.upload_payment'))

        if payment_slip and allowed_file(payment_slip.filename):
            filename = secure_filename(payment_slip.filename)
            # Add timestamp to make filename unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

            if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
                os.makedirs(current_app.config['UPLOAD_FOLDER'])

            payment_slip.save(upload_path)

            payment = Payment(
                slip_filename=filename, 
                student_id=student_id,
                status='pending',
                submitted_date=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.commit()

            flash('Payment slip uploaded successfully! It is now pending approval.', 'success')
            return redirect(url_for('student.student_dashboard'))
        else:
            flash('Invalid file format. Please upload an image or PDF.', 'danger')
            return redirect(url_for('student.upload_payment'))

    return render_template('student/upload_payment.html')

# ---------------- AJAX Payment Upload (For dashboard unified form) ----------------
@student_bp.route('/upload_payment_ajax', methods=['POST'])
@student_required
def upload_payment_ajax():
    """AJAX endpoint for payment upload from dashboard unified form"""
    try:
        student_id = session.get('student_id')
        student = Student.query.get(student_id)
        
        if not student:
            return jsonify({'success': False, 'error': 'Student not found.'}), 404
            
        payment_slip = request.files.get('payment_slip')

        if not payment_slip:
            return jsonify({'success': False, 'error': 'Please upload a payment slip.'}), 400

        if payment_slip and allowed_file(payment_slip.filename):
            filename = secure_filename(payment_slip.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

            if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
                os.makedirs(current_app.config['UPLOAD_FOLDER'])

            payment_slip.save(upload_path)

            payment = Payment(
                slip_filename=filename, 
                student_id=student_id,
                status='pending',
                submitted_date=datetime.utcnow()
            )
            db.session.add(payment)
            db.session.commit()

            return jsonify({
                'success': True, 
                'message': 'Payment slip uploaded successfully!',
                'payment_id': payment.id
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid file format. Please upload an image or PDF.'}), 400
            
    except Exception as e:
        print("UPLOAD PAYMENT AJAX ERROR:", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@student_bp.route('/delete_payment/<int:payment_id>', methods=['POST'])
@student_required
def delete_payment(payment_id):
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

# ---------------- Registration Slip Routes (UPDATED - LIVE DATA) ----------------
@student_bp.route('/registration_slip')
@student_required
def view_registration_slip():
    """Display registration slip for the logged-in student (VIEW ONLY)."""
    student_id = session.get('student_id')
    student = Student.query.get_or_404(student_id)
    
    # Get the latest academic registration for this student
    academic_registration = StudentRegistration.query.filter_by(
        student_id=student_id
    ).order_by(StudentRegistration.id.desc()).first()
    
    # Get the latest approved payment
    approved_payment = Payment.query.filter_by(
        student_id=student_id, 
        status='approved'
    ).order_by(Payment.submitted_date.desc()).first()
    
    # Get registered courses
    registered_courses = []
    if academic_registration:
        registered_courses = RegisteredCourse.query.filter_by(
            registration_id=academic_registration.id
        ).all()
    
    return render_template(
        'student/registration_slip.html',
        student=student,
        academic_registration=academic_registration,
        payment=approved_payment,
        registered_courses=registered_courses
    )


@student_bp.route('/registration_slip/download')
@student_required
def download_registration_slip():
    """Generate and download registration slip PDF with LIVE data from database"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.lib.units import inch, mm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import os
    
    student_id = session.get('student_id')
    student = Student.query.get_or_404(student_id)
    
    # Get the latest academic registration for this student
    academic_registration = StudentRegistration.query.filter_by(
        student_id=student_id
    ).order_by(StudentRegistration.id.desc()).first()
    
    # Get the latest approved payment
    approved_payment = Payment.query.filter_by(
        student_id=student_id, 
        status='approved'
    ).order_by(Payment.submitted_date.desc()).first()
    
    # Get registered courses
    registered_courses = []
    program_name = "N/A"
    faculty_name = "N/A"
    year_level = "N/A"
    semester_type = "N/A"
    academic_year = "N/A"
    
    if academic_registration:
        registered_courses = RegisteredCourse.query.filter_by(
            registration_id=academic_registration.id
        ).all()
        
        # Get program details
        if academic_registration.program:
            program_name = academic_registration.program.name or "N/A"
            if academic_registration.program.faculty:
                faculty_name = academic_registration.program.faculty.name or "N/A"
        
        year_level = f"Year {academic_registration.year_level}" if academic_registration.year_level else "N/A"
        
        # Map semester type to display name
        semester_map = {
            'SEM1': 'Semester 1',
            'SEM2': 'Semester 2',
            'SUMMER': 'Summer Semester',
            'INDUSTRIAL': 'Industrial Attachment'
        }
        semester_type = semester_map.get(academic_registration.semester_type, academic_registration.semester_type or "N/A")
        
        # Get academic year
        if academic_registration.academic_year:
            academic_year = academic_registration.academic_year.name or "N/A"
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=0.5*inch, 
        bottomMargin=0.5*inch,
        leftMargin=0.7*inch,
        rightMargin=0.7*inch
    )
    
    # Create styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        spaceAfter=5,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1e3c72'),
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#666666'),
        spaceAfter=15
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=10,
        textColor=colors.HexColor('#1e3c72'),
        fontName='Helvetica-Bold'
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#555555'),
        fontName='Helvetica-Bold'
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#333333')
    )
    
    # Build story
    story = []
    
    # =========================================================
    # HEADER WITH LOGO
    # =========================================================
    try:
        # Get the logo path
        logo_path = os.path.join(current_app.root_path, 'static', 'images', 'logo3.png')
        
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=1.2*inch, height=1.2*inch)
            
            # Create header table with logo on left, university name center, and space on right
            header_data = [
                [logo, Paragraph("CAVENDISH UNIVERSITY<br/><font size='8' color='#666666'>Lusaka, Zambia</font>", title_style), ""]
            ]
            
            header_table = Table(header_data, colWidths=[1.2*inch, 4*inch, 1*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('LEFTPADDING', (0, 0), (0, 0), 0),
                ('RIGHTPADDING', (2, 0), (2, 0), 0),
            ]))
            story.append(header_table)
        else:
            # Fallback if logo not found
            story.append(Paragraph("CAVENDISH UNIVERSITY", title_style))
            story.append(Paragraph("Lusaka, Zambia", subtitle_style))
    except Exception as e:
        print(f"Logo loading error: {e}")
        story.append(Paragraph("CAVENDISH UNIVERSITY", title_style))
        story.append(Paragraph("Lusaka, Zambia", subtitle_style))
    
    story.append(Spacer(1, 5))
    
    # Document Title
    story.append(Paragraph("OFFICIAL REGISTRATION SLIP", title_style))
    story.append(Spacer(1, 15))
    
    # =========================================================
    # REGISTRATION INFO BOX
    # =========================================================
    reg_info = [
        [Paragraph("<b>Registration Number:</b>", label_style), 
         Paragraph(f"REG-{student.id:06d}-{datetime.now().year}", value_style)],
        [Paragraph("<b>Issue Date:</b>", label_style), 
         Paragraph(datetime.now().strftime('%d %B, %Y'), value_style)],
        [Paragraph("<b>Registration Status:</b>", label_style), 
         Paragraph("<font color='green'><b>APPROVED</b></font>" if approved_payment else "<font color='orange'><b>PENDING</b></font>", value_style)],
    ]
    
    reg_table = Table(reg_info, colWidths=[2*inch, 3.5*inch])
    reg_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(reg_table)
    story.append(Spacer(1, 10))
    
    # =========================================================
    # STUDENT INFORMATION SECTION
    # =========================================================
    story.append(Paragraph("STUDENT INFORMATION", section_header_style))
    story.append(Spacer(1, 3))
    
    student_data = [
        ["Full Name:", student.name or "N/A"],
        ["Student ID:", student.student_number or "N/A"],
        ["Email:", student.email or "N/A"],
        ["Phone:", student.phone or "N/A"],
    ]
    
    student_table_data = []
    for label, value in student_data:
        student_table_data.append([
            Paragraph(f"<b>{label}</b>", label_style), 
            Paragraph(str(value), value_style)
        ])
    
    student_table = Table(student_table_data, colWidths=[1.2*inch, 4.5*inch])
    student_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 10))
    
    # =========================================================
    # ACADEMIC INFORMATION SECTION
    # =========================================================
    story.append(Paragraph("ACADEMIC INFORMATION", section_header_style))
    story.append(Spacer(1, 3))
    
    academic_data = [
        ["Program of Study:", program_name],
        ["Faculty/School:", faculty_name],
        ["Year of Study:", year_level],
        ["Semester:", semester_type],
        ["Academic Year:", academic_year],
    ]
    
    academic_table_data = []
    for label, value in academic_data:
        academic_table_data.append([
            Paragraph(f"<b>{label}</b>", label_style), 
            Paragraph(str(value), value_style)
        ])
    
    academic_table = Table(academic_table_data, colWidths=[1.2*inch, 4.5*inch])
    academic_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(academic_table)
    story.append(Spacer(1, 10))
    
    # =========================================================
    # PAYMENT INFORMATION SECTION
    # =========================================================
    story.append(Paragraph("PAYMENT INFORMATION", section_header_style))
    story.append(Spacer(1, 3))
    
    payment_data = [
        ["Payment Status:", "Paid" if approved_payment else "Pending Approval"],
        ["Amount Paid:", f"ZMW {approved_payment.amount:,.2f}" if approved_payment and approved_payment.amount else "N/A"],
        ["Reference Number:", approved_payment.reference or "N/A" if approved_payment else "N/A"],
        ["Payment Method:", approved_payment.method or "N/A" if approved_payment else "N/A"],
        ["Approved Date:", approved_payment.approved_date.strftime('%d %B, %Y') if approved_payment and approved_payment.approved_date else "N/A"],
    ]
    
    payment_table_data = []
    for label, value in payment_data:
        payment_table_data.append([
            Paragraph(f"<b>{label}</b>", label_style), 
            Paragraph(str(value), value_style)
        ])
    
    payment_table = Table(payment_table_data, colWidths=[1.2*inch, 4.5*inch])
    payment_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(payment_table)
    story.append(Spacer(1, 10))
    
    # =========================================================
    # REGISTERED COURSES SECTION - THIS IS THE KEY PART
    # =========================================================
    if registered_courses:
        story.append(Paragraph("REGISTERED COURSES", section_header_style))
        story.append(Spacer(1, 5))
        
        # Course table header
        course_data = [
            ['S/N', 'Course Code', 'Course Title', 'Credits']
        ]
        
        total_credits = 0
        for idx, rc in enumerate(registered_courses, 1):
            if rc.course:
                course_data.append([
                    str(idx),
                    rc.course.code or "N/A",
                    rc.course.title or "N/A",
                    str(rc.course.credits or 0)
                ])
                total_credits += (rc.course.credits or 0)
        
        # Add total row
        course_data.append(['', '', 'TOTAL CREDITS:', str(total_credits)])
        
        course_table = Table(course_data, colWidths=[0.5*inch, 1.2*inch, 3.5*inch, 0.8*inch])
        course_table.setStyle(TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3c72')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows styling
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('ALIGN', (0, 1), (0, -2), 'CENTER'),
            ('ALIGN', (3, 1), (3, -2), 'CENTER'),
            
            # Grid lines
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#cccccc')),
            
            # Total row styling
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8e8e8')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('SPAN', (0, -1), (1, -1)),
            ('ALIGN', (2, -1), (2, -1), 'RIGHT'),
            ('ALIGN', (3, -1), (3, -1), 'CENTER'),
            ('TOPPADDING', (0, -1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
            
            # Cell padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(course_table)
        story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("REGISTERED COURSES", section_header_style))
        story.append(Spacer(1, 5))
        story.append(Paragraph("<i>No registered courses found for this student.</i>", styles['Italic']))
        story.append(Spacer(1, 10))
    
    # =========================================================
    # FOOTER NOTES
    # =========================================================
    story.append(Spacer(1, 15))
    story.append(Paragraph("IMPORTANT NOTES", section_header_style))
    
    notes = [
        "1. This registration slip is valid for the current academic session.",
        "2. The student must present this slip when required by university authorities.",
        "3. Any changes to registered courses must be approved by the academic office.",
        "4. This is a computer-generated document and requires no signature.",
    ]
    
    for note in notes:
        story.append(Paragraph(note, styles['Normal']))
        story.append(Spacer(1, 3))
    
    # Footer with page number
    story.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#999999')
    )
    story.append(Paragraph("© Cavendish University - Official Registration Document", footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Create response
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Registration_Slip_{student.student_number}.pdf'
    
    return response

# ---------------- Timetable Download ----------------
@student_bp.route('/download_timetable')
@student_required
def download_timetable():
    """Generate and download timetable PDF with LIVE course data"""
    student_id = session.get('student_id')
    student = Student.query.get(student_id)
    
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for('student.student_dashboard'))
    
    # Get the latest academic registration
    academic_registration = StudentRegistration.query.filter_by(
        student_id=student_id
    ).order_by(StudentRegistration.id.desc()).first()
    
    # Get registered courses for timetable
    registered_courses = []
    program_name = "N/A"
    semester_type = "N/A"
    academic_year = "N/A"
    
    if academic_registration:
        registered_courses = RegisteredCourse.query.filter_by(
            registration_id=academic_registration.id
        ).all()
        
        # Get program details
        if academic_registration.program:
            program_name = academic_registration.program.name or "N/A"
        
        # Map semester type
        semester_map = {
            'SEM1': 'FIRST SEMESTER',
            'SEM2': 'SECOND SEMESTER',
            'SUMMER': 'SUMMER SEMESTER',
            'INDUSTRIAL': 'INDUSTRIAL ATTACHMENT'
        }
        semester_type = semester_map.get(academic_registration.semester_type, "N/A")
        
        # Get academic year
        if academic_registration.academic_year:
            academic_year = academic_registration.academic_year.name or "N/A"
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=1*inch)
    
    # Create styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor('#1e3c72')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor('#2a5298')
    )
    
    # Build story
    story = []
    
    # University Header
    story.append(Paragraph("CAVENDISH UNIVERSITY", title_style))
    story.append(Paragraph("Lusaka, Zambia", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Document Title
    story.append(Paragraph("STUDENT TIMETABLE", title_style))
    story.append(Spacer(1, 30))
    
    # Student Information - LIVE DATA
    story.append(Paragraph("STUDENT INFORMATION", heading_style))
    
    student_data = [
        ["Student Name:", student.name or "N/A"],
        ["Student ID:", student.student_number or "N/A"],
        ["Program:", program_name],
        ["Academic Year:", academic_year],
        ["Semester:", semester_type],
        ["Date Generated:", datetime.now().strftime('%d-%m-%Y')]
    ]
    
    normal_style = styles['Normal']
    table_data = []
    for label, value in student_data:
        table_data.append([Paragraph(f"<b>{label}</b>", normal_style), Paragraph(value, normal_style)])
    
    student_table = Table(table_data, colWidths=[2*inch, 3*inch])
    student_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(student_table)
    story.append(Spacer(1, 30))
    
    # Timetable Data - LIVE from registered courses
    story.append(Paragraph("CLASS SCHEDULE", heading_style))
    
    if registered_courses:
        # Build timetable from registered courses
        timetable_data = [
            ['#', 'Course Code', 'Course Name', 'Credits']
        ]
        
        for idx, rc in enumerate(registered_courses, 1):
            if rc.course:
                timetable_data.append([
                    str(idx),
                    rc.course.code or "N/A",
                    rc.course.title or "N/A",
                    str(rc.course.credits or 0)
                ])
        
        # Add total credits row
        total_credits = sum(rc.course.credits or 0 for rc in registered_courses if rc.course)
        timetable_data.append(['', '', 'TOTAL CREDITS:', str(total_credits)])
        
        timetable_table = Table(timetable_data, colWidths=[0.5*inch, 1.2*inch, 3.5*inch, 1*inch])
        timetable_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3c72')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('GRID', (0, 0), (-1, -2), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('SPAN', (0, -1), (1, -1)),
            ('ALIGN', (3, -1), (3, -1), 'RIGHT'),
        ]))
        story.append(timetable_table)
    else:
        story.append(Paragraph("<i>No registered courses found. Please complete registration.</i>", styles['Italic']))
    
    story.append(Spacer(1, 30))
    
    # Important Notes
    story.append(Paragraph("IMPORTANT NOTES", heading_style))
    notes = [
        "1. This timetable is subject to changes. Please check regularly for updates.",
        "2. Students are expected to be punctual for all classes.",
        "3. Any timetable conflicts should be reported to the academic office immediately.",
        "4. Laboratory sessions will be scheduled separately.",
    ]
    
    for note in notes:
        story.append(Paragraph(note, normal_style))
        story.append(Spacer(1, 5))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    # Create response
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=timetable_{student.student_number}.pdf'
    
    return response

# ---------------- Student Registration ----------------
@student_bp.route('/register', methods=['GET', 'POST'])
def student_register():
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

        student = Student.query.filter_by(student_number=student_number).first()
        if not student:
            student = Student(student_number=student_number, name=name)
            db.session.add(student)
            db.session.commit()

        user = User.query.filter_by(student_id=student.id, role='student').first()
        if user:
            flash("This student ID is already registered.", "danger")
            return redirect(url_for('student.student_register'))

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
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)

# =========================================================
# API ENDPOINTS FOR REGISTRATION & DASHBOARD
# =========================================================

# ---------------- GET ALL PROGRAMS ----------------
@student_bp.route("/get-programs")
@student_required
def get_programs():
    try:
        programs = Program.query.all()
        return jsonify({
            "programs": [
                {
                    "id": p.id,
                    "name": p.name
                }
                for p in programs
            ]
        })
    except Exception as e:
        print("GET PROGRAMS ERROR:", e)
        return jsonify({"programs": []}), 500

# ---------------- GET SEMESTERS BASED ON PROGRAM + YEAR ----------------
@student_bp.route("/get-semesters/<int:program_id>/<int:year_level>")
@student_required
def get_semesters(program_id, year_level):
    try:
        semesters = ProgramStructure.query.filter_by(
            program_id=program_id,
            year_level=year_level,
            is_active=True
        ).all()
        
        # Map semester types to display names
        semester_map = {
            'SEM1': 'Semester 1',
            'SEM2': 'Semester 2',
            'SUMMER': 'Summer Semester',
            'INDUSTRIAL': 'Industrial Attachment'
        }
        
        semester_list = []
        for s in semesters:
            if s.semester_type and s.semester_type in semester_map:
                semester_list.append(semester_map[s.semester_type])
            elif s.semester_type:
                semester_list.append(s.semester_type)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_semesters = []
        for sem in semester_list:
            if sem not in seen:
                seen.add(sem)
                unique_semesters.append(sem)
        
        return jsonify({"semesters": unique_semesters})
    except Exception as e:
        print("GET SEMESTERS ERROR:", e)
        return jsonify({"semesters": []}), 500

# ---------------- GET AVAILABLE COURSES FOR REGISTRATION ----------------
@student_bp.route("/get-available-courses", methods=['GET'])
@student_required
def get_available_courses():
    """Get available courses for registration application (before approval)"""
    try:
        program_id = request.args.get('program_id', type=int)
        year = request.args.get('year', type=int)
        semester = request.args.get('semester')
        
        if not all([program_id, year, semester]):
            return jsonify({'courses': [], 'error': 'Missing parameters'}), 400
        
        # Map semester display name back to semester_type
        semester_reverse_map = {
            'Semester 1': 'SEM1',
            'Semester 2': 'SEM2',
            'Summer Semester': 'SUMMER',
            'Industrial Attachment': 'INDUSTRIAL'
        }
        semester_type = semester_reverse_map.get(semester, 'SEM1')
        
        program_courses = ProgramCourse.query.filter_by(
            program_id=program_id,
            year_level=year,
            semester_type=semester_type,
            is_mandatory=True
        ).all()
        
        courses = []
        for pc in program_courses:
            if pc.course:
                courses.append({
                    'id': pc.course.id,
                    'code': pc.course.code,
                    'name': pc.course.title,
                    'credits': pc.course.credits or 0
                })
        
        return jsonify({'courses': courses})
    except Exception as e:
        print("GET AVAILABLE COURSES ERROR:", e)
        return jsonify({'courses': [], 'error': str(e)}), 500

# ---------------- GET APPROVED COURSES FOR DASHBOARD ----------------
@student_bp.route("/get-approved-courses", methods=['GET'])
@student_required
def get_approved_courses():
    """Get approved/registered courses for dashboard view"""
    try:
        student_id = session.get('student_id')
        program_id = request.args.get('program_id', type=int)
        year = request.args.get('year', type=int)
        semester = request.args.get('semester')
        
        if not all([program_id, year, semester]):
            return jsonify({'courses': [], 'error': 'Missing parameters'}), 400
        
        # Map semester display name to semester_type
        semester_reverse_map = {
            'Semester 1': 'SEM1',
            'Semester 2': 'SEM2',
            'Summer Semester': 'SUMMER',
            'Industrial Attachment': 'INDUSTRIAL'
        }
        semester_type = semester_reverse_map.get(semester, 'SEM1')
        
        # Find approved registration
        registration = StudentRegistration.query.filter_by(
            student_id=student_id,
            program_id=program_id,
            year_level=year,
            semester_type=semester_type,
            payment_status='approved'
        ).first()
        
        if not registration:
            return jsonify({'courses': []})
        
        registered_courses = RegisteredCourse.query.filter_by(
            registration_id=registration.id
        ).all()
        
        courses = []
        for rc in registered_courses:
            if rc.course:
                courses.append({
                    'id': rc.course.id,
                    'code': rc.course.code,
                    'name': rc.course.title,
                    'credits': rc.course.credits or 0,
                    'approved': True
                })
        
        return jsonify({'courses': courses})
    except Exception as e:
        print("GET APPROVED COURSES ERROR:", e)
        return jsonify({'courses': [], 'error': str(e)}), 500

# ---------------- SUBMIT REGISTRATION APPLICATION ----------------
@student_bp.route('/submit-registration', methods=['POST'])
@student_required
def submit_registration():
    """Submit registration application for admin approval"""
    try:
        student_id = session.get('student_id')
        data = request.get_json()
        
        program_id = data.get('program_id')
        year_level = data.get('year_level')
        semester_type_display = data.get('semester_type')
        course_ids = data.get('courses', [])
        
        if not all([program_id, year_level, semester_type_display]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Map semester display name to semester_type
        semester_reverse_map = {
            'Semester 1': 'SEM1',
            'Semester 2': 'SEM2',
            'Summer Semester': 'SUMMER',
            'Industrial Attachment': 'INDUSTRIAL'
        }
        semester_type = semester_reverse_map.get(semester_type_display, 'SEM1')
        
        # Check if already submitted
        existing = StudentRegistration.query.filter_by(
            student_id=student_id,
            program_id=program_id,
            year_level=year_level,
            semester_type=semester_type
        ).first()
        
        if existing:
            return jsonify({'success': False, 'error': 'Application already submitted for this selection'}), 400
        
        # Create registration (pending payment approval)
        registration = StudentRegistration(
            student_id=student_id,
            program_id=program_id,
            year_level=year_level,
            semester_type=semester_type,
            payment_status='pending'
        )
        db.session.add(registration)
        db.session.flush()
        
        # Add selected courses
        for course_id in course_ids:
            rc = RegisteredCourse(
                registration_id=registration.id,
                course_id=course_id
            )
            db.session.add(rc)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration application submitted successfully'})
    except Exception as e:
        db.session.rollback()
        print("SUBMIT REGISTRATION ERROR:", e)
        return jsonify({'success': False, 'error': str(e)}), 500