import psycopg2
conn = psycopg2.connect(
    host="db.essorjnuwhqxvyunizzo.supabase.co",
    port=5432,
    user="postgres",
    password="DouceurDouceAx0@",
    dbname="postgres",
    sslmode="require"
)
cur = conn.cursor()
cur.execute("SELECT version()")
print("Connected:", cur.fetchone()[0][:60])

cur.execute("SELECT 1 FROM pg_database WHERE datname='odoo_jil_crm'")
if not cur.fetchone():
    conn.autocommit = True
    cur.execute("CREATE DATABASE odoo_jil_crm")
    print("Database odoo_jil_crm created")
else:
    print("Database odoo_jil_crm already exists")

cur.close()
conn.close()
