# reset_password.py
from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Find or create admin user
    admin = User.query.filter_by(role='admin').first()
    
    if not admin:
        # Create admin if none exists
        admin = User(
            username='admin',
            email='admin@cavendish.ac.zm',
            role='admin'
        )
        print("Creating new admin user...")
    
    # Reset password
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    
    print(f"✅ Admin credentials:")
    print(f"   Username: {admin.username}")
    print(f"   Password: admin123")
    print(f"   Email: {admin.email}")