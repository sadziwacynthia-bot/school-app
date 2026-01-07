import sqlite3

db = sqlite3.connect("school.db")
cursor = db.cursor()

cursor.execute("DROP TABLE IF EXISTS students")

cursor.execute("""
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    class_name TEXT,
    date_of_birth TEXT
)
""")

db.commit()
db.close()

print("Database updated successfully!")
