from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import random
import string

app = Flask(__name__)
app.secret_key = "school_secret_key"


# DATABASE CONNECTION
def get_db():
    
    conn = sqlite3.connect("school.db")
    conn.row_factory = sqlite3.Row
    return conn


# GENERATE STUDENT NUMBER
def generate_student_number():
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=4))
    return f"STU{letters}{numbers}"
# LOGIN REQUIRED
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ROLE PROTECTION
def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            if "role" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))

            if session["role"] not in allowed_roles:
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for("dashboard"))

            return f(*args, **kwargs)

        return decorated_function
    return decorator
# LOGIN REQUIRED
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ROLE PROTECTION
def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            if "role" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))

            if session["role"] not in allowed_roles:
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for("dashboard"))

            return f(*args, **kwargs)

        return decorated_function
    return decorator
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()

        user = cursor.execute("""
            SELECT *
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "success")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))

@app.route("/users")
@login_required
@roles_required("director", "admin")
def users():
    conn = get_db()
    cursor = conn.cursor()

    user_records = cursor.execute("""
        SELECT id, full_name, username, role
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()
    return render_template("users.html", user_records=user_records)

@app.route("/add_user", methods=["GET", "POST"])
@login_required
@roles_required("director", "admin")
def add_user():
    if request.method == "POST":
        full_name = request.form["full_name"]
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()

        existing_user = cursor.execute("""
            SELECT id
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        if existing_user:
            conn.close()
            flash("Username already exists. Please choose another one.", "success")
            return redirect(url_for("add_user"))

        cursor.execute("""
            INSERT INTO users (full_name, username, password, role)
            VALUES (?, ?, ?, ?)
        """, (full_name, username, hashed_password, role))

        conn.commit()
        conn.close()

        flash("User created successfully!", "success")
        return redirect(url_for("users"))

    return render_template("add_user.html")

# DASHBOARD
@app.route("/")
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    total_students = cursor.execute("""
        SELECT COUNT(*) FROM students
    """).fetchone()[0]

    total_classes = cursor.execute("""
        SELECT COUNT(DISTINCT class_name)
        FROM students
        WHERE class_name IS NOT NULL AND class_name != ''
    """).fetchone()[0]

    total_boys = cursor.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE gender = 'Male'
    """).fetchone()[0]

    total_girls = cursor.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE gender = 'Female'
    """).fetchone()[0]

    total_fees = cursor.execute("""
        SELECT COALESCE(SUM(total_fee), 0)
        FROM fees
    """).fetchone()[0]

    total_paid = cursor.execute("""
        SELECT COALESCE(SUM(total_paid), 0)
        FROM fees
    """).fetchone()[0]

    total_balance = cursor.execute("""
        SELECT COALESCE(SUM(total_balance), 0)
        FROM fees
    """).fetchone()[0]

    recent_students = cursor.execute("""
        SELECT student_number, first_name, last_name, class_name
        FROM students
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    class_summary = cursor.execute("""
        SELECT class_name, COUNT(*) as total_students
        FROM students
        WHERE class_name IS NOT NULL AND class_name != ''
        GROUP BY class_name
        ORDER BY class_name ASC
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_classes=total_classes,
        total_boys=total_boys,
        total_girls=total_girls,
        total_fees=total_fees,
        total_paid=total_paid,
        total_balance=total_balance,
        recent_students=recent_students,
        class_summary=class_summary
    )

# ADD STUDENT PAGE
@app.route("/add_student")
@login_required
@roles_required("director", "admin")
def add_student_page():
    return render_template("add_student.html")


# SAVE STUDENT
@app.route("/save_student", methods=["POST"])
def save_student():
    conn = get_db()
    cursor = conn.cursor()

    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    birthday = request.form["birthday"]
    gender = request.form["gender"]
    enrollment_date = request.form["enrollment_date"]
    leaving_year = request.form["leaving_year"]
    class_name = request.form["class_name"]
    home_address = request.form["home_address"]
    mailing_address = request.form["mailing_address"]
    student_phone = request.form["student_phone"]
    medical_info = request.form["medical_info"]
    emergency_contact = request.form["emergency_contact"]
    guardian1_name = request.form["guardian1_name"]
    guardian1_relationship = request.form["guardian1_relationship"]
    guardian1_phone = request.form["guardian1_phone"]
    guardian1_whatsapp = request.form["guardian1_whatsapp"]
    guardian1_email = request.form["guardian1_email"]
    guardian2_name = request.form["guardian2_name"]
    guardian2_relationship = request.form["guardian2_relationship"]
    guardian2_phone = request.form["guardian2_phone"]
    guardian2_whatsapp = request.form["guardian2_whatsapp"]
    guardian2_email = request.form["guardian2_email"]

    academic_year = request.form["academic_year"]
    term1_fee = float(request.form["term1_fee"])
    term2_fee = float(request.form["term2_fee"])
    term3_fee = float(request.form["term3_fee"])

    student_number = generate_student_number()

    cursor.execute("""
        INSERT INTO students (
            student_number, first_name, last_name, birthday, gender,
            enrollment_date, leaving_year, class_name, home_address,
            mailing_address, student_phone, medical_info, emergency_contact,
            guardian1_name, guardian1_relationship, guardian1_phone,
            guardian1_whatsapp, guardian1_email, guardian2_name,
            guardian2_relationship, guardian2_phone, guardian2_whatsapp,
            guardian2_email
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_number, first_name, last_name, birthday, gender,
        enrollment_date, leaving_year, class_name, home_address,
        mailing_address, student_phone, medical_info, emergency_contact,
        guardian1_name, guardian1_relationship, guardian1_phone,
        guardian1_whatsapp, guardian1_email, guardian2_name,
        guardian2_relationship, guardian2_phone, guardian2_whatsapp,
        guardian2_email
    ))

    student_id = cursor.lastrowid

    term1_paid = 0
    term1_balance = term1_fee

    term2_paid = 0
    term2_balance = term2_fee

    term3_paid = 0
    term3_balance = term3_fee

    total_fee = term1_fee + term2_fee + term3_fee
    total_paid = 0
    total_balance = total_fee

    cursor.execute("""
        INSERT INTO fees (
            student_id, academic_year,
            term1_fee, term1_paid, term1_balance,
            term2_fee, term2_paid, term2_balance,
            term3_fee, term3_paid, term3_balance,
            total_fee, total_paid, total_balance
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id, academic_year,
        term1_fee, term1_paid, term1_balance,
        term2_fee, term2_paid, term2_balance,
        term3_fee, term3_paid, term3_balance,
        total_fee, total_paid, total_balance
    ))

    conn.commit()
    conn.close()

    flash("Student registered successfully!", "success")
    return redirect("/students")


# VIEW STUDENTS
@app.route("/students")
def students():
    conn = get_db()
    cursor = conn.cursor()

    search = request.args.get("search", "").strip()

    if search:
        student_records = cursor.execute("""
            SELECT *
            FROM students
            WHERE first_name LIKE ? OR last_name LIKE ? OR student_number LIKE ? OR class_name LIKE ?
            ORDER BY id DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        student_records = cursor.execute("""
            SELECT *
            FROM students
            ORDER BY id DESC
        """).fetchall()

    conn.close()
    return render_template("students.html", student_records=student_records, search=search)

@app.route("/student/<int:student_id>")
@login_required
def student_profile(student_id):
    conn = get_db()
    cursor = conn.cursor()

    # Directors and admins can open any student
    if session["role"] in ["director", "admin"]:
        allowed = True

    # Teachers can open students only in their classes
    elif session["role"] == "teacher":
        teacher_class = cursor.execute("""
            SELECT 1
            FROM teacher_classes tc
            JOIN students s ON tc.class_name = s.class_name
            WHERE tc.user_id = ? AND s.id = ?
        """, (session["user_id"], student_id)).fetchone()
        allowed = teacher_class is not None

    # Parents can open only linked students
    elif session["role"] == "parent":
        parent_link = cursor.execute("""
            SELECT 1
            FROM parent_students
            WHERE user_id = ? AND student_id = ?
        """, (session["user_id"], student_id)).fetchone()
        allowed = parent_link is not None

    else:
        allowed = False

    if not allowed:
        conn.close()
        flash("You do not have permission to view this student.", "success")
        return redirect(url_for("dashboard"))

    student = cursor.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (student_id,)).fetchone()

    fee_records = cursor.execute("""
        SELECT *
        FROM fees
        WHERE student_id = ?
        ORDER BY academic_year DESC
    """, (student_id,)).fetchall()

    attendance_records = cursor.execute("""
        SELECT *
        FROM attendance
        WHERE student_id = ?
        ORDER BY date DESC
    """, (student_id,)).fetchall()

    conn.close()

    return render_template(
        "student_profile.html",
        student=student,
        fee_records=fee_records,
        attendance_records=attendance_records
    )

@app.route("/edit_student/<int:student_id>")
def edit_student(student_id):
    conn = get_db()
    cursor = conn.cursor()

    student = cursor.execute("""
        SELECT *
        FROM students
        WHERE id = ?
    """, (student_id,)).fetchone()

    conn.close()

    return render_template("edit_student.html", student=student)
@app.route("/update_student/<int:student_id>", methods=["POST"])
def update_student(student_id):
    conn = get_db()
    cursor = conn.cursor()

    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    birthday = request.form["birthday"]
    gender = request.form["gender"]
    enrollment_date = request.form["enrollment_date"]
    leaving_year = request.form["leaving_year"]
    class_name = request.form["class_name"]
    home_address = request.form["home_address"]
    mailing_address = request.form["mailing_address"]
    student_phone = request.form["student_phone"]
    medical_info = request.form["medical_info"]
    emergency_contact = request.form["emergency_contact"]
    guardian1_name = request.form["guardian1_name"]
    guardian1_relationship = request.form["guardian1_relationship"]
    guardian1_phone = request.form["guardian1_phone"]
    guardian1_whatsapp = request.form["guardian1_whatsapp"]
    guardian1_email = request.form["guardian1_email"]
    guardian2_name = request.form["guardian2_name"]
    guardian2_relationship = request.form["guardian2_relationship"]
    guardian2_phone = request.form["guardian2_phone"]
    guardian2_whatsapp = request.form["guardian2_whatsapp"]
    guardian2_email = request.form["guardian2_email"]

    cursor.execute("""
        UPDATE students
        SET
            first_name = ?,
            last_name = ?,
            birthday = ?,
            gender = ?,
            enrollment_date = ?,
            leaving_year = ?,
            class_name = ?,
            home_address = ?,
            mailing_address = ?,
            student_phone = ?,
            medical_info = ?,
            emergency_contact = ?,
            guardian1_name = ?,
            guardian1_relationship = ?,
            guardian1_phone = ?,
            guardian1_whatsapp = ?,
            guardian1_email = ?,
            guardian2_name = ?,
            guardian2_relationship = ?,
            guardian2_phone = ?,
            guardian2_whatsapp = ?,
            guardian2_email = ?
        WHERE id = ?
    """, (
        first_name, last_name, birthday, gender, enrollment_date,
        leaving_year, class_name, home_address, mailing_address,
        student_phone, medical_info, emergency_contact,
        guardian1_name, guardian1_relationship, guardian1_phone,
        guardian1_whatsapp, guardian1_email,
        guardian2_name, guardian2_relationship, guardian2_phone,
        guardian2_whatsapp, guardian2_email,
        student_id
    ))

    conn.commit()
    conn.close()

    flash("Student updated successfully!", "success")
    return redirect(f"/student/{student_id}")

# CLASSES PAGE
@app.route("/classes")
@login_required
@roles_required("director", "admin", "teacher")
def classes():
    conn = get_db()
    cursor = conn.cursor()

    if session["role"] in ["director", "admin"]:
        class_records = cursor.execute("""
            SELECT class_name, COUNT(*) as total_students
            FROM students
            WHERE class_name IS NOT NULL AND class_name != ''
            GROUP BY class_name
            ORDER BY class_name ASC
        """).fetchall()
    else:
        class_records = cursor.execute("""
            SELECT s.class_name, COUNT(*) as total_students
            FROM students s
            JOIN teacher_classes tc ON s.class_name = tc.class_name
            WHERE tc.user_id = ?
            GROUP BY s.class_name
            ORDER BY s.class_name ASC
        """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("classes.html", class_records=class_records)

# SINGLE CLASS PAGE
@app.route("/class/<class_name>")
def class_students(class_name):
    conn = get_db()
    cursor = conn.cursor()

    selected_year = request.args.get("academic_year", "")
    attendance_date = request.args.get("attendance_date", "")

    students = cursor.execute("""
        SELECT *
        FROM students
        WHERE class_name = ?
        ORDER BY first_name ASC, last_name ASC
    """, (class_name,)).fetchall()

    total_students = len(students)

    total_boys = cursor.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE class_name = ? AND gender = 'Male'
    """, (class_name,)).fetchone()[0]

    total_girls = cursor.execute("""
        SELECT COUNT(*)
        FROM students
        WHERE class_name = ? AND gender = 'Female'
    """, (class_name,)).fetchone()[0]

    fee_summary = None
    if selected_year:
        fee_summary = cursor.execute("""
            SELECT
                COALESCE(SUM(fees.total_fee), 0) as total_fee,
                COALESCE(SUM(fees.total_paid), 0) as total_paid,
                COALESCE(SUM(fees.total_balance), 0) as total_balance
            FROM fees
            JOIN students ON fees.student_id = students.id
            WHERE students.class_name = ? AND fees.academic_year = ?
        """, (class_name, selected_year)).fetchone()

    attendance_records = []
    attendance_summary = None

    if attendance_date:
        attendance_records = cursor.execute("""
            SELECT
                attendance.date,
                attendance.status,
                students.first_name,
                students.last_name,
                students.student_number
            FROM attendance
            JOIN students ON attendance.student_id = students.id
            WHERE attendance.class_name = ? AND attendance.date = ?
            ORDER BY students.first_name ASC, students.last_name ASC
        """, (class_name, attendance_date)).fetchall()

        attendance_summary = cursor.execute("""
            SELECT
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_count,
                SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) as late_count
            FROM attendance
            WHERE class_name = ? AND date = ?
        """, (class_name, attendance_date)).fetchone()

    conn.close()

    return render_template(
        "class_students.html",
        class_name=class_name,
        students=students,
        total_students=total_students,
        total_boys=total_boys,
        total_girls=total_girls,
        selected_year=selected_year,
        fee_summary=fee_summary,
        attendance_date=attendance_date,
        attendance_records=attendance_records,
        attendance_summary=attendance_summary
    )

# FEES PAGE - FILTER BY CLASS AND YEAR
@app.route("/fees", methods=["GET"])
def fees():
    conn = get_db()
    cursor = conn.cursor()

    classes = cursor.execute("""
        SELECT DISTINCT class_name
        FROM students
        WHERE class_name IS NOT NULL AND class_name != ''
        ORDER BY class_name ASC
    """).fetchall()

    selected_class = request.args.get("class_name", "")
    selected_year = request.args.get("academic_year", "")

    fee_records = []

    if selected_class and selected_year:
        fee_records = cursor.execute("""
            SELECT
                fees.*,
                students.student_number,
                students.first_name,
                students.last_name,
                students.class_name
            FROM fees
            JOIN students ON fees.student_id = students.id
            WHERE students.class_name = ? AND fees.academic_year = ?
            ORDER BY students.first_name ASC, students.last_name ASC
        """, (selected_class, selected_year)).fetchall()

    conn.close()
    return render_template(
        "fees.html",
        classes=classes,
        fee_records=fee_records,
        selected_class=selected_class,
        selected_year=selected_year
    )


# UPDATE FEES
@app.route("/update_fees", methods=["POST"])
def update_fees():
    conn = get_db()
    cursor = conn.cursor()

    fee_id = request.form["fee_id"]
    selected_class = request.form["selected_class"]
    selected_year = request.form["selected_year"]

    term1_fee = float(request.form["term1_fee"])
    term1_paid = float(request.form["term1_paid"])
    term1_balance = term1_fee - term1_paid

    term2_fee = float(request.form["term2_fee"])
    term2_paid = float(request.form["term2_paid"])
    term2_balance = term2_fee - term2_paid

    term3_fee = float(request.form["term3_fee"])
    term3_paid = float(request.form["term3_paid"])
    term3_balance = term3_fee - term3_paid

    total_fee = term1_fee + term2_fee + term3_fee
    total_paid = term1_paid + term2_paid + term3_paid
    total_balance = term1_balance + term2_balance + term3_balance

    cursor.execute("""
        UPDATE fees
        SET
            term1_fee = ?, term1_paid = ?, term1_balance = ?,
            term2_fee = ?, term2_paid = ?, term2_balance = ?,
            term3_fee = ?, term3_paid = ?, term3_balance = ?,
            total_fee = ?, total_paid = ?, total_balance = ?
        WHERE id = ?
    """, (
        term1_fee, term1_paid, term1_balance,
        term2_fee, term2_paid, term2_balance,
        term3_fee, term3_paid, term3_balance,
        total_fee, total_paid, total_balance,
        fee_id
    ))

    conn.commit()
    conn.close()

    flash("Fees updated successfully!", "success")
    return redirect(f"/fees?class_name={selected_class}&academic_year={selected_year}")

@app.route("/delete_student/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    conn = get_db()
    cursor = conn.cursor()

    # Delete related attendance records first
    cursor.execute("""
        DELETE FROM attendance
        WHERE student_id = ?
    """, (student_id,))

    # Delete related fees records
    cursor.execute("""
        DELETE FROM fees
        WHERE student_id = ?
    """, (student_id,))

    # Delete the student
    cursor.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (student_id,))

    conn.commit()
    conn.close()

    flash("Student deleted successfully!", "success")
    return redirect("/students")

@app.route("/generate_fees", methods=["GET", "POST"])
def generate_fees():
    conn = get_db()
    cursor = conn.cursor()

    classes = cursor.execute("""
        SELECT DISTINCT class_name
        FROM students
        WHERE class_name IS NOT NULL AND class_name != ''
        ORDER BY class_name ASC
    """).fetchall()

    if request.method == "POST":
        class_name = request.form["class_name"]
        academic_year = request.form["academic_year"]
        term1_fee = float(request.form["term1_fee"])
        term2_fee = float(request.form["term2_fee"])
        term3_fee = float(request.form["term3_fee"])

        students_in_class = cursor.execute("""
            SELECT id
            FROM students
            WHERE class_name = ?
        """, (class_name,)).fetchall()

        created_count = 0

        for student in students_in_class:
            student_id = student["id"]

            existing_record = cursor.execute("""
                SELECT id
                FROM fees
                WHERE student_id = ? AND academic_year = ?
            """, (student_id, academic_year)).fetchone()

            if existing_record:
                continue

            term1_paid = 0
            term1_balance = term1_fee

            term2_paid = 0
            term2_balance = term2_fee

            term3_paid = 0
            term3_balance = term3_fee

            total_fee = term1_fee + term2_fee + term3_fee
            total_paid = 0
            total_balance = total_fee

            cursor.execute("""
                INSERT INTO fees (
                    student_id, academic_year,
                    term1_fee, term1_paid, term1_balance,
                    term2_fee, term2_paid, term2_balance,
                    term3_fee, term3_paid, term3_balance,
                    total_fee, total_paid, total_balance
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                student_id, academic_year,
                term1_fee, term1_paid, term1_balance,
                term2_fee, term2_paid, term2_balance,
                term3_fee, term3_paid, term3_balance,
                total_fee, total_paid, total_balance
            ))

            created_count += 1

        conn.commit()
        conn.close()

        flash(f"{created_count} fee record(s) generated for {class_name} - {academic_year}.", "success")
        return redirect(url_for("generate_fees"))

    conn.close()
    return render_template("generate_fees.html", classes=classes)
@app.route("/assign_teacher", methods=["GET", "POST"])
@login_required
@roles_required("director", "admin")
def assign_teacher():
    conn = get_db()
    cursor = conn.cursor()

    teachers = cursor.execute("""
        SELECT id, full_name, username
        FROM users
        WHERE role = 'teacher'
        ORDER BY full_name ASC
    """).fetchall()

    classes = cursor.execute("""
        SELECT DISTINCT class_name
        FROM students
        WHERE class_name IS NOT NULL AND class_name != ''
        ORDER BY class_name ASC
    """).fetchall()

    assignments = cursor.execute("""
        SELECT tc.id, u.full_name, u.username, tc.class_name
        FROM teacher_classes tc
        JOIN users u ON tc.user_id = u.id
        ORDER BY u.full_name ASC, tc.class_name ASC
    """).fetchall()

    if request.method == "POST":
        user_id = request.form["user_id"]
        class_name = request.form["class_name"]

        existing = cursor.execute("""
            SELECT id
            FROM teacher_classes
            WHERE user_id = ? AND class_name = ?
        """, (user_id, class_name)).fetchone()

        if existing:
            conn.close()
            flash("That teacher is already assigned to this class.", "success")
            return redirect(url_for("assign_teacher"))

        cursor.execute("""
            INSERT INTO teacher_classes (user_id, class_name)
            VALUES (?, ?)
        """, (user_id, class_name))

        conn.commit()
        conn.close()

        flash("Teacher assigned to class successfully!", "success")
        return redirect(url_for("assign_teacher"))

    conn.close()
    return render_template(
        "assign_teacher.html",
        teachers=teachers,
        classes=classes,
        assignments=assignments
    )
@app.route("/assign_parent", methods=["GET", "POST"])
@login_required
@roles_required("director", "admin")
def assign_parent():
    conn = get_db()
    cursor = conn.cursor()

    parents = cursor.execute("""
        SELECT id, full_name, username
        FROM users
        WHERE role = 'parent'
        ORDER BY full_name ASC
    """).fetchall()

    students = cursor.execute("""
        SELECT id, student_number, first_name, last_name, class_name
        FROM students
        ORDER BY first_name ASC, last_name ASC
    """).fetchall()

    assignments = cursor.execute("""
        SELECT ps.id, u.full_name, u.username, s.student_number, s.first_name, s.last_name, s.class_name
        FROM parent_students ps
        JOIN users u ON ps.user_id = u.id
        JOIN students s ON ps.student_id = s.id
        ORDER BY u.full_name ASC, s.first_name ASC, s.last_name ASC
    """).fetchall()

    if request.method == "POST":
        user_id = request.form["user_id"]
        student_id = request.form["student_id"]

        existing = cursor.execute("""
            SELECT id
            FROM parent_students
            WHERE user_id = ? AND student_id = ?
        """, (user_id, student_id)).fetchone()

        if existing:
            conn.close()
            flash("That parent is already linked to this student.", "success")
            return redirect(url_for("assign_parent"))

        cursor.execute("""
            INSERT INTO parent_students (user_id, student_id)
            VALUES (?, ?)
        """, (user_id, student_id))

        conn.commit()
        conn.close()

        flash("Parent linked to student successfully!", "success")
        return redirect(url_for("assign_parent"))

    conn.close()
    return render_template(
        "assign_parent.html",
        parents=parents,
        students=students,
        assignments=assignments
    )

# ATTENDANCE PAGE
@app.route("/attendance", methods=["GET"])
def attendance():
    conn = get_db()
    cursor = conn.cursor()

    classes = cursor.execute("""
        SELECT DISTINCT class_name
        FROM students
        WHERE class_name IS NOT NULL AND class_name != ''
        ORDER BY class_name ASC
    """).fetchall()

    selected_class = request.args.get("class_name", "")
    attendance_date = request.args.get("date", "")

    attendance_students = []
    if selected_class:
        attendance_students = cursor.execute("""
            SELECT id, student_number, first_name, last_name, class_name
            FROM students
            WHERE class_name = ?
            ORDER BY first_name ASC, last_name ASC
        """, (selected_class,)).fetchall()

    conn.close()
    return render_template(
        "attendance.html",
        classes=classes,
        students=attendance_students,
        selected_class=selected_class,
        attendance_date=attendance_date
    )


# SAVE ATTENDANCE
@app.route("/save_attendance", methods=["POST"])
def save_attendance():
    conn = get_db()
    cursor = conn.cursor()

    class_name = request.form["class_name"]
    attendance_date = request.form["attendance_date"]

    cursor.execute("""
        DELETE FROM attendance
        WHERE class_name = ? AND date = ?
    """, (class_name, attendance_date))

    student_ids = request.form.getlist("student_id")

    for student_id in student_ids:
        status = request.form.get(f"status_{student_id}", "Present")

        cursor.execute("""
            INSERT INTO attendance (student_id, class_name, date, status)
            VALUES (?, ?, ?, ?)
        """, (student_id, class_name, attendance_date, status))

    conn.commit()
    conn.close()

    flash("Attendance saved successfully!", "success")
    return redirect(f"/attendance?class_name={class_name}&date={attendance_date}")


if __name__ == "__main__":
    app.run(debug=True)