import psycopg2
for pw in ["postgres", "odoo", "admin", "password", "pgadmin", ""]:
    try:
        conn = psycopg2.connect(host="localhost", port=5432, user="postgres", password=pw, dbname="postgres", connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT current_user, version()")
        print(f"Password '{pw}': OK - {cur.fetchone()[0]}")
        conn.close()
        break
    except Exception as e:
        print(f"Password '{pw}': {str(e)[:50]}")
