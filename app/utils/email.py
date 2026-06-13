# app/utils/email.py

from flask_mail import Message
from app.extensions import mail
import logging

logger = logging.getLogger(__name__)


def send_registration_email(student):
    """
    Send registration confirmation email to student
    Returns True if successful, False otherwise
    """
    try:
        subject = "Welcome to Cavendish University - Registration Successful"

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

        # Plain text version
        plain_body = f"""
Dear {student.name},

Congratulations!

You have successfully registered on the Cavendish University Student Registration Portal.

Student Number: {student.student_number}
Name: {student.name}
Email: {student.email}

You may now log in and begin your semester registration process.

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
        # Don't raise the error - just log it so registration continues
        return False