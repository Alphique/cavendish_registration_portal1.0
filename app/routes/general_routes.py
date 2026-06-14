# app/routes/general_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import User
from app.extensions import db, mail
from flask_mail import Message
from werkzeug.security import generate_password_hash
import secrets
from datetime import datetime, timedelta

# Import email helper function
from app.utils.email import send_password_reset_email

general = Blueprint('general', __name__)

# -------------------------------
# FORGOT PASSWORD
# -------------------------------
@general.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email:
            flash("Please enter your email address.", "danger")
            return redirect(url_for('general.forgot_password'))

        # Find user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found with that email.", "danger")
            return redirect(url_for('general.forgot_password'))

        # Generate a reset token and expiry (valid for 1 hour)
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        # Send email with reset link using the email helper
        reset_link = url_for('general.reset_password', token=token, _external=True)
        
        email_sent = send_password_reset_email(user, reset_link)
        
        if email_sent:
            flash("A password reset link has been sent to your email.", "success")
        else:
            flash("Unable to send reset email. Please contact support.", "danger")
        
        return redirect(url_for('general.forgot_password'))

    return render_template('forgot_password.html')


# -------------------------------
# RESET PASSWORD
# -------------------------------
@general.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.reset_token_expiry or datetime.utcnow() > user.reset_token_expiry:
        flash("Invalid or expired token.", "danger")
        return redirect(url_for('general.forgot_password'))

    if request.method == 'POST':

        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not password or not confirm_password:
            flash("Please fill in all fields.", "danger")
            return redirect(url_for('general.reset_password', token=token))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('general.reset_password', token=token))

        # Update password
        user.set_password(password)

        user.reset_token = None
        user.reset_token_expiry = None

        db.session.commit()

        flash("Password updated successfully! You can now log in.", "success")

        if user.role == "admin":
            return redirect(url_for('admin.admin_login'))
        else:
            return redirect(url_for('student.student_login'))

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reset Password</title>

        <meta name="viewport" content="width=device-width, initial-scale=1">

        <style>

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Segoe UI', sans-serif;
            }}

            body {{
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                background: linear-gradient(
                    135deg,
                    #0d2453 0%,
                    #1a237e 100%
                );
                padding: 20px;
            }}

            .card {{
                width: 100%;
                max-width: 450px;
                background: white;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 15px 40px rgba(0,0,0,.2);
            }}

            .header {{
                background: #0d2453;
                color: white;
                text-align: center;
                padding: 30px;
            }}

            .header h2 {{
                margin-bottom: 8px;
            }}

            .header p {{
                opacity: .9;
            }}

            .content {{
                padding: 35px;
            }}

            .form-group {{
                margin-bottom: 20px;
            }}

            label {{
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #333;
            }}

            input {{
                width: 100%;
                padding: 14px;
                border: 1px solid #ddd;
                border-radius: 10px;
                font-size: 15px;
                transition: .3s;
            }}

            input:focus {{
                outline: none;
                border-color: #1a237e;
                box-shadow: 0 0 0 3px rgba(26,35,126,.15);
            }}

            .btn {{
                width: 100%;
                padding: 14px;
                border: none;
                border-radius: 10px;
                background: linear-gradient(
                    135deg,
                    #0d2453 0%,
                    #1a237e 100%
                );
                color: white;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: .3s;
            }}

            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(26,35,126,.25);
            }}

            .footer {{
                text-align: center;
                color: #777;
                font-size: 13px;
                margin-top: 20px;
            }}

        </style>
    </head>

    <body>

        <div class="card">

            <div class="header">
                <h2>Cavendish University</h2>
                <p>Reset Your Password</p>
            </div>

            <div class="content">

                <form method="POST">

                    <div class="form-group">
                        <label>New Password</label>
                        <input
                            type="password"
                            name="password"
                            placeholder="Enter new password"
                            required>
                    </div>

                    <div class="form-group">
                        <label>Confirm Password</label>
                        <input
                            type="password"
                            name="confirm_password"
                            placeholder="Confirm new password"
                            required>
                    </div>

                    <button type="submit" class="btn">
                        Reset Password
                    </button>

                </form>

                <div class="footer">
                    © 2026 Cavendish University
                </div>

            </div>

        </div>

    </body>
    </html>
    """