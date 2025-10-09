# check_db.py
from app import create_app
import os

app = create_app()
print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])

# Extract the database path
db_uri = app.config['SQLALCHEMY_DATABASE_URI']
if db_uri.startswith('sqlite:///'):
    db_path = db_uri.replace('sqlite:///', '')
    print("Database path:", db_path)
    print("Database exists:", os.path.exists(db_path))
    
    # Check if it's in instance folder
    instance_path = os.path.join('instance', db_path)
    print("Instance path exists:", os.path.exists(instance_path))