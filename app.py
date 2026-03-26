from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "school-secret-key"
from functools import wraps

# =========================================================
# CLASS LIST (FIXED)
# =========================================================
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
def get_db():
    conn = sqlite3.connect("school.db")
    conn.row_factory = sqlite3.Row
    return conn

def ensure_tables():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_number TEXT,
            first_name TEXT,
            last_name TEXT,
            class_name TEXT,
            boarding_status TEXT,
            guardian1_name TEXT,
            guardian1_phone TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guardians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            parent_user_id INTEGER,
            full_name TEXT,
            phone TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            amount REAL,
            paid_amount REAL,
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

    conn.commit()
    conn.close()

# =========================================================
# HELPERS
# =========================================================
def generate_student_number():
    return "STU" + ''.join(random.choices(string.ascii_uppercase, k=2)) + ''.join(random.choices(string.digits, k=4))

def generate_teacher_id():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM teachers")
    count = cursor.fetchone()[0] + 1
    conn.close()
    return f"TCH{count:03d}"

def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# =========================================================
# AUTH
# =========================================================
@app.route("/")
def index():
    return render_template("index.html")
def generate_student_number():
    return "STU" + ''.join(random.choices(string.ascii_uppercase, k=2)) + ''.join(random.choices(string.digits, k=4))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form["username"],))
        user = cursor.fetchone()

        conn.close()

        if user and check_password_hash(user["password"], request.form["password"]):
            session["user_id"] = user["id"]
            session["role"] = user["role"]

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
    return redirect(url_for("login"))
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
# DASHBOARD
# =========================================================
@app.route("/dashboard")
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    students = cursor.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    teachers = cursor.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
    users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    fees = cursor.execute("SELECT COUNT(*) FROM fees").fetchone()[0]

    conn.close()

    return render_template("dashboard.html",
        total_students=students,
        total_teachers=teachers,
        total_users=users,
        total_fee_records=fees
    )
# =========================================================
# STUDENTS
# =========================================================
@app.route("/students")
def students():
    conn = get_db()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("students.html", students=students)

@app.route("/add_student")
@login_required
@roles_required("admin", "director")
def add_student():
    return render_template("add_student.html", class_options=CLASS_OPTIONS)

@app.route("/save_student", methods=["POST"])
def save_student():
    conn = get_db()
    cursor = conn.cursor()

    try:
        student_number = generate_student_number()

        # STUDENT DETAILS
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

        # GUARDIAN 1
        guardian1_name = request.form.get("guardian1_name")
        guardian1_relationship = request.form.get("guardian1_relationship")
        guardian1_phone = request.form.get("guardian1_phone")
        guardian1_whatsapp = request.form.get("guardian1_whatsapp")
        guardian1_email = request.form.get("guardian1_email")

        # GUARDIAN 2
        guardian2_name = request.form.get("guardian2_name")
        guardian2_relationship = request.form.get("guardian2_relationship")
        guardian2_phone = request.form.get("guardian2_phone")
        guardian2_whatsapp = request.form.get("guardian2_whatsapp")
        guardian2_email = request.form.get("guardian2_email")

        # PARENT LOGIN
        parent_username = request.form.get("parent_username")
        parent_password = request.form.get("parent_password")

        if not parent_username:
            parent_username = guardian1_phone

        if not parent_password:
            parent_password = generate_password()

        hashed_password = generate_password_hash(parent_password)

        # SAVE STUDENT
        cursor.execute("""
            INSERT INTO students (
                student_number, first_name, last_name, birthday, gender,
                enrollment_date, leaving_year, class_name, boarding_status,
                home_address, mailing_address, student_phone, medical_info,
                emergency_contact, guardian1_name, guardian1_relationship,
                guardian1_phone, guardian1_whatsapp, guardian1_email,
                guardian2_name, guardian2_relationship, guardian2_phone,
                guardian2_whatsapp, guardian2_email
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student_number, first_name, last_name, birthday, gender,
            enrollment_date, leaving_year, class_name, boarding_status,
            home_address, mailing_address, student_phone, medical_info,
            emergency_contact, guardian1_name, guardian1_relationship,
            guardian1_phone, guardian1_whatsapp, guardian1_email,
            guardian2_name, guardian2_relationship, guardian2_phone,
            guardian2_whatsapp, guardian2_email
        ))

        student_id = cursor.lastrowid

        # CREATE PARENT USER
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

        # SAVE GUARDIAN 1
        cursor.execute("""
            INSERT INTO guardians (
                student_id, parent_user_id, full_name, relationship, phone, whatsapp, email
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            student_id, parent_user_id, guardian1_name, guardian1_relationship,
            guardian1_phone, guardian1_whatsapp, guardian1_email
        ))

        # SAVE GUARDIAN 2
        if guardian2_name or guardian2_phone:
            cursor.execute("""
                INSERT INTO guardians (
                    student_id, parent_user_id, full_name, relationship, phone, whatsapp, email
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                student_id, parent_user_id, guardian2_name, guardian2_relationship,
                guardian2_phone, guardian2_whatsapp, guardian2_email
            ))

        # TERM FEES
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

                cursor.execute("""
                    INSERT INTO fees (
                        student_id, term_name, amount, paid_amount, balance, status, due_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    student_id, term_name, amount, paid_amount, balance, status, due_date
                ))

        conn.commit()

        flash(
            f"Student registered successfully. Student Number: {student_number}. Parent Username: {parent_username}. Password: {parent_password}",
            "success"
        )
        return redirect(url_for("students"))

    except Exception as e:
        conn.rollback()
        flash(f"Error saving student: {str(e)}", "danger")
        return redirect(url_for("add_student"))

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
    conn = get_db()
    students = conn.execute("SELECT * FROM students WHERE class_name = ?", (class_name,)).fetchall()
    conn.close()
    return render_template("class_students.html", students=students, class_name=class_name)

# =========================================================
# TEACHERS
# =========================================================
@app.route("/teachers")
def teachers():
    conn = get_db()
    teachers = conn.execute("SELECT * FROM teachers").fetchall()
    conn.close()
    return render_template("teachers.html", teachers=teachers)

@app.route("/teacher_registration", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def teacher_registration():
    if request.method == "POST":
        conn = get_db()
        cursor = conn.cursor()

        name = request.form["full_name"]
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        cursor.execute("INSERT INTO users (full_name, username, password, role) VALUES (?, ?, ?, ?)",
                       (name, username, password, "teacher"))

        user_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO teachers (user_id, teacher_id, full_name, phone, email)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, generate_teacher_id(), name, request.form["phone"], request.form["email"]))

        conn.commit()
        conn.close()

        return redirect(url_for("teachers"))

    return render_template("teacher_register.html")

# =========================================================
# SIMPLE PAGES (NO LOGIC)
# =========================================================
@app.route("/subjects")
@login_required
@roles_required("admin", "director", "teacher")
def subjects():
    return render_template("subjects.html")

@app.route("/assign_subject")
def assign_subject():
    return render_template("assign_subject.html")

@app.route("/assign_teacher")
def assign_teacher():
    return render_template("assign_teacher.html")

@app.route("/assign_parent")
def assign_parent():
    return render_template("assign_parent.html")

@app.route("/attendance")
@login_required
@roles_required("admin", "director", "teacher")
def attendance():
    return render_template("attendance.html", class_options=CLASS_OPTIONS)
   
@app.route("/enter_result")
@login_required
@roles_required("admin", "director", "teacher")
def enter_result():
    return render_template("enter_result.html", class_options=CLASS_OPTIONS)

@app.route("/results")
@login_required
@roles_required("admin", "director", "teacher")
def results():
    return render_template("results.html")

@app.route("/fees")
@login_required
@roles_required("admin", "director")
def fees():
    conn = get_db()
    data = conn.execute("SELECT * FROM fees").fetchall()
    conn.close()
    return render_template("fees.html", fee_records=data)

@app.route("/users")
@login_required
@roles_required("admin", "director")
def users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template("users.html", users=users)

@app.route("/add_user")
def add_user():
    return render_template("add_user.html")

@app.route("/generate_fees")
def generate_fees():
    return render_template("generate_fees.html")

@app.route("/student_profile/<int:id>")
def student_profile(id):
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("student_profile.html", student=student)

@app.route("/edit_student/<int:id>")
def edit_student(id):
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("edit_student.html", student=student, class_options=CLASS_OPTIONS)

@app.route("/parent_dashboard")
@login_required
@roles_required("parent")
def parent_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.*
        FROM students s
        JOIN guardians g ON s.id = g.student_id
        WHERE g.parent_user_id = ?
        LIMIT 1
    """, (session["user_id"],))

    student = cursor.fetchone()
    conn.close()

    return render_template("parent_dashboard.html", student=student)

@app.route("/parent/fees")
@login_required
@roles_required("parent")
def parent_fees():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT f.*
        FROM fees f
        JOIN guardians g ON f.student_id = g.student_id
        WHERE g.parent_user_id = ?
    """, (session["user_id"],))

    fee_records = cursor.fetchall()
    conn.close()

    return render_template("parent_fees.html", fee_records=fee_records)

@app.route("/parent/results")
@login_required
@roles_required("parent")
def parent_results():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*
        FROM results r
        JOIN guardians g ON r.student_id = g.student_id
        WHERE g.parent_user_id = ?
    """, (session["user_id"],))

    result_records = cursor.fetchall()
    conn.close()

    return render_template("parent_results.html", result_records=result_records)
@app.route("/parent/assignments")
@login_required
@roles_required("parent")
def parent_assignments():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.class_name
        FROM students s
        JOIN guardians g ON s.id = g.student_id
        WHERE g.parent_user_id = ?
        LIMIT 1
    """, (session["user_id"],))

    student = cursor.fetchone()

    assignments = []
    if student:
        cursor.execute("""
            SELECT *
            FROM assignments
            WHERE class_name = ?
        """, (student["class_name"],))
        assignments = cursor.fetchall()

    conn.close()

    return render_template("parent_assignments.html", assignments=assignments, student=student)

@app.route("/teacher_dashboard")
def teacher_dashboard():
    return render_template("teacher_dashboard.html")

@app.route("/set_password")
def set_password():
    return render_template("set_password.html")
@app.route("/assignments")
@login_required
@roles_required("admin", "director", "teacher")
def assignments():
    return render_template("assignments.html")
@app.route("/add_assignment")
@login_required
@roles_required("admin", "director", "teacher")
def add_assignment():
    return render_template("add_assignment.html")

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    ensure_tables()
    app.run(debug=True)