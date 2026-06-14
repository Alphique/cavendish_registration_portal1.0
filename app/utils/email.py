# app/utils/email.py

from flask_mail import Message
from app.extensions import mail
import logging
from flask import url_for

logger = logging.getLogger(__name__)


def send_registration_email(student):
    """
    Send registration confirmation email to student
    Returns True if successful, False otherwise
    """
    try:
        subject = "Welcome to Cavendish University - Registration Successful"

        # Dynamic login link using url_for
        login_link = url_for('student.student_login', _external=True)

        # HTML version of the email
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Registration Successful</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #0d2453 0%, #1a237e 100%); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background: linear-gradient(135deg, #0d2453 0%, #1a237e 100%);
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    margin: 20px 0;
                    font-weight: bold;
                }}
                .button:hover {{
                    background: linear-gradient(135deg, #1a237e 0%, #0d2453 100%);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Cavendish University</h2>
                    <p>Registration Confirmation</p>
                </div>
                <div class="content">
                    <h3>Dear {student.name},</h3>
                    <p>Congratulations! You have successfully registered on the Cavendish University Student Registration Portal.</p>
                    
                    <h4>Your Registration Details:</h4>
                    <ul>
                        <li><strong>Student Number:</strong> {student.student_number}</li>
                        <li><strong>Name:</strong> {student.name}</li>
                        <li><strong>Email:</strong> {student.email}</li>
                    </ul>
                    
                    <p>You may now log in and begin your semester registration process.</p>
                    
                    <div style="text-align: center;">
                        <a href="{login_link}" class="button">Login to Your Account →</a>
                    </div>
                    
                    <p><strong>Please keep your login credentials secure.</strong></p>
                    
                    <p>We wish you success in your academic journey.</p>
                    
                    <p>Regards,<br>Registrar's Office<br>Cavendish University</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Cavendish University. All rights reserved.</p>
                    <p>Plot 15267 Chindo Road, Lusaka, Zambia</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version with login link
        plain_body = f"""
Dear {student.name},

Congratulations!

You have successfully registered on the Cavendish University Student Registration Portal.

Student Number: {student.student_number}
Name: {student.name}
Email: {student.email}

You may now log in and begin your semester registration process.

Login here: {login_link}

Please keep your login credentials secure.

We wish you success in your academic journey.

Regards,
Registrar's Office
Cavendish University
"""

        # Create message with correct sender format
        msg = Message(
            subject=subject,
            recipients=[student.email],
            body=plain_body,
            html=html_body
        )
        
        # Set sender properly
        msg.sender = ("Cavendish University", "cavendishregistrationportal@tukakula.com")

        # Send email
        mail.send(msg)
        logger.info(f"Registration email sent successfully to {student.email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send registration email to {student.email}: {str(e)}")
        return False


def send_registration_submission_email(
    student,
    program_name,
    year_level,
    semester_name,
    course_count
):
    """
    Send registration submission confirmation
    """
    try:
        subject = "Registration Application Submitted"

        # Dynamic dashboard link
        dashboard_link = url_for('student.student_dashboard', _external=True)

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width:700px;margin:auto;">
                <div style="background:#1a237e;color:white;padding:20px;text-align:center;">
                    <h2>Cavendish University</h2>
                    <p>Registration Application Received</p>
                </div>
                <div style="padding:25px;">
                    <p>Dear <strong>{student.name}</strong>,</p>
                    <p>Your semester registration application has been submitted successfully.</p>
                    <h3>Registration Details</h3>
                    <table style="width:100%;border-collapse:collapse;">
                        <tr><td style="padding:8px;"><strong>Student Number</strong></td><td style="padding:8px;">{student.student_number}</td></tr>
                        <tr><td style="padding:8px;"><strong>Program</strong></td><td style="padding:8px;">{program_name}</td></tr>
                        <tr><td style="padding:8px;"><strong>Year Level</strong></td><td style="padding:8px;">{year_level}</td></tr>
                        <tr><td style="padding:8px;"><strong>Semester</strong></td><td style="padding:8px;">{semester_name}</td></tr>
                        <tr><td style="padding:8px;"><strong>Selected Courses</strong></td><td style="padding:8px;">{course_count}</td></tr>
                    </table>
                    <br>
                    <div style="background:#fff8e1;padding:15px;border-left:4px solid #ff9800;">
                        Your registration is currently pending approval.
                    </div>
                    <br>
                    <p>Once approved, your Registration Slip will be generated automatically and made available for download.</p>
                    <p>You will receive another email notification when approval has been completed.</p>
                    <div style="text-align:center; margin-top:20px;">
                        <a href="{dashboard_link}" style="display:inline-block;padding:10px 20px;background:#1a237e;color:white;text-decoration:none;border-radius:8px;">Go to Dashboard →</a>
                    </div>
                    <p>Regards,<br>Registrar's Office<br>Cavendish University</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_body = f"""
Dear {student.name},

Your semester registration application has been submitted successfully.

Program: {program_name}
Year Level: {year_level}
Semester: {semester_name}
Selected Courses: {course_count}

Status: PENDING APPROVAL

Once approved, your Registration Slip will be generated automatically and made available for download.

You will receive another email once approval is completed.

Dashboard: {dashboard_link}

Regards,
Registrar's Office
Cavendish University
"""

        msg = Message(
            subject=subject,
            recipients=[student.email],
            body=plain_body,
            html=html_body
        )

        msg.sender = ("Cavendish University", "cavendishregistrationportal@tukakula.com")

        mail.send(msg)
        logger.info(f"Registration submission email sent to {student.email}")
        return True

    except Exception as e:
        logger.error(f"Registration submission email failed: {str(e)}")
        return False


def send_payment_approval_email(student, registration_slip, payment):
    """
    Send payment approval email with registration slip link
    """
    try:
        subject = "Payment Approved - Registration Slip Available"

        # Dynamic download link using url_for
        download_link = url_for('student.download_registration_slip', _external=True)
        dashboard_link = url_for('student.student_dashboard', _external=True)

        amount_display = f"ZMW {payment.amount:,.2f}" if payment.amount is not None else "N/A"
        reference_display = payment.reference or "N/A"
        approved_date_display = payment.approved_date.strftime("%d %B, %Y") if payment.approved_date else "N/A"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width:700px;margin:auto;">
                <div style="background:#28a745;color:white;padding:20px;text-align:center;">
                    <h2>Cavendish University</h2>
                    <p>Payment Approved ✓</p>
                </div>
                <div style="padding:25px;">
                    <p>Dear <strong>{student.name}</strong>,</p>
                    <p>We are pleased to inform you that your payment has been <strong style="color:#28a745;">APPROVED</strong>.</p>
                    
                    <h3>Payment Details</h3>
                    <table style="width:100%;border-collapse:collapse;">
                        <tr><td style="padding:8px;"><strong>Student Number</strong></td><td style="padding:8px;">{student.student_number}</td></tr>
                        <tr><td style="padding:8px;"><strong>Amount Paid</strong></td><td style="padding:8px;">{amount_display}</td></tr>
                        <tr><td style="padding:8px;"><strong>Reference Number</strong></td><td style="padding:8px;">{reference_display}</td></tr>
                        <tr><td style="padding:8px;"><strong>Approved Date</strong></td><td style="padding:8px;">{approved_date_display}</td></tr>
                    </table>
                    <br>
                    <div style="background:#e8f5e9;padding:15px;border-left:4px solid #28a745;">
                        Your registration is now complete.
                    </div>
                    <br>
                    <p>Your Registration Slip has been generated and is available for download.</p>
                    <div style="text-align:center;">
                        <a href="{download_link}" style="display:inline-block;padding:12px 24px;background:#1a237e;color:white;text-decoration:none;border-radius:8px;font-weight:bold;">
                            📄 Download Registration Slip →
                        </a>
                    </div>
                    <div style="text-align:center; margin-top:15px;">
                        <a href="{dashboard_link}" style="display:inline-block;padding:10px 20px;background:#6c757d;color:white;text-decoration:none;border-radius:8px;">
                            Go to Dashboard
                        </a>
                    </div>
                    <p>You may also access the registration slip anytime from your student dashboard.</p>
                    <p>Regards,<br>Finance & Registrar's Office<br>Cavendish University</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_body = f"""
Dear {student.name},

PAYMENT APPROVED

Your payment has been approved successfully.

Student Number: {student.student_number}
Amount Paid: {amount_display}
Reference Number: {reference_display}
Approved Date: {approved_date_display}

Your Registration Slip is now available.

Download: {download_link}
Dashboard: {dashboard_link}

You may also access it from your student dashboard.

Regards,
Finance & Registrar's Office
Cavendish University
"""

        msg = Message(
            subject=subject,
            recipients=[student.email],
            body=plain_body,
            html=html_body
        )

        msg.sender = ("Cavendish University", "cavendishregistrationportal@tukakula.com")

        mail.send(msg)
        logger.info(f"Payment approval email sent to {student.email}")
        return True

    except Exception as e:
        logger.error(f"Payment approval email failed: {str(e)}")
        return False


def send_payment_rejection_email(student, payment, reason=None):
    """
    Send payment rejection email
    """
    try:
        subject = "Payment Update - Action Required"

        reason_text = reason or "Please contact the finance office for more information."

        reference_display = payment.reference or "N/A"
        submission_date_display = payment.submitted_date.strftime("%d %B, %Y") if payment.submitted_date else "N/A"
        
        # Dynamic dashboard link
        dashboard_link = url_for('student.student_dashboard', _external=True)

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width:700px;margin:auto;">
                <div style="background:#dc3545;color:white;padding:20px;text-align:center;">
                    <h2>Cavendish University</h2>
                    <p>Payment Status: Rejected</p>
                </div>
                <div style="padding:25px;">
                    <p>Dear <strong>{student.name}</strong>,</p>
                    <p>Unfortunately your payment submission could not be approved.</p>
                    
                    <table style="width:100%;border-collapse:collapse;">
                        <tr><td style="padding:8px;"><strong>Student Number</strong></td><td style="padding:8px;">{student.student_number}</td></tr>
                        <tr><td style="padding:8px;"><strong>Reference Number</strong></td><td style="padding:8px;">{reference_display}</td></tr>
                        <tr><td style="padding:8px;"><strong>Submission Date</strong></td><td style="padding:8px;">{submission_date_display}</td></tr>
                    </table>
                    <br>
                    <div style="background:#ffebee;padding:15px;border-left:4px solid #dc3545;">
                        <strong>Reason:</strong> {reason_text}
                    </div>
                    <br>
                    <p>Please log in and upload a new payment slip.</p>
                    <div style="text-align:center;">
                        <a href="{dashboard_link}" style="display:inline-block;padding:12px 24px;background:#1a237e;color:white;text-decoration:none;border-radius:8px;">
                            Go to Dashboard →
                        </a>
                    </div>
                    <p>Regards,<br>Finance Office<br>Cavendish University</p>
                </div>
            </div>
        </body>
        </html>
        """

        plain_body = f"""
Dear {student.name},

PAYMENT REJECTED

Student Number: {student.student_number}
Reference Number: {reference_display}
Submission Date: {submission_date_display}

Reason: {reason_text}

Please log in and upload a new payment slip.

Dashboard: {dashboard_link}

Regards,
Finance Office
Cavendish University
"""

        msg = Message(
            subject=subject,
            recipients=[student.email],
            body=plain_body,
            html=html_body
        )

        msg.sender = ("Cavendish University", "cavendishregistrationportal@tukakula.com")

        mail.send(msg)
        logger.info(f"Payment rejection email sent to {student.email}")
        return True

    except Exception as e:
        logger.error(f"Payment rejection email failed: {str(e)}")
        return False


def send_password_reset_email(user, reset_link):
    """
    Send password reset email
    """
    try:
        subject = "Reset Your Cavendish University Password"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width:700px;margin:auto;">
                <div style="background:#1a237e;color:white;padding:20px;text-align:center;">
                    <h2>Cavendish University</h2>
                    <p>Password Reset Request</p>
                </div>

                <div style="padding:25px;">
                    <p>Dear <strong>{user.username}</strong>,</p>

                    <p>We received a request to reset the password for your student portal account.</p>

                    <div style="background:#fff8e1;padding:15px;border-left:4px solid #ff9800;">
                        This link will expire in <strong>1 hour</strong>.
                    </div>

                    <br>

                    <div style="text-align:center;">
                        <a href="{reset_link}"
                           style="
                               display:inline-block;
                               padding:12px 24px;
                               background:#1a237e;
                               color:white;
                               text-decoration:none;
                               border-radius:8px;
                               font-weight:bold;">
                            Reset Password →
                        </a>
                    </div>

                    <br>

                    <p>If you did not request a password reset, please ignore this email.</p>

                    <p>
                        For security reasons, never share your password with anyone.
                    </p>

                    <p>
                        Regards,<br>
                        ICT Support Team<br>
                        Cavendish University
                    </p>
                </div>

                <div style="background:#f5f5f5;padding:15px;text-align:center;font-size:12px;">
                    © 2025 Cavendish University
                </div>
            </div>
        </body>
        </html>
        """

        plain_body = f"""
Dear {user.username},

A password reset request was received for your account.

Click the link below to reset your password:

{reset_link}

This link expires in 1 hour.

If you did not request this reset, simply ignore this email.

Regards,
ICT Support Team
Cavendish University
"""

        msg = Message(
            subject=subject,
            sender="cavendishregistrationportal@tukakula.com",
            recipients=[user.email],
            body=plain_body,
            html=html_body
        )

        logger.info(f"Sending password reset email to {user.email}")

        mail.send(msg)

        logger.info(f"Password reset email sent successfully to {user.email}")

        return True

    except Exception as e:
        logger.exception("Password reset email failed")
        return False