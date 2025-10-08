# app/routes/general_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import User
from app.extensions import db, mail
from flask_mail import Message
from werkzeug.security import generate_password_hash
import secrets
from datetime import datetime, timedelta

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

        # Send email with reset link
        reset_link = url_for('general.reset_password', token=token, _external=True)
        msg = Message(
            subject="Password Reset Request",
            recipients=[email],
            html=f"""
                <p>Hello {user.username},</p>
                <p>You requested a password reset. Click the link below to reset your password:</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p>If you didn't request this, ignore this email.</p>
            """
        )
        mail.send(msg)
        flash("A password reset link has been sent to your email.", "success")
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

        # Redirect based on role
        if user.role == "admin":
            return redirect(url_for('auth.admin_login'))
        else:
            return redirect(url_for('auth.student_login'))

    return render_template('reset_password.html', token=token)
