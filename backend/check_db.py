import sqlite3
import os

db_path = "creditiq.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, company_id, analysis_status, progress, failure_reason FROM analyses ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    for row in rows:
        print(row)
    conn.close()
else:
    print("DB not found")
