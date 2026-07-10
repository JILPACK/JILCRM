import psycopg2

pw = "DouceurDouceAx0@"

# Try different SSL modes
for mode in ["require", "prefer", "allow", "verify-full", "verify-ca"]:
    try:
        conn = psycopg2.connect(
            host="db.essorjnuwhqxvyunizzo.supabase.co",
            port=5432,
            user="postgres",
            password=pw,
            dbname="postgres",
            sslmode=mode,
            connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print(f"SSL mode '{mode}': OK")
        cur.close()
        conn.close()
        break
    except Exception as e:
        err = str(e)[:80]
        print(f"SSL mode '{mode}': {err}")
