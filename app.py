from flask import Flask, render_template, request, redirect, url_for, flash
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


# DASHBOARD
@app.route("/")
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    total_students = cursor.execute("SELECT COUNT(*) FROM students").fetchone()[0]

    total_classes = cursor.execute("""
        SELECT COUNT(DISTINCT class_name)
        FROM students
        WHERE class_name IS NOT NULL AND class_name != ''
    """).fetchone()[0]

    total_fees = cursor.execute("""
        SELECT COALESCE(SUM(total_fee), 0) FROM fees
    """).fetchone()[0]

    total_paid = cursor.execute("""
        SELECT COALESCE(SUM(total_paid), 0) FROM fees
    """).fetchone()[0]

    total_balance = cursor.execute("""
        SELECT COALESCE(SUM(total_balance), 0) FROM fees
    """).fetchone()[0]

    recent_students = cursor.execute("""
        SELECT student_number, first_name, last_name, class_name
        FROM students
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_classes=total_classes,
        total_fees=total_fees,
        total_paid=total_paid,
        total_balance=total_balance,
        recent_students=recent_students
    )


# ADD STUDENT PAGE
@app.route("/add_student")
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
def student_profile(student_id):
    conn = get_db()
    cursor = conn.cursor()

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
def classes():
    conn = get_db()
    cursor = conn.cursor()

    class_records = cursor.execute("""
        SELECT class_name, COUNT(*) as total_students
        FROM students
        WHERE class_name IS NOT NULL AND class_name != ''
        GROUP BY class_name
        ORDER BY class_name ASC
    """).fetchall()

    conn.close()
    return render_template("classes.html", class_records=class_records)


# SINGLE CLASS PAGE
@app.route("/class/<class_name>")
def class_students(class_name):
    conn = get_db()
    cursor = conn.cursor()

    class_students_records = cursor.execute("""
        SELECT *
        FROM students
        WHERE class_name = ?
        ORDER BY first_name ASC, last_name ASC
    """, (class_name,)).fetchall()

    conn.close()
    return render_template(
        "class_students.html",
        students=class_students_records,
        class_name=class_name
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