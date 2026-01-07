from flask import Flask, render_template, request, redirect
import sqlite3
from urllib.parse import unquote  # for URL decoding class names
from datetime import date as today

app = Flask(__name__)

# -----------------------------
# Database connection
# -----------------------------
def get_db():
    return sqlite3.connect("school.db")

# -----------------------------
# Home page
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# -----------------------------
# Register student (with optional fee)
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Student info
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        class_name = request.form["class_name"]
        date_of_birth = request.form["date_of_birth"]

        # Fee info (optional)
        fee_amount = request.form.get("fee_amount")
        fee_due_date = request.form.get("fee_due_date")
        fee_status = request.form.get("fee_status")

        db = get_db()
        cursor = db.cursor()

        # Insert student
        cursor.execute("""
            INSERT INTO students 
            (first_name, last_name, email, class_name, date_of_birth)
            VALUES (?, ?, ?, ?, ?)
        """, (first_name, last_name, email, class_name, date_of_birth))
        student_id = cursor.lastrowid

        # Insert fee if provided
        if fee_amount and fee_due_date and fee_status:
            cursor.execute("""
                INSERT INTO fees (student_id, amount, status, due_date)
                VALUES (?, ?, ?, ?)
            """, (student_id, float(fee_amount), fee_status, fee_due_date))

        db.commit()
        db.close()
        return redirect("/students")

    return render_template("register.html")

# -----------------------------
# View all students
# -----------------------------
@app.route("/students")
def students():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM students ORDER BY class_name, last_name")
    students = cursor.fetchall()
    db.close()
    return render_template("students.html", students=students)

# -----------------------------
# View all classes
# -----------------------------
@app.route("/classes")
def classes():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT class_name, COUNT(*) as student_count
        FROM students
        GROUP BY class_name
        ORDER BY class_name
    """)
    classes = cursor.fetchall()
    db.close()
    return render_template("classes.html", classes=classes)

# -----------------------------
# View students in a class
# -----------------------------
@app.route("/class/<class_name>")
def class_students(class_name):
    class_name = unquote(class_name)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM students WHERE class_name = ? ORDER BY last_name", (class_name,))
    students = cursor.fetchall()
    db.close()
    return render_template("class_students.html", students=students, class_name=class_name)

# -----------------------------
# Attendance tracking
# -----------------------------
@app.route("/attendance/<class_name>", methods=["GET", "POST"])
def attendance(class_name):
    class_name = unquote(class_name)
    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        for student_id, status in request.form.items():
            cursor.execute("""
                INSERT INTO attendance (student_id, date, status)
                VALUES (?, ?, ?)
            """, (student_id, today().isoformat(), status))
        db.commit()
        db.close()
        return redirect(f"/class/{class_name}")

    # Get students in class
    cursor.execute("SELECT * FROM students WHERE class_name = ? ORDER BY last_name", (class_name,))
    students = cursor.fetchall()
    db.close()
    return render_template("attendance.html", students=students, class_name=class_name)

# -----------------------------
# View all fees
# -----------------------------
@app.route("/fees")
def fees():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT s.id, s.first_name, s.last_name, s.class_name,
               SUM(CASE WHEN f.status='Paid' THEN f.amount ELSE 0 END) as total_paid,
               SUM(CASE WHEN f.status='Unpaid' THEN f.amount ELSE 0 END) as total_unpaid
        FROM students s
        LEFT JOIN fees f ON s.id = f.student_id
        GROUP BY s.id
        ORDER BY s.class_name, s.last_name
    """)
    fees_list = cursor.fetchall()
    db.close()
    return render_template("fees.html", fees=fees_list)

# -----------------------------
# Add fee for a student (optional)
# -----------------------------
@app.route("/add_fee", methods=["GET", "POST"])
def add_fee():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM students ORDER BY class_name, last_name")
    students = cursor.fetchall()

    if request.method == "POST":
        student_id = request.form["student_id"]
        amount = request.form["amount"]
        due_date = request.form["due_date"]
        status = request.form["status"]

        cursor.execute("""
            INSERT INTO fees (student_id, amount, status, due_date)
            VALUES (?, ?, ?, ?)
        """, (student_id, float(amount), status, due_date))
        db.commit()
        db.close()
        return redirect("/fees")

    db.close()
    return render_template("add_fee.html", students=students)

# -----------------------------
# Run the app
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)

