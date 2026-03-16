import sqlite3

conn = sqlite3.connect("school.db")
cursor = conn.cursor()

# add missing columns if they don't exist
try:
    cursor.execute("ALTER TABLE fees ADD COLUMN paid_amount REAL DEFAULT 0")
except:
    pass

try:
    cursor.execute("ALTER TABLE fees ADD COLUMN balance REAL DEFAULT 0")
except:
    pass

conn.commit()
conn.close()

print("Fees table updated successfully!")