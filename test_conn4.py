import socket
import psycopg2

# Get IPv6 address
host = "db.essorjnuwhqxvyunizzo.supabase.co"
ips = socket.getaddrinfo(host, 5432, socket.AF_INET6)
ipv6 = ips[0][4][0]
print(f"Connecting via IPv6: {ipv6}")

pw = "DouceurDouceAx0@"

# Try with IPv6 in brackets
for addr in [ipv6, f"[{ipv6}]", host]:
    try:
        conn = psycopg2.connect(
            host=addr,
            port=5432,
            user="postgres",
            password=pw,
            dbname="postgres",
            sslmode="require",
            connect_timeout=10
        )
        cur = conn.cursor()
        cur.execute("SELECT version()")
        print(f"Connected via {addr}: {cur.fetchone()[0][:60]}")
        cur.close()
        conn.close()
        break
    except Exception as e:
        print(f"Failed via {addr}: {type(e).__name__}: {str(e)[:100]}")
