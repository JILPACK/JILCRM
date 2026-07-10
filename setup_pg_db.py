import psycopg2
conn = psycopg2.connect(host="localhost", port=5432, user="postgres", password="postgres", dbname="postgres")
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT 1 FROM pg_roles WHERE rolname='odoo'")
if not cur.fetchone():
    cur.execute("CREATE ROLE odoo WITH LOGIN PASSWORD 'odoo' CREATEDB")
    print("User odoo created")
else:
    print("User odoo exists")

cur.execute("SELECT 1 FROM pg_database WHERE datname='odoo_jil_crm'")
if not cur.fetchone():
    cur.execute("CREATE DATABASE odoo_jil_crm OWNER odoo")
    print("Database odoo_jil_crm created")
else:
    print("Database odoo_jil_crm exists")

cur.close()
conn.close()
print("Done")
