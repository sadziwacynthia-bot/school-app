import os
import sqlite3
import random
import string
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change_this_to_a_real_secret_key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "school.db")


# ---------------------------------
# DATABASE
# ---------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            teacher_id TEXT UNIQUE,
            full_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            subjects TEXT,
            class_teacher_for TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_number TEXT UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS parents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE,
            password TEXT,
            relationship TEXT,
            phone TEXT,
            whatsapp TEXT,
            email TEXT,
            parent_code TEXT UNIQUE,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            academic_year TEXT,
            term TEXT,
            amount REAL NOT NULL DEFAULT 0,
            paid_amount REAL NOT NULL DEFAULT 0,
            balance REAL NOT NULL DEFAULT 0,
            status TEXT,
            due_date TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            class_name TEXT,
            term TEXT,
            academic_year TEXT,
            marks REAL,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            class_name TEXT,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            remarks TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    default_classes = [
        "ECD A", "ECD B",
        "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7",
        "Form 1", "Form 2", "Form 3", "Form 4", "Form 5", "Form 6"
    ]

    default_subjects = [
        "Mathematics", "English", "Science", "History", "Geography",
        "Biology", "Chemistry", "Physics", "Agriculture", "Shona", "ICT"
    ]

    for class_name in default_classes:
        cur.execute("INSERT OR IGNORE INTO classes (class_name) VALUES (?)", (class_name,))

    for subject_name in default_subjects:
        cur.execute("INSERT OR IGNORE INTO subjects (subject_name) VALUES (?)", (subject_name,))

    cur.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    admin = cur.fetchone()

    if not admin:
        cur.execute("""
            INSERT INTO users (full_name, username, password, role)
            VALUES (?, ?, ?, ?)
        """, (
            "System Admin",
            "admin",
            generate_password_hash("admin123"),
            "admin"
        ))

    conn.commit()
    conn.close()


# ---------------------------------
# HELPERS
# ---------------------------------
def generate_student_number():
    conn = get_db()
    while True:
        code = "STU" + "".join(random.choices(string.ascii_uppercase, k=2)) + "".join(random.choices(string.digits, k=4))
        existing = conn.execute(
            "SELECT id FROM students WHERE student_number = ?",
            (code,)
        ).fetchone()
        if not existing:
            return code


def generate_teacher_id():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) AS total FROM teachers").fetchone()
    total = row["total"] + 1
    return f"TCH{total:03d}"


def generate_parent_code():
    conn = get_db()
    while True:
        code = "PAR" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        existing = conn.execute(
            "SELECT id FROM parents WHERE parent_code = ?",
            (code,)
        ).fetchone()
        if not existing:
            return code


# ---------------------------------
# AUTH DECORATORS
# ---------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "role" not in session:
                flash("Access denied.", "danger")
                return redirect(url_for("login"))
            if session["role"] not in allowed_roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ---------------------------------
# HOME / AUTH
# ---------------------------------
@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        parent = conn.execute(
            "SELECT * FROM parents WHERE username = ?",
            (username,)
        ).fetchone()

        if parent and parent["password"] and check_password_hash(parent["password"], password):
            session.clear()
            session["user_id"] = parent["id"]
            session["full_name"] = parent["full_name"]
            session["role"] = "parent"
            session["student_id"] = parent["student_id"]
            flash("Parent login successful.", "success")
            return redirect(url_for("parent_dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()

    total_students = conn.execute("SELECT COUNT(*) AS total FROM students").fetchone()["total"]
    total_teachers = conn.execute("SELECT COUNT(*) AS total FROM teachers").fetchone()["total"]
    total_classes = conn.execute("SELECT COUNT(*) AS total FROM classes").fetchone()["total"]
    total_users = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_teachers=total_teachers,
        total_classes=total_classes,
        total_users=total_users
    )


# ---------------------------------
# USERS
# ---------------------------------
@app.route("/users")
@login_required
@roles_required("admin", "director")
def users():
    conn = get_db()
    users_list = conn.execute("SELECT * FROM users ORDER BY full_name").fetchall()
    return render_template("users.html", users=users_list)


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

        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO users (full_name, username, password, role)
                VALUES (?, ?, ?, ?)
            """, (full_name, username, generate_password_hash(password), role))
            conn.commit()
            flash("User added successfully.", "success")
            return redirect(url_for("users"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")

    return render_template("add_user.html")


# ---------------------------------
# TEACHERS
# ---------------------------------
@app.route("/teachers")
@login_required
def teachers():
    conn = get_db()
    teachers_list = conn.execute("SELECT * FROM teachers ORDER BY full_name").fetchall()
    return render_template("teachers.html", teachers=teachers_list)


@app.route("/register_teacher", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def register_teacher():
    conn = get_db()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        subjects = request.form.get("subjects", "").strip()
        class_teacher_for = request.form.get("class_teacher_for", "").strip()

        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (full_name, username, password, role)
                VALUES (?, ?, ?, ?)
            """, (full_name, username, generate_password_hash(password), "teacher"))
            user_id = cur.lastrowid

            cur.execute("""
                INSERT INTO teachers (user_id, teacher_id, full_name, phone, email, subjects, class_teacher_for)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                generate_teacher_id(),
                full_name,
                phone,
                email,
                subjects,
                class_teacher_for
            ))

            conn.commit()
            flash("Teacher registered successfully.", "success")
            return redirect(url_for("teachers"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")

    classes = conn.execute("SELECT class_name FROM classes ORDER BY class_name").fetchall()
    return render_template("teacher_register.html", classes=classes)


# ---------------------------------
# STUDENTS
# ---------------------------------
@app.route("/students")
@login_required
def students():
    if session.get("role") == "parent":
        return redirect(url_for("parent_dashboard"))

    conn = get_db()
    students_list = conn.execute("""
        SELECT * FROM students
        ORDER BY class_name, first_name, last_name
    """).fetchall()
    return render_template("students.html", students=students_list)


@app.route("/add_student")
@login_required
@roles_required("admin", "director")
def add_student():
    conn = get_db()
    classes = conn.execute("SELECT class_name FROM classes ORDER BY class_name").fetchall()
    return render_template("add_student.html", classes=classes)


@app.route("/save_student", methods=["POST"])
@login_required
@roles_required("admin", "director")
def save_student():
    try:
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        if not first_name or not last_name:
            flash("First name and last name are required.", "danger")
            return redirect(url_for("add_student"))

        data = {
            "birthday": request.form.get("birthday", "").strip(),
            "gender": request.form.get("gender", "").strip(),
            "enrollment_date": request.form.get("enrollment_date", "").strip(),
            "leaving_year": request.form.get("leaving_year", "").strip(),
            "class_name": request.form.get("class_name", "").strip(),
            "home_address": request.form.get("home_address", "").strip(),
            "mailing_address": request.form.get("mailing_address", "").strip(),
            "student_phone": request.form.get("student_phone", "").strip(),
            "medical_info": request.form.get("medical_info", "").strip(),
            "emergency_contact": request.form.get("emergency_contact", "").strip(),
            "guardian1_name": request.form.get("guardian1_name", "").strip(),
            "guardian1_relationship": request.form.get("guardian1_relationship", "").strip(),
            "guardian1_phone": request.form.get("guardian1_phone", "").strip(),
            "guardian1_whatsapp": request.form.get("guardian1_whatsapp", "").strip(),
            "guardian1_email": request.form.get("guardian1_email", "").strip(),
            "guardian2_name": request.form.get("guardian2_name", "").strip(),
            "guardian2_relationship": request.form.get("guardian2_relationship", "").strip(),
            "guardian2_phone": request.form.get("guardian2_phone", "").strip(),
            "guardian2_whatsapp": request.form.get("guardian2_whatsapp", "").strip(),
            "guardian2_email": request.form.get("guardian2_email", "").strip(),
        }

        conn = get_db()
        cur = conn.cursor()

        student_number = generate_student_number()

        cur.execute("""
            INSERT INTO students (
                student_number, first_name, last_name, birthday, gender, enrollment_date,
                leaving_year, class_name, home_address, mailing_address, student_phone,
                medical_info, emergency_contact,
                guardian1_name, guardian1_relationship, guardian1_phone, guardian1_whatsapp, guardian1_email,
                guardian2_name, guardian2_relationship, guardian2_phone, guardian2_whatsapp, guardian2_email
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student_number,
            first_name,
            last_name,
            data["birthday"],
            data["gender"],
            data["enrollment_date"],
            data["leaving_year"],
            data["class_name"],
            data["home_address"],
            data["mailing_address"],
            data["student_phone"],
            data["medical_info"],
            data["emergency_contact"],
            data["guardian1_name"],
            data["guardian1_relationship"],
            data["guardian1_phone"],
            data["guardian1_whatsapp"],
            data["guardian1_email"],
            data["guardian2_name"],
            data["guardian2_relationship"],
            data["guardian2_phone"],
            data["guardian2_whatsapp"],
            data["guardian2_email"]
        ))

        student_id = cur.lastrowid

        if data["guardian1_name"]:
            cur.execute("""
                INSERT INTO parents (
                    student_id, full_name, relationship, phone, whatsapp, email, parent_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                student_id,
                data["guardian1_name"],
                data["guardian1_relationship"],
                data["guardian1_phone"],
                data["guardian1_whatsapp"],
                data["guardian1_email"],
                generate_parent_code()
            ))

        if data["guardian2_name"]:
            cur.execute("""
                INSERT INTO parents (
                    student_id, full_name, relationship, phone, whatsapp, email, parent_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                student_id,
                data["guardian2_name"],
                data["guardian2_relationship"],
                data["guardian2_phone"],
                data["guardian2_whatsapp"],
                data["guardian2_email"],
                generate_parent_code()
            ))

        conn.commit()
        flash("Student registered successfully.", "success")
        return redirect(url_for("students"))

    except Exception as e:
        app.logger.exception("Error saving student")
        flash(f"Error saving student: {e}", "danger")
        return redirect(url_for("add_student"))


@app.route("/student/<int:student_id>")
@login_required
def student_profile(student_id):
    if session.get("role") == "parent" and session.get("student_id") != student_id:
        flash("Access denied.", "danger")
        return redirect(url_for("parent_dashboard"))

    conn = get_db()

    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("students"))

    parents = conn.execute("SELECT * FROM parents WHERE student_id = ?", (student_id,)).fetchall()

    fees = conn.execute("""
        SELECT * FROM fees
        WHERE student_id = ?
        ORDER BY academic_year DESC, term
    """, (student_id,)).fetchall()

    results = conn.execute("""
        SELECT results.*, subjects.subject_name
        FROM results
        JOIN subjects ON results.subject_id = subjects.id
        WHERE results.student_id = ?
        ORDER BY academic_year DESC, term, subjects.subject_name
    """, (student_id,)).fetchall()

    attendance_records = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id = ?
        ORDER BY date DESC
    """, (student_id,)).fetchall()

    return render_template(
        "student_profile.html",
        student=student,
        parents=parents,
        fees=fees,
        results=results,
        attendance_records=attendance_records
    )


@app.route("/edit_student/<int:student_id>", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def edit_student(student_id):
    conn = get_db()

    if request.method == "POST":
        data = {key: request.form.get(key, "").strip() for key in request.form.keys()}

        conn.execute("""
            UPDATE students SET
                first_name=?, last_name=?, birthday=?, gender=?, enrollment_date=?, leaving_year=?,
                class_name=?, home_address=?, mailing_address=?, student_phone=?, medical_info=?, emergency_contact=?,
                guardian1_name=?, guardian1_relationship=?, guardian1_phone=?, guardian1_whatsapp=?, guardian1_email=?,
                guardian2_name=?, guardian2_relationship=?, guardian2_phone=?, guardian2_whatsapp=?, guardian2_email=?
            WHERE id=?
        """, (
            data.get("first_name", ""),
            data.get("last_name", ""),
            data.get("birthday", ""),
            data.get("gender", ""),
            data.get("enrollment_date", ""),
            data.get("leaving_year", ""),
            data.get("class_name", ""),
            data.get("home_address", ""),
            data.get("mailing_address", ""),
            data.get("student_phone", ""),
            data.get("medical_info", ""),
            data.get("emergency_contact", ""),
            data.get("guardian1_name", ""),
            data.get("guardian1_relationship", ""),
            data.get("guardian1_phone", ""),
            data.get("guardian1_whatsapp", ""),
            data.get("guardian1_email", ""),
            data.get("guardian2_name", ""),
            data.get("guardian2_relationship", ""),
            data.get("guardian2_phone", ""),
            data.get("guardian2_whatsapp", ""),
            data.get("guardian2_email", ""),
            student_id
        ))
        conn.commit()

        flash("Student updated successfully.", "success")
        return redirect(url_for("student_profile", student_id=student_id))

    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    classes = conn.execute("SELECT class_name FROM classes ORDER BY class_name").fetchall()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("students"))

    return render_template("edit_student.html", student=student, classes=classes)


# ---------------------------------
# PARENTS
# ---------------------------------
@app.route("/parent_dashboard")
@login_required
@roles_required("parent")
def parent_dashboard():
    student_id = session.get("student_id")
    conn = get_db()

    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    results = conn.execute("""
        SELECT results.*, subjects.subject_name
        FROM results
        JOIN subjects ON results.subject_id = subjects.id
        WHERE results.student_id = ?
        ORDER BY academic_year DESC, term, subjects.subject_name
    """, (student_id,)).fetchall()

    fees = conn.execute("""
        SELECT * FROM fees
        WHERE student_id = ?
        ORDER BY academic_year DESC, term
    """, (student_id,)).fetchall()

    attendance_records = conn.execute("""
        SELECT * FROM attendance
        WHERE student_id = ?
        ORDER BY date DESC
    """, (student_id,)).fetchall()

    return render_template(
        "parent_dashboard.html",
        student=student,
        results=results,
        fees=fees,
        attendance_records=attendance_records
    )


@app.route("/parent_setup/<parent_code>", methods=["GET", "POST"])
def parent_setup(parent_code):
    conn = get_db()
    parent = conn.execute("SELECT * FROM parents WHERE parent_code = ?", (parent_code,)).fetchone()

    if not parent:
        flash("Invalid parent setup code.", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("parent_setup", parent_code=parent_code))

        try:
            conn.execute("""
                UPDATE parents
                SET username = ?, password = ?
                WHERE id = ?
            """, (username, generate_password_hash(password), parent["id"]))
            conn.commit()
            flash("Parent account setup successful. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already taken.", "danger")

    return render_template("parent_setup.html", parent=parent)


# ---------------------------------
# CLASSES
# ---------------------------------
@app.route("/classes")
@login_required
def classes():
    conn = get_db()
    class_list = conn.execute("SELECT class_name FROM classes ORDER BY class_name").fetchall()
    return render_template("classes.html", classes=class_list)


@app.route("/class/<class_name>/students")
@login_required
def class_students(class_name):
    conn = get_db()
    students_list = conn.execute("""
        SELECT * FROM students
        WHERE class_name = ?
        ORDER BY first_name, last_name
    """, (class_name,)).fetchall()
    return render_template("class_students.html", students=students_list, class_name=class_name)


# ---------------------------------
# FEES
# ---------------------------------
@app.route("/fees")
@login_required
def fees():
    conn = get_db()
    classes_list = conn.execute("SELECT class_name FROM classes ORDER BY class_name").fetchall()
    return render_template("fees.html", classes=classes_list)


@app.route("/fees/<class_name>")
@login_required
def fees_by_class(class_name):
    conn = get_db()
    fee_records = conn.execute("""
        SELECT fees.*, students.first_name, students.last_name, students.student_number
        FROM fees
        JOIN students ON fees.student_id = students.id
        WHERE students.class_name = ?
        ORDER BY students.first_name, students.last_name
    """, (class_name,)).fetchall()
    return render_template("fees_by_class.html", fee_records=fee_records, class_name=class_name)


@app.route("/add_fee", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def add_fee():
    conn = get_db()

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        academic_year = request.form.get("academic_year", "").strip()
        term = request.form.get("term", "").strip()
        due_date = request.form.get("due_date", "").strip()

        try:
            amount = float(request.form.get("amount", 0) or 0)
            paid_amount = float(request.form.get("paid_amount", 0) or 0)
        except ValueError:
            flash("Amount fields must be numbers.", "danger")
            return redirect(url_for("add_fee"))

        balance = amount - paid_amount
        status = "Paid" if balance <= 0 else "Pending"

        conn.execute("""
            INSERT INTO fees (student_id, academic_year, term, amount, paid_amount, balance, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_id, academic_year, term, amount, paid_amount, balance, status, due_date))
        conn.commit()

        flash("Fee added successfully.", "success")
        return redirect(url_for("students"))

    students_list = conn.execute("""
        SELECT id, first_name, last_name, student_number
        FROM students
        ORDER BY first_name, last_name
    """).fetchall()

    return render_template("add_fee.html", students=students_list)


# ---------------------------------
# RESULTS
# ---------------------------------
@app.route("/results", methods=["GET", "POST"])
@login_required
def results():
    conn = get_db()

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        subject_id = request.form.get("subject_id", "").strip()
        class_name = request.form.get("class_name", "").strip()
        term = request.form.get("term", "").strip()
        academic_year = request.form.get("academic_year", "").strip()
        marks = request.form.get("marks", "").strip()

        if not student_id or not subject_id or not class_name or not term or not academic_year or not marks:
            flash("Please fill in all result fields.", "danger")
            return redirect(url_for("results"))

        try:
            conn.execute("""
                INSERT INTO results (student_id, subject_id, class_name, term, academic_year, marks)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (student_id, subject_id, class_name, term, academic_year, marks))
            conn.commit()
            flash("Result saved successfully.", "success")
        except Exception as e:
            app.logger.exception("Error saving result")
            flash(f"Error saving result: {e}", "danger")

        return redirect(url_for("results"))

    students_list = conn.execute("""
        SELECT id, first_name, last_name, student_number, class_name
        FROM students
        ORDER BY first_name, last_name
    """).fetchall()

    subjects_list = conn.execute("""
        SELECT * FROM subjects
        ORDER BY subject_name
    """).fetchall()

    classes_list = conn.execute("""
        SELECT class_name FROM classes
        ORDER BY class_name
    """).fetchall()

    results_list = conn.execute("""
        SELECT results.*, students.first_name, students.last_name, subjects.subject_name
        FROM results
        JOIN students ON results.student_id = students.id
        JOIN subjects ON results.subject_id = subjects.id
        ORDER BY results.academic_year DESC, results.term, students.first_name
    """).fetchall()

    return render_template(
        "results.html",
        students=students_list,
        subjects=subjects_list,
        classes=classes_list,
        results_list=results_list
    )

# ---------------------------------
# ATTENDANCE
# ---------------------------------
@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    conn = get_db()

    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        class_name = request.form.get("class_name", "").strip()
        date = request.form.get("date", "").strip()
        status = request.form.get("status", "").strip()
        remarks = request.form.get("remarks", "").strip()

        conn.execute("""
            INSERT INTO attendance (student_id, class_name, date, status, remarks)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, class_name, date, status, remarks))
        conn.commit()

        flash("Attendance saved successfully.", "success")
        return redirect(url_for("attendance"))

    students_list = conn.execute("""
        SELECT id, first_name, last_name, class_name
        FROM students
        ORDER BY class_name, first_name
    """).fetchall()

    classes_list = conn.execute("SELECT class_name FROM classes ORDER BY class_name").fetchall()

    attendance_records = conn.execute("""
        SELECT attendance.*, students.first_name, students.last_name
        FROM attendance
        JOIN students ON attendance.student_id = students.id
        ORDER BY attendance.date DESC
    """).fetchall()

    return render_template(
        "attendance.html",
        students=students_list,
        classes=classes_list,
        attendance_records=attendance_records
    )


# ---------------------------------
# SETUP
# ---------------------------------
@app.route("/setup")
def setup():
    init_db()
    return "Database setup complete."


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)