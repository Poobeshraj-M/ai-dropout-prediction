import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'students.db')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("PRAGMA table_info(students)")
cols = [r[1] for r in c.fetchall()]

if 'department' not in cols:
    c.execute("ALTER TABLE students ADD COLUMN department TEXT DEFAULT 'General'")
    print("Added 'department' column to students table.")

if 'roll_number' not in cols:
    c.execute("ALTER TABLE students ADD COLUMN roll_number TEXT DEFAULT 'N/A'")
    print("Added 'roll_number' column to students table.")
else:
    print("'roll_number' column already exists.")

conn.commit()
conn.close()
print("Migration complete!")
