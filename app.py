from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import random
import sqlite3
import string
from functools import wraps

import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "school-secret-key"

CLASS_OPTIONS = [
    "Form 1 Grey", "Form 1 Blue",
    "Form 2 Grey", "Form 2 Blue",
    "Form 3 Grey", "Form 3 Blue",
    "Form 4 Grey", "Form 4 Blue",
    "Form 5", "Form 6"
]


# =========================================================
# DATABASE
# =========================================================
def is_postgres():
    return os.environ.get("DATABASE_URL") is not None


def get_db():
    if is_postgres():
        return psycopg2.connect(
            os.environ.get("DATABASE_URL"),
            cursor_factory=RealDictCursor
        )
    else:
        conn = sqlite3.connect("school.db")
        conn.row_factory = sqlite3.Row
        return conn


def convert_query(query):
    if is_postgres():
        return query
    return query.replace("%s", "?")


def fetch_one(query, params=()):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(convert_query(query), params)
    row = cursor.fetchone()
    conn.close()
    return row


def fetch_all(query, params=()):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(convert_query(query), params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def execute_commit(query, params=()):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(convert_query(query), params)
    conn.commit()
    conn.close()


def insert_and_get_id(query, params=()):
    conn = get_db()
    cursor = conn.cursor()

    if is_postgres():
        cursor.execute(query + " RETURNING id", params)
        new_id = cursor.fetchone()["id"]
    else:
        cursor.execute(convert_query(query), params)
        new_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return new_id


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    if is_postgres():
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                student_number VARCHAR(50) UNIQUE,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                birthday VARCHAR(50),
                gender VARCHAR(20),
                enrollment_date VARCHAR(50),
                leaving_year VARCHAR(20),
                class_name VARCHAR(100),
                boarding_status VARCHAR(30),
                home_address TEXT,
                mailing_address TEXT,
                student_phone VARCHAR(50),
                medical_info TEXT,
                emergency_contact VARCHAR(100),
                guardian1_name VARCHAR(255),
                guardian1_relationship VARCHAR(100),
                guardian1_phone VARCHAR(50),
                guardian1_whatsapp VARCHAR(50),
                guardian1_email VARCHAR(255),
                guardian2_name VARCHAR(255),
                guardian2_relationship VARCHAR(100),
                guardian2_phone VARCHAR(50),
                guardian2_whatsapp VARCHAR(50),
                guardian2_email VARCHAR(255),
                current_status VARCHAR(50)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guardians (
                id SERIAL PRIMARY KEY,
                student_id INTEGER,
                parent_user_id INTEGER,
                full_name VARCHAR(255),
                relationship VARCHAR(100),
                phone VARCHAR(50),
                whatsapp VARCHAR(50),
                email VARCHAR(255)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fees (
                id SERIAL PRIMARY KEY,
                student_id INTEGER,
                term_name VARCHAR(50),
                amount NUMERIC(10,2),
                paid_amount NUMERIC(10,2) DEFAULT 0,
                balance NUMERIC(10,2),
                status VARCHAR(50),
                due_date VARCHAR(50)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                teacher_id VARCHAR(50),
                full_name VARCHAR(255),
                phone VARCHAR(50),
                email VARCHAR(255)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id SERIAL PRIMARY KEY,
                student_id INTEGER,
                class_name VARCHAR(100),
                subject VARCHAR(100),
                term VARCHAR(50),
                marks NUMERIC(6,2),
                grade VARCHAR(10)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id SERIAL PRIMARY KEY,
                student_id INTEGER,
                class_name VARCHAR(100),
                date VARCHAR(50),
                status VARCHAR(50)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teacher_assignments (
                id SERIAL PRIMARY KEY,
                teacher_id INTEGER,
                class_name VARCHAR(100),
                subject VARCHAR(100)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id SERIAL PRIMARY KEY,
                class_name VARCHAR(100),
                subject VARCHAR(100),
                title VARCHAR(255),
                description TEXT,
                due_date VARCHAR(50),
                created_by VARCHAR(255)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fee_payments (
                id SERIAL PRIMARY KEY,
                fee_id INTEGER,
                payment_date VARCHAR(50),
                amount_paid NUMERIC(10,2),
                receipt_number VARCHAR(100)
            )
        """)

    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)

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
                boarding_status TEXT,
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
                guardian2_email TEXT,
                current_status TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guardians (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                parent_user_id INTEGER,
                full_name TEXT,
                relationship TEXT,
                phone TEXT,
                whatsapp TEXT,
                email TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                term_name TEXT,
                amount REAL,
                paid_amount REAL DEFAULT 0,
                balance REAL,
                status TEXT,
                due_date TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                teacher_id TEXT,
                full_name TEXT,
                phone TEXT,
                email TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                class_name TEXT,
                subject TEXT,
                term TEXT,
                marks REAL,
                grade TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                class_name TEXT,
                date TEXT,
                status TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teacher_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER,
                class_name TEXT,
                subject TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT,
                subject TEXT,
                title TEXT,
                description TEXT,
                due_date TEXT,
                created_by TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fee_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fee_id INTEGER,
                payment_date TEXT,
                amount_paid REAL,
                receipt_number TEXT
            )
        """)

    conn.commit()
    conn.close()
def run_migrations():
    conn = get_db()
    cursor = conn.cursor()

    statements = [
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS boarding_status VARCHAR(30)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS home_address TEXT",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS mailing_address TEXT",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS student_phone VARCHAR(50)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS medical_info TEXT",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS emergency_contact VARCHAR(100)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian1_name VARCHAR(255)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian1_relationship VARCHAR(100)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian1_phone VARCHAR(50)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian1_whatsapp VARCHAR(50)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian1_email VARCHAR(255)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian2_name VARCHAR(255)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian2_relationship VARCHAR(100)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian2_phone VARCHAR(50)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian2_whatsapp VARCHAR(50)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS guardian2_email VARCHAR(255)",
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS current_status VARCHAR(50)",

        "ALTER TABLE fees ADD COLUMN IF NOT EXISTS term_name VARCHAR(50)",
        "ALTER TABLE fees ADD COLUMN IF NOT EXISTS paid_amount NUMERIC(10,2) DEFAULT 0",
        "ALTER TABLE fees ADD COLUMN IF NOT EXISTS balance NUMERIC(10,2)",
        "ALTER TABLE fees ADD COLUMN IF NOT EXISTS status VARCHAR(50)",
        "ALTER TABLE fees ADD COLUMN IF NOT EXISTS due_date VARCHAR(50)",

        "ALTER TABLE results ADD COLUMN IF NOT EXISTS class_name VARCHAR(100)",
        "ALTER TABLE results ADD COLUMN IF NOT EXISTS term VARCHAR(50)",
        "ALTER TABLE results ADD COLUMN IF NOT EXISTS grade VARCHAR(10)",

        "ALTER TABLE attendance ADD COLUMN IF NOT EXISTS class_name VARCHAR(100)",

        """
        CREATE TABLE IF NOT EXISTS guardians (
            id SERIAL PRIMARY KEY,
            student_id INTEGER,
            parent_user_id INTEGER,
            full_name VARCHAR(255),
            relationship VARCHAR(100),
            phone VARCHAR(50),
            whatsapp VARCHAR(50),
            email VARCHAR(255)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS teacher_assignments (
            id SERIAL PRIMARY KEY,
            teacher_id INTEGER,
            class_name VARCHAR(100),
            subject VARCHAR(100)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS assignments (
            id SERIAL PRIMARY KEY,
            class_name VARCHAR(100),
            subject VARCHAR(100),
            title VARCHAR(255),
            description TEXT,
            due_date VARCHAR(50),
            created_by VARCHAR(255)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS fee_payments (
            id SERIAL PRIMARY KEY,
            fee_id INTEGER,
            payment_date VARCHAR(50),
            amount_paid NUMERIC(10,2),
            receipt_number VARCHAR(100)
        )
        """
    ]

    try:
        if is_postgres():
            for stmt in statements:
                cursor.execute(stmt)
        else:
            # SQLite fallback
            sqlite_statements = [
                "ALTER TABLE students ADD COLUMN boarding_status TEXT",
                "ALTER TABLE students ADD COLUMN home_address TEXT",
                "ALTER TABLE students ADD COLUMN mailing_address TEXT",
                "ALTER TABLE students ADD COLUMN student_phone TEXT",
                "ALTER TABLE students ADD COLUMN medical_info TEXT",
                "ALTER TABLE students ADD COLUMN emergency_contact TEXT",
                "ALTER TABLE students ADD COLUMN guardian1_name TEXT",
                "ALTER TABLE students ADD COLUMN guardian1_relationship TEXT",
                "ALTER TABLE students ADD COLUMN guardian1_phone TEXT",
                "ALTER TABLE students ADD COLUMN guardian1_whatsapp TEXT",
                "ALTER TABLE students ADD COLUMN guardian1_email TEXT",
                "ALTER TABLE students ADD COLUMN guardian2_name TEXT",
                "ALTER TABLE students ADD COLUMN guardian2_relationship TEXT",
                "ALTER TABLE students ADD COLUMN guardian2_phone TEXT",
                "ALTER TABLE students ADD COLUMN guardian2_whatsapp TEXT",
                "ALTER TABLE students ADD COLUMN guardian2_email TEXT",
                "ALTER TABLE students ADD COLUMN current_status TEXT",

                "ALTER TABLE fees ADD COLUMN term_name TEXT",
                "ALTER TABLE fees ADD COLUMN paid_amount REAL DEFAULT 0",
                "ALTER TABLE fees ADD COLUMN balance REAL",
                "ALTER TABLE fees ADD COLUMN status TEXT",
                "ALTER TABLE fees ADD COLUMN due_date TEXT",

                "ALTER TABLE results ADD COLUMN class_name TEXT",
                "ALTER TABLE results ADD COLUMN term TEXT",
                "ALTER TABLE results ADD COLUMN grade TEXT",

                "ALTER TABLE attendance ADD COLUMN class_name TEXT",

                """
                CREATE TABLE IF NOT EXISTS guardians (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    parent_user_id INTEGER,
                    full_name TEXT,
                    relationship TEXT,
                    phone TEXT,
                    whatsapp TEXT,
                    email TEXT
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS teacher_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id INTEGER,
                    class_name TEXT,
                    subject TEXT
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_name TEXT,
                    subject TEXT,
                    title TEXT,
                    description TEXT,
                    due_date TEXT,
                    created_by TEXT
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS fee_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fee_id INTEGER,
                    payment_date TEXT,
                    amount_paid REAL,
                    receipt_number TEXT
                )
                """
            ]

            for stmt in sqlite_statements:
                try:
                    cursor.execute(stmt)
                except Exception:
                    pass

        conn.commit()
    finally:
        conn.close()

def create_admin_user():
    admin = fetch_one("SELECT * FROM users WHERE username = %s", ("admin",))
    if not admin:
        execute_commit("""
            INSERT INTO users (full_name, username, password, role)
            VALUES (%s, %s, %s, %s)
        """, (
            "Administrator",
            "admin",
            generate_password_hash("admin123"),
            "admin"
        ))


# =========================================================
# HELPERS
# =========================================================
def generate_student_number():
    return "STU" + ''.join(random.choices(string.ascii_uppercase, k=2)) + ''.join(random.choices(string.digits, k=4))


def generate_teacher_id():
    row = fetch_one("SELECT COUNT(*) AS total FROM teachers")
    count = row["total"] if is_postgres() else row[0]
    return f"TCH{count + 1:03d}"


def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))

            if session.get("role") not in allowed_roles:
                flash("You are not allowed to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# =========================================================
# AUTH
# =========================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = fetch_one(
            "SELECT * FROM users WHERE username = %s",
            (request.form["username"],)
        )

        if user and check_password_hash(user["password"], request.form["password"]):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]

            if user["role"] == "parent":
                return redirect(url_for("parent_dashboard"))
            elif user["role"] == "teacher":
                return redirect(url_for("teacher_dashboard"))
            else:
                return redirect(url_for("dashboard"))

        flash("Invalid login", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================
@app.route("/dashboard")
@login_required
def dashboard():
    students_row = fetch_one("SELECT COUNT(*) AS total FROM students")
    teachers_row = fetch_one("SELECT COUNT(*) AS total FROM teachers")
    users_row = fetch_one("SELECT COUNT(*) AS total FROM users")
    fees_row = fetch_one("SELECT COUNT(*) AS total FROM fees")

    total_students = students_row["total"] if is_postgres() else students_row[0]
    total_teachers = teachers_row["total"] if is_postgres() else teachers_row[0]
    total_users = users_row["total"] if is_postgres() else users_row[0]
    total_fee_records = fees_row["total"] if is_postgres() else fees_row[0]

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_teachers=total_teachers,
        total_users=total_users,
        total_fee_records=total_fee_records
    )


# =========================================================
# STUDENTS
# =========================================================
@app.route("/students")
@login_required
@roles_required("admin", "director")
def students():
    search = request.args.get("search", "").strip()

    if search:
        if is_postgres():
            query = """
                SELECT * FROM students
                WHERE first_name ILIKE %s
                   OR last_name ILIKE %s
                   OR student_number ILIKE %s
                   OR class_name ILIKE %s
                ORDER BY class_name, first_name, last_name
            """
        else:
            query = """
                SELECT * FROM students
                WHERE first_name LIKE %s
                   OR last_name LIKE %s
                   OR student_number LIKE %s
                   OR class_name LIKE %s
                ORDER BY class_name, first_name, last_name
            """
        like_search = f"%{search}%"
        all_students = fetch_all(query, (like_search, like_search, like_search, like_search))
    else:
        all_students = fetch_all("SELECT * FROM students ORDER BY class_name, first_name, last_name")

    grouped_students = {}
    for student in all_students:
        class_name = student["class_name"] or "No Class Assigned"
        grouped_students.setdefault(class_name, []).append(student)

    return render_template("students.html", grouped_students=grouped_students, search=search)


@app.route("/add_student")
@login_required
@roles_required("admin", "director")
def add_student():
    return render_template("add_student.html", class_options=CLASS_OPTIONS)


@app.route("/save_student", methods=["POST"])
@login_required
@roles_required("admin", "director")
def save_student():
    conn = get_db()
    cursor = conn.cursor()

    try:
        student_number = generate_student_number()

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        birthday = request.form.get("birthday")
        gender = request.form.get("gender")
        enrollment_date = request.form.get("enrollment_date")
        leaving_year = request.form.get("leaving_year")
        class_name = request.form.get("class_name")
        boarding_status = request.form.get("boarding_status")
        home_address = request.form.get("home_address")
        mailing_address = request.form.get("mailing_address")
        student_phone = request.form.get("student_phone")
        medical_info = request.form.get("medical_info")
        emergency_contact = request.form.get("emergency_contact")
        current_status = request.form.get("current_status")

        guardian1_name = request.form.get("guardian1_name")
        guardian1_relationship = request.form.get("guardian1_relationship")
        guardian1_phone = request.form.get("guardian1_phone")
        guardian1_whatsapp = request.form.get("guardian1_whatsapp")
        guardian1_email = request.form.get("guardian1_email")

        guardian2_name = request.form.get("guardian2_name")
        guardian2_relationship = request.form.get("guardian2_relationship")
        guardian2_phone = request.form.get("guardian2_phone")
        guardian2_whatsapp = request.form.get("guardian2_whatsapp")
        guardian2_email = request.form.get("guardian2_email")

        parent_username = request.form.get("parent_username") or guardian1_phone
        temporary_password = generate_password()
        hashed_password = generate_password_hash(temporary_password)

        if is_postgres():
            cursor.execute("""
                INSERT INTO students (
                    student_number, first_name, last_name, birthday, gender,
                    enrollment_date, leaving_year, class_name, boarding_status,
                    home_address, mailing_address, student_phone, medical_info,
                    emergency_contact, guardian1_name, guardian1_relationship,
                    guardian1_phone, guardian1_whatsapp, guardian1_email,
                    guardian2_name, guardian2_relationship, guardian2_phone,
                    guardian2_whatsapp, guardian2_email, current_status
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
                RETURNING id
            """, (
                student_number, first_name, last_name, birthday, gender,
                enrollment_date, leaving_year, class_name, boarding_status,
                home_address, mailing_address, student_phone, medical_info,
                emergency_contact, guardian1_name, guardian1_relationship,
                guardian1_phone, guardian1_whatsapp, guardian1_email,
                guardian2_name, guardian2_relationship, guardian2_phone,
                guardian2_whatsapp, guardian2_email, current_status
            ))
            student_id = cursor.fetchone()["id"]

            cursor.execute("""
                INSERT INTO users (full_name, username, password, role)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                guardian1_name,
                parent_username,
                hashed_password,
                "parent"
            ))
            parent_user_id = cursor.fetchone()["id"]
        else:
            cursor.execute("""
                INSERT INTO students (
                    student_number, first_name, last_name, birthday, gender,
                    enrollment_date, leaving_year, class_name, boarding_status,
                    home_address, mailing_address, student_phone, medical_info,
                    emergency_contact, guardian1_name, guardian1_relationship,
                    guardian1_phone, guardian1_whatsapp, guardian1_email,
                    guardian2_name, guardian2_relationship, guardian2_phone,
                    guardian2_whatsapp, guardian2_email, current_status
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?
                )
            """, (
                student_number, first_name, last_name, birthday, gender,
                enrollment_date, leaving_year, class_name, boarding_status,
                home_address, mailing_address, student_phone, medical_info,
                emergency_contact, guardian1_name, guardian1_relationship,
                guardian1_phone, guardian1_whatsapp, guardian1_email,
                guardian2_name, guardian2_relationship, guardian2_phone,
                guardian2_whatsapp, guardian2_email, current_status
            ))
            student_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO users (full_name, username, password, role)
                VALUES (?, ?, ?, ?)
            """, (
                guardian1_name,
                parent_username,
                hashed_password,
                "parent"
            ))
            parent_user_id = cursor.lastrowid

        cursor.execute(convert_query("""
            INSERT INTO guardians (
                student_id, parent_user_id, full_name, relationship, phone, whatsapp, email
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """), (
            student_id,
            parent_user_id,
            guardian1_name,
            guardian1_relationship,
            guardian1_phone,
            guardian1_whatsapp,
            guardian1_email
        ))

        if guardian2_name or guardian2_phone:
            cursor.execute(convert_query("""
                INSERT INTO guardians (
                    student_id, parent_user_id, full_name, relationship, phone, whatsapp, email
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """), (
                student_id,
                parent_user_id,
                guardian2_name,
                guardian2_relationship,
                guardian2_phone,
                guardian2_whatsapp,
                guardian2_email
            ))

        fee_terms = [
            ("Term 1", request.form.get("term1_amount", 0), request.form.get("term1_paid", 0), request.form.get("term1_due_date")),
            ("Term 2", request.form.get("term2_amount", 0), request.form.get("term2_paid", 0), request.form.get("term2_due_date")),
            ("Term 3", request.form.get("term3_amount", 0), request.form.get("term3_paid", 0), request.form.get("term3_due_date")),
        ]

        for term_name, amount, paid_amount, due_date in fee_terms:
            amount = float(amount or 0)
            paid_amount = float(paid_amount or 0)
            balance = amount - paid_amount

            if amount > 0:
                if balance <= 0:
                    status = "Paid"
                elif paid_amount > 0:
                    status = "Partially Paid"
                else:
                    status = "Pending"

                cursor.execute(convert_query("""
                    INSERT INTO fees (
                        student_id, term_name, amount, paid_amount, balance, status, due_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """), (
                    student_id,
                    term_name,
                    amount,
                    paid_amount,
                    balance,
                    status,
                    due_date
                ))

        conn.commit()
        flash(
            f"Student registered successfully. Student Number: {student_number}. Temporary parent password: {temporary_password}",
            "success"
        )
        return redirect(url_for("students"))

    except Exception as e:
        conn.rollback()
        flash(f"Error saving student: {str(e)}", "danger")
        return redirect(url_for("add_student"))

    finally:
        conn.close()


@app.route("/student_profile/<int:id>")
@login_required
@roles_required("admin", "director")
def student_profile(id):
    student = fetch_one("SELECT * FROM students WHERE id = %s", (id,))
    guardians = fetch_all("SELECT * FROM guardians WHERE student_id = %s", (id,))
    fees = fetch_all("SELECT * FROM fees WHERE student_id = %s ORDER BY term_name", (id,))
    results = fetch_all("SELECT * FROM results WHERE student_id = %s ORDER BY term, subject", (id,))
    attendance_records = fetch_all("SELECT * FROM attendance WHERE student_id = %s ORDER BY date DESC", (id,))

    return render_template(
        "student_profile.html",
        student=student,
        guardians=guardians,
        fees=fees,
        results=results,
        attendance_records=attendance_records
    )


@app.route("/edit_student/<int:id>")
@login_required
@roles_required("admin", "director")
def edit_student(id):
    student = fetch_one("SELECT * FROM students WHERE id = %s", (id,))
    return render_template("edit_student.html", student=student, class_options=CLASS_OPTIONS)


@app.route("/update_student/<int:id>", methods=["POST"])
@login_required
@roles_required("admin", "director")
def update_student(id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(convert_query("""
            UPDATE students
            SET
                first_name = %s,
                last_name = %s,
                birthday = %s,
                gender = %s,
                enrollment_date = %s,
                leaving_year = %s,
                class_name = %s,
                boarding_status = %s,
                home_address = %s,
                mailing_address = %s,
                student_phone = %s,
                medical_info = %s,
                emergency_contact = %s,
                guardian1_name = %s,
                guardian1_relationship = %s,
                guardian1_phone = %s,
                guardian1_whatsapp = %s,
                guardian1_email = %s,
                guardian2_name = %s,
                guardian2_relationship = %s,
                guardian2_phone = %s,
                guardian2_whatsapp = %s,
                guardian2_email = %s
            WHERE id = %s
        """), (
            request.form.get("first_name"),
            request.form.get("last_name"),
            request.form.get("birthday"),
            request.form.get("gender"),
            request.form.get("enrollment_date"),
            request.form.get("leaving_year"),
            request.form.get("class_name"),
            request.form.get("boarding_status"),
            request.form.get("home_address"),
            request.form.get("mailing_address"),
            request.form.get("student_phone"),
            request.form.get("medical_info"),
            request.form.get("emergency_contact"),
            request.form.get("guardian1_name"),
            request.form.get("guardian1_relationship"),
            request.form.get("guardian1_phone"),
            request.form.get("guardian1_whatsapp"),
            request.form.get("guardian1_email"),
            request.form.get("guardian2_name"),
            request.form.get("guardian2_relationship"),
            request.form.get("guardian2_phone"),
            request.form.get("guardian2_whatsapp"),
            request.form.get("guardian2_email"),
            id
        ))

        conn.commit()
        flash("Student updated successfully.", "success")
        return redirect(url_for("student_profile", id=id))

    except Exception as e:
        conn.rollback()
        flash(f"Error updating student: {str(e)}", "danger")
        return redirect(url_for("edit_student", id=id))

    finally:
        conn.close()


# =========================================================
# CLASSES
# =========================================================
@app.route("/classes")
@login_required
@roles_required("admin", "director", "teacher")
def classes():
    return render_template("classes.html", class_options=CLASS_OPTIONS)


@app.route("/class/<class_name>")
@login_required
@roles_required("admin", "director", "teacher")
def class_students(class_name):
    class_list = fetch_all(
        "SELECT * FROM students WHERE class_name = %s ORDER BY first_name, last_name",
        (class_name,)
    )
    return render_template("class_students.html", students=class_list, class_name=class_name)


# =========================================================
# TEACHERS
# =========================================================
@app.route("/teachers")
@login_required
@roles_required("admin", "director")
def teachers():
    teacher_list = fetch_all("SELECT * FROM teachers ORDER BY full_name")
    return render_template("teachers.html", teachers=teacher_list)


@app.route("/teacher_registration", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def teacher_registration():
    if request.method == "POST":
        conn = get_db()
        cursor = conn.cursor()

        try:
            name = request.form["full_name"]
            username = request.form["username"]
            password = generate_password_hash(request.form["password"])

            if is_postgres():
                cursor.execute("""
                    INSERT INTO users (full_name, username, password, role)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (name, username, password, "teacher"))
                user_id = cursor.fetchone()["id"]
            else:
                cursor.execute("""
                    INSERT INTO users (full_name, username, password, role)
                    VALUES (?, ?, ?, ?)
                """, (name, username, password, "teacher"))
                user_id = cursor.lastrowid

            cursor.execute(convert_query("""
                INSERT INTO teachers (user_id, teacher_id, full_name, phone, email)
                VALUES (%s, %s, %s, %s, %s)
            """), (
                user_id,
                generate_teacher_id(),
                name,
                request.form.get("phone"),
                request.form.get("email")
            ))

            conn.commit()
            flash("Teacher registered successfully.", "success")
            return redirect(url_for("teachers"))

        except Exception as e:
            conn.rollback()
            flash(f"Error registering teacher: {str(e)}", "danger")
            return redirect(url_for("teacher_registration"))

        finally:
            conn.close()

    return render_template("teacher_register.html")


@app.route("/teacher_dashboard")
@login_required
@roles_required("teacher")
def teacher_dashboard():
    teacher = fetch_one("""
        SELECT * FROM teachers
        WHERE user_id = %s
        LIMIT 1
    """, (session["user_id"],))

    assignments_list = []
    if teacher:
        assignments_list = fetch_all("""
            SELECT *
            FROM teacher_assignments
            WHERE teacher_id = %s
            ORDER BY class_name, subject
        """, (teacher["id"],))

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        assignments=assignments_list
    )


# =========================================================
# FEES / USERS
# =========================================================
@app.route("/fees")
@login_required
@roles_required("admin", "director")
def fees():
    search = request.args.get("search", "").strip()

    if search:
        query = """
            SELECT 
                f.*,
                s.first_name,
                s.last_name,
                s.student_number,
                s.class_name
            FROM fees f
            JOIN students s ON f.student_id = s.id
            WHERE
                s.first_name {like} %s
                OR s.last_name {like} %s
                OR s.student_number {like} %s
            ORDER BY s.class_name, s.first_name, s.last_name, f.term_name
        """.format(like="ILIKE" if is_postgres() else "LIKE")

        like_search = f"%{search}%"
        fee_records = fetch_all(query, (like_search, like_search, like_search))
    else:
        fee_records = fetch_all("""
            SELECT 
                f.*,
                s.first_name,
                s.last_name,
                s.student_number,
                s.class_name
            FROM fees f
            JOIN students s ON f.student_id = s.id
            ORDER BY s.class_name, s.first_name, s.last_name, f.term_name
        """)

    return render_template("fees.html", fee_records=fee_records, search=search)


@app.route("/update_fee/<int:fee_id>", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def update_fee(fee_id):
    fee = fetch_one("""
        SELECT 
            f.*,
            s.first_name,
            s.last_name,
            s.student_number,
            s.class_name
        FROM fees f
        JOIN students s ON f.student_id = s.id
        WHERE f.id = %s
    """, (fee_id,))

    if not fee:
        flash("Fee record not found.", "danger")
        return redirect(url_for("fees"))

    if request.method == "POST":
        try:
            additional_payment = float(request.form.get("additional_payment", 0) or 0)
        except:
            additional_payment = 0

        payment_date = request.form.get("payment_date")
        receipt_number = request.form.get("receipt_number")

        new_paid_amount = float(fee["paid_amount"] or 0) + additional_payment
        total_amount = float(fee["amount"] or 0)
        new_balance = total_amount - new_paid_amount

        if new_balance <= 0:
            new_balance = 0
            status = "Paid"
        elif new_paid_amount > 0:
            status = "Partially Paid"
        else:
            status = "Pending"

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(convert_query("""
                UPDATE fees
                SET paid_amount = %s, balance = %s, status = %s
                WHERE id = %s
            """), (new_paid_amount, new_balance, status, fee_id))

            if additional_payment > 0:
                cursor.execute(convert_query("""
                    INSERT INTO fee_payments (fee_id, payment_date, amount_paid, receipt_number)
                    VALUES (%s, %s, %s, %s)
                """), (
                    fee_id,
                    payment_date,
                    additional_payment,
                    receipt_number
                ))

            conn.commit()
            flash("Fee payment updated successfully.", "success")

        except Exception as e:
            conn.rollback()
            flash(f"Error updating fee payment: {str(e)}", "danger")

        finally:
            conn.close()

        return redirect(url_for("update_fee", fee_id=fee_id))

    payment_history = fetch_all("""
        SELECT *
        FROM fee_payments
        WHERE fee_id = %s
        ORDER BY payment_date DESC, id DESC
    """, (fee_id,))

    return render_template("update_fee.html", fee=fee, payment_history=payment_history)

@app.route("/users")
@login_required
@roles_required("admin", "director")
def users():
    user_list = fetch_all("SELECT * FROM users ORDER BY full_name")
    return render_template("users.html", users=user_list)


@app.route("/add_user", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def add_user():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()

        if not full_name or not username or not password or not role:
            flash("All fields are required.", "danger")
            return redirect(url_for("add_user"))

        existing_user = fetch_one("SELECT * FROM users WHERE username = %s", (username,))
        if existing_user:
            flash("Username already exists.", "danger")
            return redirect(url_for("add_user"))

        execute_commit("""
            INSERT INTO users (full_name, username, password, role)
            VALUES (%s, %s, %s, %s)
        """, (
            full_name,
            username,
            generate_password_hash(password),
            role
        ))

        flash("User added successfully.", "success")
        return redirect(url_for("users"))

    return render_template("add_user.html")


@app.route("/generate_fees")
@login_required
@roles_required("admin", "director")
def generate_fees():
    return render_template("generate_fees.html")


# =========================================================
# SUBJECTS / ASSIGNMENTS / ATTENDANCE / RESULTS
# =========================================================
@app.route("/subjects")
@login_required
@roles_required("admin", "director", "teacher")
def subjects():
    subject_list = fetch_all("""
        SELECT DISTINCT class_name, subject
        FROM teacher_assignments
        WHERE subject IS NOT NULL AND subject != ''
        ORDER BY class_name, subject
    """)

    return render_template("subjects.html", subjects=subject_list)


@app.route("/assign_subject", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def assign_subject():
    conn = get_db()
    cursor = conn.cursor()

    try:
        if request.method == "POST":
            class_name = request.form.get("class_name")
            subject = request.form.get("subject")

            if not class_name or not subject:
                flash("Class and subject are required.", "danger")
                return redirect(url_for("assign_subject"))

            cursor.execute(convert_query("""
                INSERT INTO teacher_assignments (teacher_id, class_name, subject)
                VALUES (%s, %s, %s)
            """), (
                0,
                class_name,
                subject
            ))
            conn.commit()
            flash("Subject assigned successfully.", "success")
            return redirect(url_for("assign_subject"))

        assignments = fetch_all("""
            SELECT class_name, subject
            FROM teacher_assignments
            ORDER BY class_name, subject
        """)

        return render_template(
            "assign_subject.html",
            class_options=CLASS_OPTIONS,
            assignments=assignments
        )

    except Exception as e:
        conn.rollback()
        flash(f"Error assigning subject: {str(e)}", "danger")
        return redirect(url_for("assign_subject"))

    finally:
        conn.close()


@app.route("/assign_teacher", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def assign_teacher():
    if request.method == "POST":
        execute_commit("""
            INSERT INTO teacher_assignments (teacher_id, class_name, subject)
            VALUES (%s, %s, %s)
        """, (
            request.form.get("teacher_id"),
            request.form.get("class_name"),
            request.form.get("subject")
        ))
        flash("Teacher assigned successfully.", "success")
        return redirect(url_for("assign_teacher"))

    teachers_list = fetch_all("SELECT * FROM teachers ORDER BY full_name")
    assignments_list = fetch_all("""
        SELECT ta.*, t.full_name
        FROM teacher_assignments ta
        JOIN teachers t ON ta.teacher_id = t.id
        ORDER BY t.full_name, ta.class_name, ta.subject
    """)

    subjects_list = ["Math", "English", "Science", "History", "Geography", "Biology"]

    return render_template(
        "assign_teacher.html",
        teachers=teachers_list,
        class_options=CLASS_OPTIONS,
        subjects=subjects_list,
        assignments=assignments_list
    )


@app.route("/assign_parent")
@login_required
@roles_required("admin", "director")
def assign_parent():
    return render_template("assign_parent.html")


@app.route("/attendance", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director", "teacher")
def attendance():
    selected_class = request.form.get("class_name") if request.method == "POST" else request.args.get("class_name")
    students_list = []

    if selected_class:
        students_list = fetch_all("""
            SELECT * FROM students
            WHERE class_name = %s
            ORDER BY first_name, last_name
        """, (selected_class,))

    return render_template(
        "attendance.html",
        class_options=CLASS_OPTIONS,
        selected_class=selected_class,
        students=students_list
    )


@app.route("/save_attendance", methods=["POST"])
@login_required
@roles_required("admin", "director", "teacher")
def save_attendance():
    conn = get_db()
    cursor = conn.cursor()

    class_name = request.form.get("class_name")
    date = request.form.get("date")
    student_ids = request.form.getlist("student_id")

    try:
        for student_id in student_ids:
            status = request.form.get(f"status_{student_id}")
            cursor.execute(convert_query("""
                INSERT INTO attendance (student_id, class_name, date, status)
                VALUES (%s, %s, %s, %s)
            """), (student_id, class_name, date, status))

        conn.commit()
        flash("Attendance saved successfully.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Error saving attendance: {str(e)}", "danger")

    finally:
        conn.close()

    return redirect(url_for("attendance", class_name=class_name))


@app.route("/attendance_records")
@login_required
@roles_required("admin", "director", "teacher")
def attendance_records():
    attendance_list = fetch_all("""
        SELECT a.*, s.first_name, s.last_name, s.student_number
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        ORDER BY a.date DESC, s.first_name, s.last_name
    """)
    return render_template("attendance_records.html", attendance_records=attendance_list)


@app.route("/enter_result")
@login_required
@roles_required("admin", "director", "teacher")
def enter_result():
    students_list = fetch_all("SELECT * FROM students ORDER BY first_name, last_name")
    subjects_list = ["Math", "English", "Science", "History", "Geography", "Biology"]

    return render_template(
        "enter_result.html",
        class_options=CLASS_OPTIONS,
        students=students_list,
        subjects=subjects_list
    )


@app.route("/save_result", methods=["POST"])
@login_required
@roles_required("admin", "director", "teacher")
def save_result():
    student_id = request.form.get("student_id")
    class_name = request.form.get("class_name")
    subject = request.form.get("subject")
    term = request.form.get("term")
    marks = request.form.get("marks")

    try:
        marks = float(marks)
    except:
        marks = 0

    if marks >= 80:
        grade = "A"
    elif marks >= 70:
        grade = "B"
    elif marks >= 60:
        grade = "C"
    elif marks >= 50:
        grade = "D"
    else:
        grade = "F"

    execute_commit("""
        INSERT INTO results (student_id, class_name, subject, term, marks, grade)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (student_id, class_name, subject, term, marks, grade))

    flash("Result saved successfully.", "success")
    return redirect(url_for("results"))


@app.route("/results")
@login_required
@roles_required("admin", "director", "teacher")
def results():
    result_records = fetch_all("""
        SELECT r.*, s.first_name, s.last_name, s.student_number
        FROM results r
        JOIN students s ON r.student_id = s.id
        ORDER BY s.first_name, s.last_name, r.subject
    """)
    return render_template("results.html", result_records=result_records)


@app.route("/assignments")
@login_required
@roles_required("admin", "director", "teacher")
def assignments():
    assignments_list = fetch_all("""
        SELECT *
        FROM assignments
        ORDER BY due_date ASC, class_name ASC, subject ASC
    """)
    return render_template("assignments.html", assignments=assignments_list)


@app.route("/add_assignment", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director", "teacher")
def add_assignment():
    if request.method == "POST":
        execute_commit("""
            INSERT INTO assignments (class_name, subject, title, description, due_date, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            request.form.get("class_name"),
            request.form.get("subject"),
            request.form.get("title"),
            request.form.get("description"),
            request.form.get("due_date"),
            session.get("full_name")
        ))

        flash("Assignment added successfully.", "success")
        return redirect(url_for("assignments"))

    subjects_list = ["Math", "English", "Science", "History", "Geography", "Biology"]
    return render_template(
        "add_assignment.html",
        class_options=CLASS_OPTIONS,
        subjects=subjects_list
    )


# =========================================================
# PARENT PORTAL
# =========================================================
@app.route("/parent_setup", methods=["GET", "POST"])
def parent_setup():
    if request.method == "POST":
        student_number = request.form.get("student_number")
        phone = request.form.get("phone")
        password = request.form.get("password")

        if not student_number or not phone or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("parent_setup"))

        user = fetch_one("""
            SELECT u.id
            FROM users u
            JOIN guardians g ON u.id = g.parent_user_id
            JOIN students s ON s.id = g.student_id
            WHERE s.student_number = %s AND g.phone = %s
            LIMIT 1
        """, (student_number, phone))

        if not user:
            flash("No matching parent account was found. Check student number and phone number.", "danger")
            return redirect(url_for("parent_setup"))

        execute_commit("""
            UPDATE users
            SET password = %s
            WHERE id = %s
        """, (generate_password_hash(password), user["id"]))

        flash("Password set successfully. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("parent_setup.html")


@app.route("/parent_dashboard")
@login_required
@roles_required("parent")
def parent_dashboard():
    student = fetch_one("""
        SELECT s.*
        FROM students s
        JOIN guardians g ON s.id = g.student_id
        WHERE g.parent_user_id = %s
        LIMIT 1
    """, (session["user_id"],))

    fee_summary = {
        "total_amount": 0,
        "total_paid": 0,
        "total_balance": 0
    }

    if student:
        fee_summary = fetch_one("""
            SELECT
                COALESCE(SUM(amount), 0) AS total_amount,
                COALESCE(SUM(paid_amount), 0) AS total_paid,
                COALESCE(SUM(balance), 0) AS total_balance
            FROM fees
            WHERE student_id = %s
        """, (student["id"],))

    return render_template(
        "parent_dashboard.html",
        student=student,
        fee_summary=fee_summary
    )


@app.route("/parent_fees")
@login_required
@roles_required("parent")
def parent_fees():
    fee_records = fetch_all("""
        SELECT f.*, s.first_name, s.last_name, s.class_name
        FROM fees f
        JOIN guardians g ON f.student_id = g.student_id
        JOIN students s ON s.id = f.student_id
        WHERE g.parent_user_id = %s
        ORDER BY f.term_name
    """, (session["user_id"],))

    return render_template("parent_fees.html", fee_records=fee_records)


@app.route("/parent_results")
@login_required
@roles_required("parent")
def parent_results():
    result_records = fetch_all("""
        SELECT r.*, s.first_name, s.last_name, s.student_number
        FROM results r
        JOIN guardians g ON r.student_id = g.student_id
        JOIN students s ON s.id = r.student_id
        WHERE g.parent_user_id = %s
        ORDER BY r.term, r.subject
    """, (session["user_id"],))

    return render_template("parent_results.html", result_records=result_records)


@app.route("/parent_attendance")
@login_required
@roles_required("parent")
def parent_attendance():
    attendance_list = fetch_all("""
        SELECT a.*, s.first_name, s.last_name, s.student_number
        FROM attendance a
        JOIN guardians g ON a.student_id = g.student_id
        JOIN students s ON s.id = a.student_id
        WHERE g.parent_user_id = %s
        ORDER BY a.date DESC
    """, (session["user_id"],))

    return render_template("parent_attendance.html", attendance_records=attendance_list)


@app.route("/parent_assignments")
@login_required
@roles_required("parent")
def parent_assignments():
    assignments_list = fetch_all("""
        SELECT a.*
        FROM assignments a
        JOIN students s ON a.class_name = s.class_name
        JOIN guardians g ON s.id = g.student_id
        WHERE g.parent_user_id = %s
        ORDER BY a.due_date ASC
    """, (session["user_id"],))

    return render_template("parent_assignments.html", assignments=assignments_list)


with app.app_context():
    try:
        init_db()
        create_admin_user()
        print("Startup completed successfully.")
    except Exception as e:
        print(f"Startup error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)