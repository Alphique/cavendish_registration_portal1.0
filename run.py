# run.py
from app import create_app
from app.extensions import db  # use extensions for consistent initialization

app = create_app()

def create_db():
    """Create all database tables if they do not exist."""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")

if __name__ == "__main__":
    # Ensure DB tables are created before running the server
    create_db()

    # Run the app
    app.run(
        host="0.0.0.0",  # accessible externally if needed
        port=5000,
        debug=True       # set to False in production
    )
