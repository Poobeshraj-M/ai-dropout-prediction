import sqlite3
import os
from flask_bcrypt import Bcrypt
from flask import Flask

# Need a Flask app context for Bcrypt
app = Flask(__name__)
bcrypt = Bcrypt(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'students.db')

def migrate_passwords():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, password FROM admins')
    admins = cursor.fetchall()
    
    updated_count = 0
    for admin in admins:
        pwd = admin['password']
        
        # Check if already hashed (bcrypt hashes start with $2b$ or $2a$)
        if not pwd.startswith('$2b$') and not pwd.startswith('$2a$'):
            hashed_pwd = bcrypt.generate_password_hash(pwd).decode('utf-8')
            cursor.execute('UPDATE admins SET password = ? WHERE id = ?', (hashed_pwd, admin['id']))
            updated_count += 1
            print(f"Hashed password for admin ID: {admin['id']}")
            
    conn.commit()
    conn.close()
    print(f"Migration complete. Hashed {updated_count} passwords.")

if __name__ == '__main__':
    migrate_passwords()
