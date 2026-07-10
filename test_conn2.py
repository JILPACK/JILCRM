import os
pw = "DouceurDouceAx0@"
print(f"Password length: {len(pw)}")
print(f"Password chars: {[ord(c) for c in pw]}")
print(f"Password repr: {repr(pw)}")

import psycopg2
try:
    conn = psycopg2.connect(
        host="db.essorjnuwhqxvyunizzo.supabase.co",
        port=5432,
        user="postgres",
        password=pw,
        dbname="postgres",
        sslmode="disable",
        connect_timeout=10
    )
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("OK")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error type: {type(e).__name__}")
    print(f"Error: {e}")
