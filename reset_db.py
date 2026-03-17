import sqlite3
from werkzeug.security import generate_password_hash
conn = sqlite3.connect("school.db")
cursor = conn.cursor()

# STUDENTS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_number TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    birthday TEXT,
    gender TEXT,
    enrollment_date TEXT,
    leaving_year TEXT,
    class_name TEXT,
    home_address TEXT,
    mailing_address TEXT,
    student_phone TEXT,
    medical_info TEXT,
    emergency_contact TEXT,
    guardian1_name TEXT,
    guardian1_relationship TEXT,
    guardian1_phone TEXT,
    guardian1_whatsapp TEXT,
    guardian1_email TEXT,
    guardian2_name TEXT,
    guardian2_relationship TEXT,
    guardian2_phone TEXT,
    guardian2_whatsapp TEXT,
    guardian2_email TEXT
)
""")

# FEES TABLE
# FEES TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    academic_year TEXT,

    term1_fee REAL DEFAULT 0,
    term1_paid REAL DEFAULT 0,
    term1_balance REAL DEFAULT 0,

    term2_fee REAL DEFAULT 0,
    term2_paid REAL DEFAULT 0,
    term2_balance REAL DEFAULT 0,

    term3_fee REAL DEFAULT 0,
    term3_paid REAL DEFAULT 0,
    term3_balance REAL DEFAULT 0,

    total_fee REAL DEFAULT 0,
    total_paid REAL DEFAULT 0,
    total_balance REAL DEFAULT 0,

    FOREIGN KEY (student_id) REFERENCES students(id)
)
""")

# ATTENDANCE TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    class_name TEXT,
    date TEXT,
    status TEXT,
    FOREIGN KEY (student_id) REFERENCES students(id)
)
""")
# USERS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

# TEACHER CLASSES TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS teacher_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    class_name TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

# PARENT-STUDENT LINK TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS parent_students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    student_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (student_id) REFERENCES students(id)
)
""")
# DEFAULT DIRECTOR ACCOUNT
director_password = generate_password_hash("admin123")

cursor.execute("""
INSERT OR IGNORE INTO users (full_name, username, password, role)
VALUES (?, ?, ?, ?)
""", ("System Director", "director", director_password, "director"))
conn.commit()
conn.close()

print("Database recreated successfully.")