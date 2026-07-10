from supabase import create_client
SUPABASE_URL = "https://essorjnuwhqxvyunizzo.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzc29yam51d2hxeHZ5dW5penpvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjgxMDczOSwiZXhwIjoyMDk4Mzg2NzM5fQ.9b_BNzaqUVYoBnYhn-yBjxrhWfSOwWhX-GEoLB7SUbY"
supabase = create_client(SUPABASE_URL, KEY)

tables = [
    "clients", "suppliers", "products", "quotes", "quote_items",
    "orders", "order_items", "invoices", "claims", "transports",
    "recoveries", "support_tickets", "purchase_orders", "purchase_order_items",
    "stock_movements", "crm_opportunities", "sage_config", "crm_users"
]

print(f"{'Table':25s} {'Count':>6s}  {'Status'}")
print("-" * 43)
for t in tables:
    try:
        r = supabase.table(t).select("*", count="exact").execute()
        print(f"{t:25s} {r.count:>6d}  OK")
    except Exception as e:
        print(f"{t:25s} {'ERR':>6s}  {str(e)[:50]}")
