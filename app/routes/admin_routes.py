#app/routes/admin_routes.py
import os
from flask import Blueprint, render_template, redirect, url_for, flash, send_from_directory, current_app, session, request
from functools import wraps
from werkzeug.security import check_password_hash
from app.models import db, User, Student, Payment, Registration

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
    pending_payments = Payment.query.filter_by(status='Pending').all()
    approved_payments = Payment.query.filter_by(status='Approved').all()
    rejected_payments = Payment.query.filter_by(status='Rejected').all()
    return render_template(
        'admin/dashboard.html',
        pending_payments=pending_payments,
        approved_payments=approved_payments,
        rejected_payments=rejected_payments
    )

# -----------------
# Approve/Reject Payment
# -----------------
@admin_bp.route('/payment/<int:payment_id>/<action>')
@admin_required
def manage_payment(payment_id, action):
    payment = Payment.query.get_or_404(payment_id)

    if action == 'approve':
        payment.status = 'Approved'
        registration = Registration.query.filter_by(student_id=payment.student_id).first()
        if not registration:
            registration = Registration(student_id=payment.student_id, is_registered=True)
            db.session.add(registration)
        else:
            registration.is_registered = True
        db.session.commit()
        flash(f'Payment for {payment.student.name} approved and student registered.', 'success')

    elif action == 'reject':
        payment.status = 'Rejected'
        db.session.commit()
        flash(f'Payment for {payment.student.name} rejected.', 'warning')
    else:
        flash("Invalid action.", "danger")

    return redirect(url_for('admin.dashboard'))

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
