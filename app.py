from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import random
import string
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "school-secret-key"

# =========================================================
# FIXED CLASS LIST
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
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    else:
        conn = sqlite3.connect("school.db")
        conn.row_factory = sqlite3.Row

    return conn


def get_columns(table_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row["name"] for row in cursor.fetchall()]
    conn.close()
    return columns


def column_exists(table_name, column_name):
    return column_name in get_columns(table_name)


def add_column_if_missing(table_name, column_name, column_type):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row["name"] for row in cursor.fetchall()]
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            conn.commit()
    finally:
        conn.close()


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

    # Expand older tables to match the current app features
    student_columns = [
        ("birthday", "TEXT"),
        ("gender", "TEXT"),
        ("enrollment_date", "TEXT"),
        ("leaving_year", "TEXT"),
        ("home_address", "TEXT"),
        ("mailing_address", "TEXT"),
        ("student_phone", "TEXT"),
        ("medical_info", "TEXT"),
        ("emergency_contact", "TEXT"),
        ("guardian1_relationship", "TEXT"),
        ("guardian1_whatsapp", "TEXT"),
        ("guardian1_email", "TEXT"),
        ("guardian2_name", "TEXT"),
        ("guardian2_relationship", "TEXT"),
        ("guardian2_phone", "TEXT"),
        ("guardian2_whatsapp", "TEXT"),
        ("guardian2_email", "TEXT"),
        ("current_status", "TEXT"),
    ]
    result_columns = [
        ("class_name", "TEXT"),
        ("subject", "TEXT"),
        ("term", "TEXT"),
        ("marks", "REAL"),
        ("grade", "TEXT"),
    ]

    for column_name, column_type in result_columns:
        add_column_if_missing("results", column_name, column_type)

    guardian_columns = [
        ("relationship", "TEXT"),
        ("whatsapp", "TEXT"),
        ("email", "TEXT"),
    ]
    attendance_columns = [
        ("class_name", "TEXT"),
        ("date", "TEXT"),
        ("status", "TEXT"),
    ]
    assignment_columns = [
        ("class_name", "TEXT"),
        ("subject", "TEXT"),
        ("title", "TEXT"),
        ("description", "TEXT"),
        ("due_date", "TEXT"),
        ("created_by", "TEXT"),
    ]
    fee_payment_columns = [
        ("payment_date", "TEXT"),
        ("amount_paid", "REAL"),
        ("receipt_number", "TEXT"),
    ]
    for column_name, column_type in fee_payment_columns:
        add_column_if_missing("fee_payments", column_name, column_type)

    for column_name, column_type in assignment_columns:
        add_column_if_missing("assignments", column_name, column_type)
    
    for column_name, column_type in attendance_columns:
        add_column_if_missing("attendance", column_name, column_type)
    
    fee_columns = [
        ("term_name", "TEXT"),
    ]
    teacher_assignment_columns = [
        ("class_name", "TEXT"),
        ("subject", "TEXT"),
    ]
    for column_name, column_type in teacher_assignment_columns:
        add_column_if_missing("teacher_assignments", column_name, column_type)

    for column_name, column_type in student_columns:
        add_column_if_missing("students", column_name, column_type)

    for column_name, column_type in guardian_columns:
        add_column_if_missing("guardians", column_name, column_type)

    for column_name, column_type in fee_columns:
        add_column_if_missing("fees", column_name, column_type)


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
def is_postgres():
    return os.environ.get("DATABASE_URL") is not None


def run_query(query_sqlite, query_postgres, params=(), fetchone=False, fetchall=False, commit=False):
    db = get_db()

    if is_postgres():
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query_postgres, params)

        result = None
        if fetchone:
            result = cur.fetchone()
        elif fetchall:
            result = cur.fetchall()

        if commit:
            db.commit()

        cur.close()
        return result
    else:
        cur = db.execute(query_sqlite, params)

        result = None
        if fetchone:
            result = cur.fetchone()
        elif fetchall:
            result = cur.fetchall()

        if commit:
            db.commit()

        return result
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = %s",
            (request.form["username"],)
        )
        user = cursor.fetchone()
        conn.close()

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
    conn = get_db()
    cursor = conn.cursor()

    total_students = cursor.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_teachers = cursor.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
    total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_fee_records = cursor.execute("SELECT COUNT(*) FROM fees").fetchone()[0]

    conn.close()

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
    conn = get_db()
    cursor = conn.cursor()

    search = request.args.get("search", "").strip()

    query = "SELECT * FROM students"
    params = []

    if search:
        query += """
            WHERE first_name LIKE %s
            OR last_name LIKE %s
            OR student_number LIKE %s
            OR class_name LIKE %s
        """
        like_search = f"%{search}%"
        params = [like_search, like_search, like_search, like_search]

    query += " ORDER BY class_name, first_name, last_name"

    all_students = cursor.execute(query, params).fetchall()
    conn.close()

    grouped_students = {}
    for student in all_students:
        class_name = student["class_name"] or "No Class Assigned"
        if class_name not in grouped_students:
            grouped_students[class_name] = []
        grouped_students[class_name].append(student)

    return render_template(
        "students.html",
        grouped_students=grouped_students,
        search=search
    )

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
        current_status = request.form.get("current_status")

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

        # PARENT LOGIN PLACEHOLDER ACCOUNT
        parent_username = request.form.get("parent_username")
        if not parent_username:
            parent_username = guardian1_phone

        temporary_password = generate_password()
        hashed_password = generate_password_hash(temporary_password)

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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

        cursor.execute("""
            INSERT INTO users (full_name, username, password, role)
            VALUES (%s, %s, %s, %s)
        """, (
            guardian1_name,
            parent_username,
            hashed_password,
            "parent"
        ))
        parent_user_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO guardians (
                student_id, parent_user_id, full_name, relationship, phone, whatsapp, email
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            parent_user_id,
            guardian1_name,
            guardian1_relationship,
            guardian1_phone,
            guardian1_whatsapp,
            guardian1_email
        ))

        if guardian2_name or guardian2_phone:
            cursor.execute("""
                INSERT INTO guardians (
                    student_id, parent_user_id, full_name, relationship, phone, whatsapp, email
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
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

                cursor.execute("""
                    INSERT INTO fees (
                        student_id, term_name, amount, paid_amount, balance, status, due_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    student_id,
                    term_name,
                    amount,
                    paid_amount,
                    balance,
                    status,
                    due_date
                ))

        conn.commit()

        setup_link = url_for("parent_setup", _external=True)
        flash(
            f"Student registered successfully. Student Number: {student_number}. Parent setup link: {setup_link}",
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
    conn = get_db()
    cursor = conn.cursor()

    student = cursor.execute(
        "SELECT * FROM students WHERE id = %s",
        (id,)
    ).fetchone()

    guardians = cursor.execute(
        "SELECT * FROM guardians WHERE student_id = %s",
        (id,)
    ).fetchall()

    fees = cursor.execute(
        "SELECT * FROM fees WHERE student_id = %s ORDER BY term_name",
        (id,)
    ).fetchall()

    try:
        results = cursor.execute(
            "SELECT * FROM results WHERE student_id = %s ORDER BY term, subject",
            (id,)
        ).fetchall()
    except Exception:
        results = []

    try:
        attendance_records = cursor.execute(
            "SELECT * FROM attendance WHERE student_id = %s ORDER BY date DESC",
            (id,)
        ).fetchall()
    except Exception:
        attendance_records = []

    conn.close()

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
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id = %s", (id,)).fetchone()
    conn.close()
    return render_template("edit_student.html", student=student, class_options=CLASS_OPTIONS)
@app.route("/update_student/<int:id>", methods=["POST"])
@login_required
@roles_required("admin", "director")
def update_student(id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
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
        """, (
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
    conn = get_db()
    class_list = conn.execute(
        "SELECT * FROM students WHERE class_name = %s ORDER BY first_name, last_name",
        (class_name,)
    ).fetchall()
    conn.close()
    return render_template("class_students.html", students=class_list, class_name=class_name)


# =========================================================
# TEACHERS
# =========================================================
@app.route("/teachers")
@login_required
@roles_required("admin", "director")
def teachers():
    conn = get_db()
    teacher_list = conn.execute("SELECT * FROM teachers ORDER BY full_name").fetchall()
    conn.close()
    return render_template("teachers.html", teachers=teacher_list)


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

        cursor.execute("""
            INSERT INTO users (full_name, username, password, role)
            VALUES (%s, %s, %s, %s)
        """, (name, username, password, "teacher"))

        user_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO teachers (user_id, teacher_id, full_name, phone, email)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            user_id,
            generate_teacher_id(),
            name,
            request.form.get("phone"),
            request.form.get("email")
        ))

        conn.commit()
        conn.close()

        flash("Teacher registered successfully.", "success")
        return redirect(url_for("teachers"))

    return render_template("teacher_register.html")


@app.route("/teacher_dashboard")
@login_required
@roles_required("teacher")
def teacher_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    teacher = cursor.execute("""
        SELECT * FROM teachers
        WHERE user_id = %s
        LIMIT 1
    """, (session["user_id"],)).fetchone()

    assignments = []
    if teacher:
        assignments = cursor.execute("""
            SELECT *
            FROM teacher_assignments
            WHERE teacher_id = %s
            ORDER BY class_name, subject
        """, (teacher["id"],)).fetchall()

    conn.close()

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        assignments=assignments
    )

# =========================================================
# FEES / USERS
# =========================================================
@app.route("/fees")
@login_required
@roles_required("admin", "director")
def fees():
    conn = get_db()
    cursor = conn.cursor()

    search = request.args.get("search", "").strip()

    query = """
        SELECT 
            f.*,
            s.first_name,
            s.last_name,
            s.student_number,
            s.class_name
        FROM fees f
        JOIN students s ON f.student_id = s.id
    """

    params = []

    if search:
        query += """
            WHERE
                s.first_name LIKE %s
                OR s.last_name LIKE %s
                OR s.student_number LIKE %s
        """
        like_search = f"%{search}%"
        params.extend([like_search, like_search, like_search])

    query += " ORDER BY s.class_name, s.first_name, s.last_name, f.term_name"

    cursor.execute(query, params)
    fee_records = cursor.fetchall()

    conn.close()
    return render_template("fees.html", fee_records=fee_records, search=search)

@app.route("/update_fee/<int:fee_id>", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def update_fee(fee_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
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
    fee = cursor.fetchone()

    if not fee:
        conn.close()
        flash("Fee record not found.", "danger")
        return redirect(url_for("fees"))

    if request.method == "POST":
        additional_payment = request.form.get("additional_payment", 0)

        try:
            additional_payment = float(additional_payment or 0)
        except:
            additional_payment = 0

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

        cursor.execute("""
            UPDATE fees
            SET paid_amount = %s, balance = %s, status = %s
            WHERE id = %s
        """, (new_paid_amount, new_balance, status, fee_id))

        conn.commit()
        conn.close()

        flash("Fee payment updated successfully.", "success")
        return redirect(url_for("fees"))

    conn.close()
    return render_template("update_fee.html", fee=fee)

@app.route("/users")
@login_required
@roles_required("admin", "director")
def users():
    conn = get_db()
    user_list = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template("users.html", users=user_list)


@app.route("/add_user")
@login_required
@roles_required("admin", "director")
def add_user():
    return render_template("add_user.html")


@app.route("/generate_fees")
@login_required
@roles_required("admin", "director")
def generate_fees():
    return render_template("generate_fees.html")


# =========================================================
# SIMPLE / PLACEHOLDER PAGES
# =========================================================
@app.route("/subjects")
@login_required
@roles_required("admin", "director", "teacher")
def subjects():
    return render_template("subjects.html")


@app.route("/assign_subject")
@login_required
@roles_required("admin", "director")
def assign_subject():
    return render_template("assign_subject.html")


@app.route("/assign_teacher", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director")
def assign_teacher():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        teacher_id = request.form.get("teacher_id")
        class_name = request.form.get("class_name")
        subject = request.form.get("subject")

        cursor.execute("""
            INSERT INTO teacher_assignments (teacher_id, class_name, subject)
            VALUES (%s, %s, %s)
        """, (teacher_id, class_name, subject))

        conn.commit()
        flash("Teacher assigned successfully.", "success")
        return redirect(url_for("assign_teacher"))

    teachers = cursor.execute("""
        SELECT * FROM teachers ORDER BY full_name
    """).fetchall()

    assignments = cursor.execute("""
        SELECT ta.*, t.full_name
        FROM teacher_assignments ta
        JOIN teachers t ON ta.teacher_id = t.id
        ORDER BY t.full_name, ta.class_name, ta.subject
    """).fetchall()

    conn.close()

    subjects = ["Math", "English", "Science", "History", "Geography", "Biology"]

    return render_template(
        "assign_teacher.html",
        teachers=teachers,
        class_options=CLASS_OPTIONS,
        subjects=subjects,
        assignments=assignments
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
    conn = get_db()
    cursor = conn.cursor()

    selected_class = request.form.get("class_name") if request.method == "POST" else request.args.get("class_name")
    students = []

    if selected_class:
        cursor.execute("""
            SELECT * FROM students
            WHERE class_name = %s
            ORDER BY first_name, last_name
        """, (selected_class,))
        students = cursor.fetchall()

    conn.close()

    return render_template(
        "attendance.html",
        class_options=CLASS_OPTIONS,
        selected_class=selected_class,
        students=students
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

            cursor.execute("""
                INSERT INTO attendance (student_id, class_name, date, status)
                VALUES (%s, %s, %s, %s)
            """, (student_id, class_name, date, status))

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
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.*, s.first_name, s.last_name, s.student_number
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        ORDER BY a.date DESC, s.first_name, s.last_name
    """)
    attendance_records = cursor.fetchall()

    conn.close()

    return render_template("attendance_records.html", attendance_records=attendance_records)


@app.route("/enter_result")
@login_required
@roles_required("admin", "director", "teacher")
def enter_result():
    conn = get_db()
    students = conn.execute(
        "SELECT * FROM students ORDER BY first_name, last_name"
    ).fetchall()
    conn.close()

    subjects = ["Math", "English", "Science", "History", "Geography", "Biology"]

    return render_template(
        "enter_result.html",
        class_options=CLASS_OPTIONS,
        students=students,
        subjects=subjects
    )

@app.route("/save_result", methods=["POST"])
@login_required
@roles_required("admin", "director", "teacher")
def save_result():
    conn = get_db()
    cursor = conn.cursor()

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

    cursor.execute("""
        INSERT INTO results (student_id, class_name, subject, term, marks, grade)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (student_id, class_name, subject, term, marks, grade))

    conn.commit()
    conn.close()

    flash("Result saved successfully.", "success")
    return redirect(url_for("results"))


@app.route("/results")
@login_required
@roles_required("admin", "director", "teacher")
def results():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*, s.first_name, s.last_name, s.student_number
        FROM results r
        JOIN students s ON r.student_id = s.id
        ORDER BY s.first_name, s.last_name, r.subject
    """)
    result_records = cursor.fetchall()

    conn.close()
    return render_template("results.html", result_records=result_records)


@app.route("/assignments")
@login_required
@roles_required("admin", "director", "teacher")
def assignments():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM assignments
        ORDER BY due_date ASC, class_name ASC, subject ASC
    """)
    assignments_list = cursor.fetchall()

    conn.close()
    return render_template("assignments.html", assignments=assignments_list)


@app.route("/add_assignment", methods=["GET", "POST"])
@login_required
@roles_required("admin", "director", "teacher")
def add_assignment():
    if request.method == "POST":
        conn = get_db()
        cursor = conn.cursor()

        class_name = request.form.get("class_name")
        subject = request.form.get("subject")
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        created_by = session.get("full_name")

        cursor.execute("""
            INSERT INTO assignments (class_name, subject, title, description, due_date, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (class_name, subject, title, description, due_date, created_by))

        conn.commit()
        conn.close()

        flash("Assignment added successfully.", "success")
        return redirect(url_for("assignments"))

    subjects = ["Math", "English", "Science", "History", "Geography", "Biology"]
    return render_template(
        "add_assignment.html",
        class_options=CLASS_OPTIONS,
        subjects=subjects
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

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.id
            FROM users u
            JOIN guardians g ON u.id = g.parent_user_id
            JOIN students s ON s.id = g.student_id
            WHERE s.student_number = %s AND g.phone = %s
            LIMIT 1
        """, (student_number, phone))

        user = cursor.fetchone()

        if not user:
            conn.close()
            flash("No matching parent account was found. Check student number and phone number.", "danger")
            return redirect(url_for("parent_setup"))

        hashed_password = generate_password_hash(password)

        cursor.execute("""
            UPDATE users
            SET password = %s
            WHERE id = %s
        """, (hashed_password, user["id"]))

        conn.commit()
        conn.close()

        flash("Password set successfully. You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("parent_setup.html")


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
        WHERE g.parent_user_id = %s
        LIMIT 1
    """, (session["user_id"],))

    student = cursor.fetchone()

    fee_summary = {
        "total_amount": 0,
        "total_paid": 0,
        "total_balance": 0
    }

    if student:
        cursor.execute("""
            SELECT
                COALESCE(SUM(amount), 0) AS total_amount,
                COALESCE(SUM(paid_amount), 0) AS total_paid,
                COALESCE(SUM(balance), 0) AS total_balance
            FROM fees
            WHERE student_id = %s
        """, (student["id"],))
        fee_summary = cursor.fetchone()

    conn.close()

    return render_template(
        "parent_dashboard.html",
        student=student,
        fee_summary=fee_summary
    )

@app.route("/parent_fees")
@login_required
@roles_required("parent")
def parent_fees():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT f.*, s.first_name, s.last_name, s.class_name
        FROM fees f
        JOIN guardians g ON f.student_id = g.student_id
        JOIN students s ON s.id = f.student_id
        WHERE g.parent_user_id = %s
        ORDER BY f.term_name
    """, (session["user_id"],))

    fee_records = cursor.fetchall()
    conn.close()

    return render_template("parent_fees.html", fee_records=fee_records)


@app.route("/parent_results")
@login_required
@roles_required("parent")
def parent_results():
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT r.*, s.first_name, s.last_name
            FROM results r
            JOIN guardians g ON r.student_id = g.student_id
            JOIN students s ON s.id = r.student_id
            WHERE g.parent_user_id = %s
            ORDER BY r.term, r.subject
        """, (session["user_id"],))
        result_records = cursor.fetchall()
    except Exception:
        result_records = []

    conn.close()

    return render_template("parent_results.html", result_records=result_records)


@app.route("/parent_attendance")
@login_required
@roles_required("parent")
def parent_attendance():
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT a.*, s.first_name, s.last_name
            FROM attendance a
            JOIN guardians g ON a.student_id = g.student_id
            JOIN students s ON s.id = a.student_id
            WHERE g.parent_user_id = %s
            ORDER BY a.date DESC
        """, (session["user_id"],))
        attendance_records = cursor.fetchall()
    except Exception:
        attendance_records = []

    conn.close()

    return render_template("parent_attendance.html", attendance_records=attendance_records)


@app.route("/parent_assignments")
@login_required
@roles_required("parent")
def parent_assignments():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.class_name, s.first_name, s.last_name
        FROM students s
        JOIN guardians g ON s.id = g.student_id
        WHERE g.parent_user_id = %s
        LIMIT 1
    """, (session["user_id"],))

    student = cursor.fetchone()
    assignments_list = []

    if student:
        try:
            cursor.execute("""
                SELECT *
                FROM assignments
                WHERE class_name = %s
                ORDER BY due_date
            """, (student["class_name"],))
            assignments_list = cursor.fetchall()
        except Exception:
            assignments_list = []

    conn.close()

    return render_template(
        "parent_assignments.html",
        assignments=assignments_list,
        student=student
    )
@app.route("/delete_student/<int:id>", methods=["POST"])
@login_required
@roles_required("admin", "director")
def delete_student(id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM fees WHERE student_id = %s", (id,))
        cursor.execute("DELETE FROM guardians WHERE student_id = %s", (id,))
        cursor.execute("DELETE FROM students WHERE id = %s", (id,))

        conn.commit()
        flash("Student deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting student: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("students"))
@app.route("/delete_teacher/<int:id>", methods=["POST"])
@login_required
@roles_required("admin", "director")
def delete_teacher(id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT user_id FROM teachers WHERE id = %s", (id,))
        teacher = cursor.fetchone()

        if teacher:
            cursor.execute("DELETE FROM teachers WHERE id = %s", (id,))
            cursor.execute("DELETE FROM users WHERE id = %s", (teacher["user_id"],))
            conn.commit()
            flash("Teacher deleted successfully.", "success")
        else:
            flash("Teacher not found.", "danger")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting teacher: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("teachers"))
@app.route("/delete_user/<int:id>", methods=["POST"])
@login_required
@roles_required("admin", "director")
def delete_user(id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (id,))
        conn.commit()
        flash("User deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting user: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for("users"))
# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    ensure_tables()
    app.run(debug=True)