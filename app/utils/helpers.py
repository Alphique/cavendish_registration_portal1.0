import os
import io
from datetime import datetime
from flask import current_app
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_registration_slip_pdf(registration_slip):
    """Generate PDF for registration slip"""
    try:
        # Create PDF filename
        filename = f"registration_slip_{registration_slip.student.student_number}.pdf"
        file_path = os.path.join(current_app.config['REGISTRATION_SLIP_FOLDER'], filename)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=20,
            alignment=1,
            textColor=colors.HexColor('#1e3c72')
        )
        
        # Build content
        story = []
        
        # Header
        story.append(Paragraph("CAVENDISH UNIVERSITY ZAMBIA", title_style))
        story.append(Paragraph("OFFICIAL REGISTRATION SLIP", styles['Heading2']))
        story.append(Spacer(1, 20))
        
        # Student Information
        story.append(Paragraph("STUDENT INFORMATION", styles['Heading3']))
        
        student_data = [
            ["Student Name:", registration_slip.student.name],
            ["Student Number:", registration_slip.student.student_number],
            ["Program:", registration_slip.program_name or "Not specified"],
            ["Faculty:", registration_slip.faculty_name or "Not specified"],
            ["Academic Year:", registration_slip.academic_year or "2024/2025"],
            ["Semester:", registration_slip.semester or "Semester 1"],
            ["Issue Date:", registration_slip.issue_date.strftime('%d/%m/%Y')],
            ["Slip Number:", registration_slip.slip_number]
        ]
        
        # Create table
        table_data = []
        for label, value in student_data:
            table_data.append([Paragraph(f"<b>{label}</b>", styles['Normal']), Paragraph(value, styles['Normal'])])
        
        student_table = Table(table_data, colWidths=[2*inch, 4*inch])
        student_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        story.append(student_table)
        story.append(Spacer(1, 30))
        
        # Footer
        story.append(Paragraph("This is an official registration document.", styles['Normal']))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Save to file
        with open(file_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        # Update registration slip with PDF filename
        registration_slip.pdf_filename = filename
        return True
        
    except Exception as e:
        current_app.logger.error(f"PDF generation failed: {str(e)}")
        return False

def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS