import socket
import psycopg2

host = "db.essorjnuwhqxvyunizzo.supabase.co"
pw = "DouceurDouceAx0@"

# Get IPv6 address
ipv6 = socket.getaddrinfo(host, 5432, socket.AF_INET6)[0][4][0]
print(f"IPv6: {ipv6}")

# Try connecting with IPv6 in brackets
try:
    conn = psycopg2.connect(
        host=f"[{ipv6}]",
        port=5432,
        user="postgres",
        password=pw,
        dbname="postgres",
        sslmode="require",
        connect_timeout=15
    )
    cur = conn.cursor()
    cur.execute("SELECT version()")
    print("Connected:", cur.fetchone()[0][:60])
    cur.close()
    conn.close()
except Exception as e:
    print(f"Failed: {type(e).__name__}: {str(e)[:200]}")
