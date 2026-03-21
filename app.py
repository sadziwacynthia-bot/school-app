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


# GENERATE TEACHER ID
def generate_teacher_id():
    conn = get_db()
    cursor = conn.cursor()

    last_teacher = cursor.execute("""
        SELECT id
        FROM teachers
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    if last_teacher:
        next_id = last_teacher["id"] + 1
    else:
        next_id = 1

    return f"TCH{next_id:03d}"


# LOGIN REQUIRED
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "success")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ROLE PROTECTION
def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "role" not in session:
                flash("Please log in first.", "success")
                return redirect(url_for("login"))

            if session["role"] not in allowed_roles:
                flash("You do not have permission to view that page.", "success")
                return redirect(url_for("dashboard"))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_setup_code(length=6):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=length))

# LOGIN
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

        if not user:
            flash("Invalid username or password.", "success")
            return redirect(url_for("login"))

        if user["must_set_password"] == 1:
            flash("You must set your password first using your setup code.", "success")
            return redirect(url_for("set_password"))

        if user["password"] and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]

            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "success")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/set_password", methods=["GET", "POST"])
def set_password():
    if request.method == "POST":
        username = request.form["username"]
        setup_code = request.form["setup_code"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match.", "success")
            return redirect(url_for("set_password"))

        conn = get_db()
        cursor = conn.cursor()

        user = cursor.execute("""
            SELECT *
            FROM users
            WHERE username = ? AND setup_code = ?
        """, (username, setup_code)).fetchone()

        if not user:
            conn.close()
            flash("Invalid username or setup code.", "success")
            return redirect(url_for("set_password"))

        hashed_password = generate_password_hash(new_password)

        cursor.execute("""
            UPDATE users
            SET password = ?, setup_code = '', must_set_password = 0
            WHERE id = ?
        """, (hashed_password, user["id"]))

        conn.commit()
        conn.close()

        flash("Password set successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("set_password.html")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


# DASHBOARD
@app.route("/")
@login_required
def dashboard():
    if session.get("role") == "teacher":
        conn = get_db()
        cursor = conn.cursor()

        teacher_classes = cursor.execute("""
            SELECT class_name
            FROM teacher_classes
            WHERE user_id = ?
            ORDER BY class_name ASC
        """, (session["user_id"],)).fetchall()

        conn.close()

        return render_template(
            "teacher_dashboard.html",
            teacher_name=session.get("full_name"),
            teacher_classes=teacher_classes
        )

    elif session.get("role") == "parent":
        return redirect(url_for("parent_dashboard"))

    conn = get_db()
    cursor = conn.cursor()

    total_students = cursor.execute("""
        SELECT COUNT(*)
        FROM students
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
@app.route("/parent_dashboard")
@login_required
@roles_required("parent")
def parent_dashboard():
    conn = get_db()
    cursor = conn.cursor()

    children = cursor.execute("""
        SELECT
            s.id,
            s.student_number,
            s.first_name,
            s.last_name,
            s.class_name
        FROM parent_students ps
        JOIN students s ON ps.student_id = s.id
        WHERE ps.user_id = ?
        ORDER BY s.first_name ASC, s.last_name ASC
    """, (session["user_id"],)).fetchall()

    children_data = []

    for child in children:
        latest_fee = cursor.execute("""
            SELECT *
            FROM fees
            WHERE student_id = ?
            ORDER BY academic_year DESC
            LIMIT 1
        """, (child["id"],)).fetchone()

        attendance_summary = cursor.execute("""
            SELECT
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_count,
                SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) as late_count
            FROM attendance
            WHERE student_id = ?
        """, (child["id"],)).fetchone()

        result_summary = cursor.execute("""
            SELECT
                COUNT(*) as total_subjects,
                AVG(mark) as average_mark
            FROM results
            WHERE student_id = ?
        """, (child["id"],)).fetchone()
        result_records = cursor.execute("""
            SELECT *
            FROM results
            WHERE student_id = ?
            ORDER BY academic_year DESC, term ASC, subject_name ASC
        """, (child["id"],)).fetchall()

        children_data.append({
            "id": child["id"],
            "student_number": child["student_number"],
            "first_name": child["first_name"],
            "last_name": child["last_name"],
            "class_name": child["class_name"],
            "fee": latest_fee,
            "attendance": attendance_summary,
            "results": result_summary,
            "result_records": result_records
        })
        
    conn.close()

    return render_template(
        "parent_dashboard.html",
        parent_name=session.get("full_name"),
        children_data=children_data
    )
@app.route("/subjects")
@login_required
@roles_required("director", "admin", "teacher")
def subjects():
    conn = get_db()
    cursor = conn.cursor()

    if session["role"] in ["director", "admin"]:
        subject_records = cursor.execute("""
            SELECT ts.id, u.full_name, ts.class_name, ts.subject_name
            FROM teacher_subjects ts
            JOIN users u ON ts.user_id = u.id
            ORDER BY ts.class_name ASC, ts.subject_name ASC
        """).fetchall()
    else:
        subject_records = cursor.execute("""
            SELECT ts.id, u.full_name, ts.class_name, ts.subject_name
            FROM teacher_subjects ts
            JOIN users u ON ts.user_id = u.id
            WHERE ts.user_id = ?
            ORDER BY ts.class_name ASC, ts.subject_name ASC
        """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("subjects.html", subject_records=subject_records)
@app.route("/assign_subject", methods=["GET", "POST"])
@login_required
@roles_required("director", "admin")
def assign_subject():
    conn = get_db()
    cursor = conn.cursor()

    teachers = cursor.execute("""
        SELECT id, full_name, username
        FROM users
        WHERE role = 'teacher'
        ORDER BY full_name ASC
    """).fetchall()

    classes = cursor.execute("""
        SELECT class_name
        FROM classes
        ORDER BY class_name ASC
    """).fetchall()

    subjects = cursor.execute("""
        SELECT subject_name
        FROM subjects
        ORDER BY subject_name ASC
    """).fetchall()

    assignments = cursor.execute("""
        SELECT ts.id, u.full_name, ts.class_name, ts.subject_name
        FROM teacher_subjects ts
        JOIN users u ON ts.user_id = u.id
        ORDER BY u.full_name ASC, ts.class_name ASC, ts.subject_name ASC
    """).fetchall()

    if request.method == "POST":
        user_id = request.form["user_id"]
        class_name = request.form["class_name"]
        subject_name = request.form["subject_name"]

        existing = cursor.execute("""
            SELECT id
            FROM teacher_subjects
            WHERE user_id = ? AND class_name = ? AND subject_name = ?
        """, (user_id, class_name, subject_name)).fetchone()

        if existing:
            conn.close()
            flash("This subject assignment already exists.", "success")
            return redirect(url_for("assign_subject"))

        cursor.execute("""
            INSERT INTO teacher_subjects (user_id, class_name, subject_name)
            VALUES (?, ?, ?)
        """, (user_id, class_name, subject_name))

        conn.commit()
        conn.close()

        flash("Subject assigned successfully!", "success")
        return redirect(url_for("assign_subject"))

    conn.close()
    return render_template(
        "assign_subject.html",
        teachers=teachers,
        classes=classes,
        subjects=subjects,
        assignments=assignments
    )
@app.route("/assignments")
@login_required
@roles_required("director", "admin", "teacher")
def assignments():
    conn = get_db()
    cursor = conn.cursor()

    if session["role"] in ["director", "admin"]:
        assignment_records = cursor.execute("""
            SELECT a.*, u.full_name
            FROM assignments a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
        """).fetchall()
    else:
        assignment_records = cursor.execute("""
            SELECT a.*, u.full_name
            FROM assignments a
            JOIN users u ON a.user_id = u.id
            WHERE a.user_id = ?
            ORDER BY a.created_at DESC
        """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("assignments.html", assignment_records=assignment_records)


@app.route("/add_assignment", methods=["GET", "POST"])
@login_required
@roles_required("director", "admin", "teacher")
def add_assignment():
    conn = get_db()
    cursor = conn.cursor()

    if session["role"] in ["director", "admin"]:
        subject_options = cursor.execute("""
            SELECT ts.class_name, ts.subject_name
            FROM teacher_subjects ts
            ORDER BY ts.class_name ASC, ts.subject_name ASC
        """).fetchall()
    else:
        subject_options = cursor.execute("""
            SELECT ts.class_name, ts.subject_name
            FROM teacher_subjects ts
            WHERE ts.user_id = ?
            ORDER BY ts.class_name ASC, ts.subject_name ASC
        """, (session["user_id"],)).fetchall()

    if request.method == "POST":
        class_name = request.form["class_name"]
        subject_name = request.form["subject_name"]
        title = request.form["title"]
        instructions = request.form["instructions"]
        due_date = request.form["due_date"]

        cursor.execute("""
            INSERT INTO assignments (user_id, class_name, subject_name, title, instructions, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session["user_id"], class_name, subject_name, title, instructions, due_date))

        conn.commit()
        conn.close()

        flash("Assignment created successfully!", "success")
        return redirect(url_for("assignments"))

    conn.close()
    return render_template("add_assignment.html", subject_options=subject_options)

# USERS PAGE
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


# TEACHERS PAGE
@app.route("/teachers")
@login_required
@roles_required("director", "admin")
def teachers_list():
    conn = get_db()
    cursor = conn.cursor()

    teacher_records = cursor.execute("""
        SELECT teacher_id, full_name, phone, email
        FROM teachers
        ORDER BY id DESC
    """).fetchall()

    conn.close()
    return render_template("teachers.html", teacher_records=teacher_records)


# REGISTER TEACHER PAGE
@app.route("/register_teacher")
@login_required
@roles_required("director", "admin")
def register_teacher():
    return render_template("teacher_register.html")


# SAVE TEACHER
@app.route("/save_teacher", methods=["POST"])
@login_required
@roles_required("director", "admin")
def save_teacher():
    full_name = request.form["full_name"]
    phone = request.form["phone"]
    email = request.form["email"]
    username = request.form["username"]

    teacher_id = generate_teacher_id()
    setup_code = generate_setup_code()

    conn = get_db()
    cursor = conn.cursor()

    existing_user = cursor.execute("""
        SELECT id, role
        FROM users
        WHERE username = ?
    """, (username,)).fetchone()

    if existing_user:
        conn.close()
        flash("Username already exists. Please choose another one.", "success")
        return redirect(url_for("register_teacher"))

    cursor.execute("""
        INSERT INTO users (full_name, username, password, role, setup_code, must_set_password)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (full_name, username, None, "teacher", setup_code, 1))

    user_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO teachers (user_id, teacher_id, full_name, phone, email)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, teacher_id, full_name, phone, email))

    conn.commit()
    conn.close()

    flash(f"Teacher registered! Teacher ID: {teacher_id} | Setup Code: {setup_code}", "success")
    return redirect(url_for("teachers_list"))

# ADD STUDENT PAGE
@app.route("/add_student")
@login_required
@roles_required("director", "admin")
def add_student_page():
    return render_template("add_student.html")


# SAVE STUDENT
@app.route("/save_student", methods=["POST"])
@login_required
@roles_required("director", "admin")
def save_student():
    conn = get_db()
    cursor = conn.cursor()

    # STUDENT DETAILS
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

    # GUARDIAN 1
    guardian1_name = request.form["guardian1_name"]
    guardian1_relationship = request.form["guardian1_relationship"]
    guardian1_phone = request.form["guardian1_phone"]
    guardian1_whatsapp = request.form["guardian1_whatsapp"]
    guardian1_email = request.form["guardian1_email"]
    parent_username = request.form["parent_username"].strip()

    # GUARDIAN 2
    guardian2_name = request.form["guardian2_name"]
    guardian2_relationship = request.form["guardian2_relationship"]
    guardian2_phone = request.form["guardian2_phone"]
    guardian2_whatsapp = request.form["guardian2_whatsapp"]
    guardian2_email = request.form["guardian2_email"]

    # FEES
    academic_year = request.form["academic_year"]
    term1_fee = float(request.form["term1_fee"])
    term2_fee = float(request.form["term2_fee"])
    term3_fee = float(request.form["term3_fee"])

    # GENERATE STUDENT NUMBER
    student_number = generate_student_number()

    try:
        # SAVE STUDENT
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

        # SAVE FEES
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

        # CREATE OR LINK PARENT ACCOUNT USING GUARDIAN 1
        parent_setup_code = None

        if guardian1_name and parent_username:
            existing_parent = cursor.execute("""
                SELECT id, role
                FROM users
                WHERE username = ?
            """, (parent_username,)).fetchone()

            if existing_parent:
                # Username exists but not as parent
                if existing_parent["role"] != "parent":
                    conn.rollback()
                    conn.close()
                    flash("Parent username already exists under another role. Please choose another username.", "success")
                    return redirect(url_for("add_student_page"))

                parent_user_id = existing_parent["id"]

            else:
                # Create new parent account
                parent_setup_code = generate_setup_code()

                cursor.execute("""
                    INSERT INTO users (full_name, username, password, role, setup_code, must_set_password)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    guardian1_name,
                    parent_username,
                    None,
                    "parent",
                    parent_setup_code,
                    1
                ))

                parent_user_id = cursor.lastrowid

            # Link parent to student
            existing_link = cursor.execute("""
                SELECT id
                FROM parent_students
                WHERE user_id = ? AND student_id = ?
            """, (parent_user_id, student_id)).fetchone()

            if not existing_link:
                cursor.execute("""
                    INSERT INTO parent_students (user_id, student_id)
                    VALUES (?, ?)
                """, (parent_user_id, student_id))

        conn.commit()
        conn.close()

        if guardian1_name and parent_username and parent_setup_code:
            flash(
                f"Student registered successfully! Parent account created. Username: {parent_username} | Setup Code: {parent_setup_code}",
                "success"
            )
        elif guardian1_name and parent_username:
            flash(
                f"Student registered successfully! Existing parent account linked. Username: {parent_username}",
                "success"
            )
        else:
            flash("Student registered successfully!", "success")

        return redirect("/students")

    except Exception as e:
        conn.rollback()
        conn.close()
        flash(f"Error saving student: {str(e)}", "success")
        return redirect(url_for("add_student_page"))

# VIEW STUDENTS
@app.route("/students")
@login_required
@roles_required("director", "admin", "teacher")
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


# STUDENT PROFILE
@app.route("/student/<int:student_id>")
@login_required
def student_profile(student_id):
    conn = get_db()
    cursor = conn.cursor()

    if session["role"] in ["director", "admin"]:
        allowed = True

    elif session["role"] == "teacher":
        teacher_class = cursor.execute("""
            SELECT 1
            FROM teacher_classes tc
            JOIN students s ON tc.class_name = s.class_name
            WHERE tc.user_id = ? AND s.id = ?
        """, (session["user_id"], student_id)).fetchone()
        allowed = teacher_class is not None

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
    
    result_records = cursor.execute("""
        SELECT *
        FROM results
        WHERE student_id = ?
        ORDER BY academic_year DESC, term ASC, subject_name ASC
    """, (student_id,)).fetchall()

    conn.close()

    return render_template(
        "student_profile.html",
        student=student,
        fee_records=fee_records,
        attendance_records=attendance_records,
        result_records=result_records
    )


# EDIT STUDENT
@app.route("/edit_student/<int:student_id>")
@login_required
@roles_required("director", "admin")
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


# UPDATE STUDENT
@app.route("/update_student/<int:student_id>", methods=["POST"])
@login_required
@roles_required("director", "admin")
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


# DELETE STUDENT
@app.route("/delete_student/<int:student_id>", methods=["POST"])
@login_required
@roles_required("director", "admin")
def delete_student(student_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM attendance
        WHERE student_id = ?
    """, (student_id,))

    cursor.execute("""
        DELETE FROM fees
        WHERE student_id = ?
    """, (student_id,))

    cursor.execute("""
        DELETE FROM parent_students
        WHERE student_id = ?
    """, (student_id,))

    cursor.execute("""
        DELETE FROM students
        WHERE id = ?
    """, (student_id,))

    conn.commit()
    conn.close()

    flash("Student deleted successfully!", "success")
    return redirect("/students")


# CLASSES PAGE
@app.route("/classes")
@login_required
@roles_required("director", "admin", "teacher")
def classes():
    conn = get_db()
    cursor = conn.cursor()

    if session["role"] in ["director", "admin"]:
        class_records = cursor.execute("""
            SELECT
                c.class_name,
                COUNT(s.id) as total_students
            FROM classes c
            LEFT JOIN students s ON c.class_name = s.class_name
            GROUP BY c.class_name
            ORDER BY c.class_name ASC
        """).fetchall()
    else:
        class_records = cursor.execute("""
            SELECT
                c.class_name,
                COUNT(s.id) as total_students
            FROM classes c
            JOIN teacher_classes tc ON c.class_name = tc.class_name
            LEFT JOIN students s ON c.class_name = s.class_name
            WHERE tc.user_id = ?
            GROUP BY c.class_name
            ORDER BY c.class_name ASC
        """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("classes.html", class_records=class_records)

# SINGLE CLASS PAGE
@app.route("/class/<class_name>")
@login_required
@roles_required("director", "admin", "teacher")
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


# FEES PAGE
@app.route("/fees", methods=["GET"])
@login_required
@roles_required("director", "admin")
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
@login_required
@roles_required("director", "admin")
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


# GENERATE FEES
@app.route("/generate_fees", methods=["GET", "POST"])
@login_required
@roles_required("director", "admin")
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
@app.route("/results")
@login_required
@roles_required("director", "admin", "teacher")
def results():
    conn = get_db()
    cursor = conn.cursor()

    if session["role"] in ["director", "admin"]:
        result_records = cursor.execute("""
            SELECT
                r.*,
                s.first_name,
                s.last_name,
                s.student_number,
                u.full_name
            FROM results r
            JOIN students s ON r.student_id = s.id
            JOIN users u ON r.user_id = u.id
            ORDER BY r.academic_year DESC, r.term ASC, r.class_name ASC, r.subject_name ASC
        """).fetchall()
    else:
        result_records = cursor.execute("""
            SELECT
                r.*,
                s.first_name,
                s.last_name,
                s.student_number,
                u.full_name
            FROM results r
            JOIN students s ON r.student_id = s.id
            JOIN users u ON r.user_id = u.id
            WHERE r.user_id = ?
            ORDER BY r.academic_year DESC, r.term ASC, r.class_name ASC, r.subject_name ASC
        """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("results.html", result_records=result_records)
@app.route("/enter_results", methods=["GET", "POST"])
@login_required
@roles_required("director", "admin", "teacher")
def enter_results():
    conn = get_db()
    cursor = conn.cursor()

    selected_class = request.args.get("class_name", "")
    selected_subject = request.args.get("subject_name", "")
    selected_term = request.args.get("term", "")
    selected_year = request.args.get("academic_year", "")

    if session["role"] in ["director", "admin"]:
        subject_options = cursor.execute("""
            SELECT DISTINCT class_name, subject_name
            FROM teacher_subjects
            ORDER BY class_name ASC, subject_name ASC
        """).fetchall()
    else:
        subject_options = cursor.execute("""
            SELECT DISTINCT class_name, subject_name
            FROM teacher_subjects
            WHERE user_id = ?
            ORDER BY class_name ASC, subject_name ASC
        """, (session["user_id"],)).fetchall()

    students = []
    if selected_class:
        students = cursor.execute("""
            SELECT id, student_number, first_name, last_name
            FROM students
            WHERE class_name = ?
            ORDER BY first_name ASC, last_name ASC
        """, (selected_class,)).fetchall()

    if request.method == "POST":
        class_name = request.form["class_name"]
        subject_name = request.form["subject_name"]
        term = request.form["term"]
        academic_year = request.form["academic_year"]

        student_ids = request.form.getlist("student_id")

        for student_id in student_ids:
            mark_value = request.form.get(f"mark_{student_id}", "").strip()

            if mark_value == "":
                continue

            mark = float(mark_value)

            existing_result = cursor.execute("""
                SELECT id
                FROM results
                WHERE student_id = ? AND class_name = ? AND subject_name = ? AND term = ? AND academic_year = ?
            """, (student_id, class_name, subject_name, term, academic_year)).fetchone()

            if existing_result:
                cursor.execute("""
                    UPDATE results
                    SET mark = ?, user_id = ?
                    WHERE id = ?
                """, (mark, session["user_id"], existing_result["id"]))
            else:
                cursor.execute("""
                    INSERT INTO results (student_id, user_id, class_name, subject_name, term, academic_year, mark)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (student_id, session["user_id"], class_name, subject_name, term, academic_year, mark))

        conn.commit()
        conn.close()

        flash("Results saved successfully!", "success")
        return redirect(url_for(
            "enter_results",
            class_name=class_name,
            subject_name=subject_name,
            term=term,
            academic_year=academic_year
        ))

    conn.close()
    return render_template(
        "enter_results.html",
        subject_options=subject_options,
        students=students,
        selected_class=selected_class,
        selected_subject=selected_subject,
        selected_term=selected_term,
        selected_year=selected_year
    )

# ASSIGN TEACHER TO CLASS
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


# ASSIGN PARENT TO STUDENT
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
@login_required
@roles_required("director", "admin", "teacher")
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
@login_required
@roles_required("director", "admin", "teacher")
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