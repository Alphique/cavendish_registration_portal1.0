# manual_fix_correct.py
import sqlite3
import os

def manual_fix():
    # Use the correct database path we found
    db_path = r'app\cavendish_registration.db'
    print(f"Using database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # First, let's see what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Existing tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # List of columns to add (table_name: [(column_name, column_type), ...])
        columns_to_add = {
            'student': [
                ('faculty', 'VARCHAR(100)'),
                ('semester', 'VARCHAR(20)')
            ],
            'payment': [
                ('receipt_image', 'VARCHAR(255)')
            ],
            'registration': [
                ('academic_year', 'VARCHAR(20)')
            ],
            'registration_slip': [
                ('academic_year', 'VARCHAR(20)'),
                ('semester', 'VARCHAR(20)'),
                ('program_name', 'VARCHAR(100)'),
                ('faculty_name', 'VARCHAR(100)')
            ],
            'user': [
                ('created_at', 'DATETIME'),
                ('last_login', 'DATETIME')
            ]
        }
        
        # Add columns to each table if the table exists
        for table, columns in columns_to_add.items():
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                print(f"Table {table} doesn't exist, skipping...")
                continue
                
            for column_name, column_type in columns:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")
                    print(f"Added {column_name} to {table} table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e):
                        print(f"Column {column_name} already exists in {table} table")
                    else:
                        print(f"Error adding {column_name} to {table}: {e}")
        
        # Create system_log table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action VARCHAR(100) NOT NULL,
                description TEXT,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES user (id)
            )
        ''')
        print("Created system_log table (or it already exists)")
        
        conn.commit()
        print("\nManual migration completed successfully!")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    manual_fix()