# cleanup_database.py
from app import create_app, db
from app.models import Payment, RegistrationSlip, Registration, Student, User
import os

def cleanup_database():
    app = create_app()
    
    with app.app_context():
        print("🚀 Starting database cleanup...")
        
        # Count records before cleanup
        payments_count = Payment.query.count()
        slips_count = RegistrationSlip.query.count()
        registrations_count = Registration.query.count()
        students_count = Student.query.count()
        users_count = User.query.count()
        
        print(f"Before cleanup:")
        print(f"  - Payments: {payments_count}")
        print(f"  - Registration Slips: {slips_count}")
        print(f"  - Registrations: {registrations_count}")
        print(f"  - Students: {students_count}")
        print(f"  - Users: {users_count}")
        
        # Delete all data except users
        Payment.query.delete()
        RegistrationSlip.query.delete()
        Registration.query.delete()
        Student.query.delete()
        
        # Commit the changes
        db.session.commit()
        
        # Count records after cleanup
        payments_after = Payment.query.count()
        slips_after = RegistrationSlip.query.count()
        registrations_after = Registration.query.count()
        students_after = Student.query.count()
        users_after = User.query.count()
        
        print(f"\nAfter cleanup:")
        print(f"  - Payments: {payments_after}")
        print(f"  - Registration Slips: {slips_after}")
        print(f"  - Registrations: {registrations_after}")
        print(f"  - Students: {students_after}")
        print(f"  - Users: {users_after} (preserved)")
        
        print("\n✅ Database cleanup completed successfully!")
        print("📝 All student data, payments, and registration slips have been removed.")
        print("🔐 User login credentials have been preserved.")

if __name__ == "__main__":
    cleanup_database()