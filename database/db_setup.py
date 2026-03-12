import sqlite3
import os
from flask import Flask
from flask_bcrypt import Bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'students.db')

def setup_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            department TEXT DEFAULT 'General',
            attendance REAL,
            marks REAL,
            arrears INTEGER,
            assignments INTEGER,
            family_income INTEGER,
            travel_distance REAL,
            stress_level INTEGER,
            feedback_sentiment INTEGER,
            dropout_risk TEXT,
            counseling_recommendation TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create admins table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL
        )
    ''')
    
    # Create audit_logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            username TEXT,
            event TEXT,
            details TEXT
        )
    ''')

    # Create system_settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Insert default email settings
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('smtp_server', 'smtp.gmail.com')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('smtp_port', '587')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('smtp_user', '')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('smtp_pass', '')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('counselor_email', '')")
    
    # Insert default admin users if none exist
    cursor.execute('SELECT COUNT(*) FROM admins')
    if cursor.fetchone()[0] == 0:
        # We need a Flask app context for Bcrypt if used with it, or just use Bcrypt standalone
        app = Flask(__name__)
        bcrypt = Bcrypt(app)
        
        admin_pass = bcrypt.generate_password_hash('Admin@123').decode('utf-8')
        principal_pass = bcrypt.generate_password_hash('Principal@456').decode('utf-8')
        
        cursor.execute('''
            INSERT INTO admins (username, password, name) 
            VALUES (?, ?, ?), (?, ?, ?)
        ''', ('admin', admin_pass, 'System Administrator', 
              'principal', principal_pass, 'Principal Smith'))
    
    conn.commit()
    conn.close()
    print(f"Database initialized successfully at {DB_PATH}")

if __name__ == '__main__':
    setup_db()
