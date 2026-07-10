-- Jil Pack CRM - Complete Supabase Schema
-- Run this in Supabase SQL Editor

-- 1. CLIENTS / CUSTOMERS
CREATE TABLE clients (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    mobile TEXT,
    address TEXT,
    city TEXT,
    country TEXT,
    notes TEXT,
    is_company BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. SUPPLIERS
CREATE TABLE suppliers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    country TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. PRODUCTS
CREATE TABLE products (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    reference TEXT UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    unit_price DECIMAL(10,2) DEFAULT 0,
    category TEXT,
    unit TEXT DEFAULT 'pcs',
    stock_qty DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. DEVIS / QUOTES
CREATE TABLE quotes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    quote_number TEXT UNIQUE NOT NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'brouillon' CHECK (status IN ('brouillon', 'envoye', 'accepte', 'refuse', 'annule')),
    total_ht DECIMAL(12,2) DEFAULT 0,
    total_ttc DECIMAL(12,2) DEFAULT 0,
    valid_until DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE quote_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE,
    product_reference TEXT,
    description TEXT NOT NULL,
    quantity DECIMAL(10,2) DEFAULT 1,
    unit_price DECIMAL(10,2) DEFAULT 0,
    total DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. ORDERS / COMMANDES
CREATE TABLE orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    order_number TEXT UNIQUE NOT NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    quote_id UUID REFERENCES quotes(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'brouillon' CHECK (status IN ('brouillon', 'confirme', 'livre', 'annule')),
    total_ht DECIMAL(12,2) DEFAULT 0,
    total_ttc DECIMAL(12,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE order_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    order_id UUID REFERENCES orders(id) ON DELETE CASCADE,
    product_reference TEXT,
    description TEXT NOT NULL,
    quantity DECIMAL(10,2) DEFAULT 1,
    unit_price DECIMAL(10,2) DEFAULT 0,
    total DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. INVOICES / FACTURES
CREATE TABLE invoices (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_number TEXT UNIQUE NOT NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'brouillon' CHECK (status IN ('brouillon', 'envoye', 'paye', 'annule')),
    total_ht DECIMAL(12,2) DEFAULT 0,
    total_ttc DECIMAL(12,2) DEFAULT 0,
    invoice_date DATE,
    due_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. CLAIMS / RECLAMATIONS
CREATE TABLE claims (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    claim_number TEXT UNIQUE NOT NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    type TEXT DEFAULT 'reclamation' CHECK (type IN ('reclamation', 'retour')),
    status TEXT DEFAULT 'ouverte' CHECK (status IN ('ouverte', 'en_cours', 'acceptee', 'refusee', 'resolue')),
    description TEXT,
    decision TEXT,
    decision_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. TRANSPORTS / LOGISTICS
CREATE TABLE transports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    transport_number TEXT UNIQUE NOT NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
    mode TEXT DEFAULT 'routier' CHECK (mode IN ('routier', 'maritime', 'aerien', 'ferroviaire')),
    status TEXT DEFAULT 'planifie' CHECK (status IN ('planifie', 'en_cours', 'termine', 'annule')),
    carrier TEXT,
    bl_number TEXT,
    incoterm TEXT,
    departure_city TEXT,
    departure_date DATE,
    arrival_city TEXT,
    arrival_date DATE,
    eta DATE,
    origin TEXT,
    destination TEXT,
    documents TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. RECOVERIES / RECOUVREMENT
CREATE TABLE recoveries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    recovery_number TEXT UNIQUE NOT NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    invoice_number TEXT,
    amount DECIMAL(12,2) DEFAULT 0,
    status TEXT DEFAULT 'en_attente' CHECK (status IN ('en_attente', 'relance_email', 'relance_telephone', 'accord', 'contentieux', 'resolu')),
    contact_type TEXT CHECK (contact_type IN ('email', 'telephone')),
    contact_date DATE,
    email_sent BOOLEAN DEFAULT FALSE,
    phone_called BOOLEAN DEFAULT FALSE,
    agreement_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. SUPPORT TICKETS / SAV
CREATE TABLE support_tickets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticket_number TEXT UNIQUE NOT NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    subject TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'ouvert' CHECK (status IN ('ouvert', 'en_cours', 'attente', 'resolu', 'ferme')),
    priority TEXT DEFAULT '1' CHECK (priority IN ('0', '1', '2', '3')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. PURCHASE ORDERS / ACHATS
CREATE TABLE purchase_orders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    po_number TEXT UNIQUE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'brouillon' CHECK (status IN ('brouillon', 'envoye', 'confirme', 'recu', 'annule')),
    order_date DATE,
    expected_date DATE,
    total_ht DECIMAL(12,2) DEFAULT 0,
    total_ttc DECIMAL(12,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE purchase_order_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    order_id UUID REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_reference TEXT,
    description TEXT NOT NULL,
    quantity DECIMAL(10,2) DEFAULT 1,
    unit_price DECIMAL(10,2) DEFAULT 0,
    total DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. STOCK MOVEMENTS
CREATE TABLE stock_movements (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    reference TEXT UNIQUE NOT NULL,
    product_reference TEXT,
    product_name TEXT,
    movement_type TEXT CHECK (movement_type IN ('entree', 'sortie', 'transfert')),
    quantity DECIMAL(10,2) DEFAULT 0,
    movement_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. CRM OPPORTUNITIES
CREATE TABLE crm_opportunities (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    subject TEXT NOT NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    estimated_value DECIMAL(12,2) DEFAULT 0,
    status TEXT DEFAULT 'nouveau' CHECK (status IN ('nouveau', 'qualifie', 'proposition', 'negociation', 'gagne', 'perdu')),
    probability INTEGER DEFAULT 0,
    follow_up_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14. SAGE ERP CONFIG
CREATE TABLE sage_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT DEFAULT 'Sage ERP',
    sage_db_path TEXT,
    sage_username TEXT,
    sage_password TEXT,
    last_sync TIMESTAMPTZ,
    auto_sync BOOLEAN DEFAULT FALSE,
    sync_interval INTEGER DEFAULT 60,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. USERS (for CRM user management)
CREATE TABLE crm_users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'manager', 'user')),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_quotes_client_id ON quotes(client_id);
CREATE INDEX idx_orders_client_id ON orders(client_id);
CREATE INDEX idx_invoices_client_id ON invoices(client_id);
CREATE INDEX idx_claims_client_id ON claims(client_id);
CREATE INDEX idx_transports_client_id ON transports(client_id);
CREATE INDEX idx_recoveries_client_id ON recoveries(client_id);
CREATE INDEX idx_support_tickets_client_id ON support_tickets(client_id);
CREATE INDEX idx_quote_items_quote_id ON quote_items(quote_id);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_purchase_order_items_order_id ON purchase_order_items(order_id);
CREATE INDEX idx_transports_order_id ON transports(order_id);
CREATE INDEX idx_recoveries_invoice_id ON recoveries(invoice_id);
CREATE INDEX idx_opportunities_client_id ON crm_opportunities(client_id);

-- Enable Row Level Security (RLS)
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE transports ENABLE ROW LEVEL SECURITY;
ALTER TABLE recoveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE sage_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE crm_users ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (authenticated users can read/write)
CREATE POLICY "Authenticated users can read clients" ON clients FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY "Authenticated users can insert clients" ON clients FOR INSERT TO authenticated WITH CHECK (TRUE);
CREATE POLICY "Authenticated users can update clients" ON clients FOR UPDATE TO authenticated USING (TRUE);
CREATE POLICY "Authenticated users can delete clients" ON clients FOR DELETE TO authenticated USING (TRUE);

-- Apply same policy to all tables (replace 'clients' with each table name)
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY['suppliers','products','quotes','quote_items','orders','order_items','invoices','claims','transports','recoveries','support_tickets','purchase_orders','purchase_order_items','stock_movements','crm_opportunities','sage_config','crm_users'])
    LOOP
        EXECUTE format('CREATE POLICY "Authenticated users can read %s" ON %I FOR SELECT TO authenticated USING (TRUE);', tbl, tbl);
        EXECUTE format('CREATE POLICY "Authenticated users can insert %s" ON %I FOR INSERT TO authenticated WITH CHECK (TRUE);', tbl, tbl);
        EXECUTE format('CREATE POLICY "Authenticated users can update %s" ON %I FOR UPDATE TO authenticated USING (TRUE);', tbl, tbl);
        EXECUTE format('CREATE POLICY "Authenticated users can delete %s" ON %I FOR DELETE TO authenticated USING (TRUE);', tbl, tbl);
    END LOOP;
END;
$$;
