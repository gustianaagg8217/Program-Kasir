-- ============================================================================
-- DATABASE MIGRATION - Enterprise Features for POS System
-- ============================================================================
-- Fungsi: Add tables for Multi-Payment, Inventory, Activity Logging, Online Orders
-- Version: 1.0
-- Date: 2026-04-27
-- ============================================================================

-- ============================================================================
-- 1. PAYMENT TABLES - Multi-Payment Support
-- ============================================================================

-- Payment records table (stores each payment method used in transaction)
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    method TEXT NOT NULL CHECK (method IN ('cash', 'debit', 'credit', 'ovo', 'gopay', 'dana', 'qris')),
    amount INTEGER NOT NULL,
    reference_id TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed', 'refunded', 'cancelled')),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    verified_by TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_payments_transaction ON payments(transaction_id);
CREATE INDEX IF NOT EXISTS idx_payments_method ON payments(method);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_timestamp ON payments(timestamp);


-- ============================================================================
-- 2. INVENTORY TABLES - Real-Time Stock Management
-- ============================================================================

-- Inventory movements tracking (stock in/out history)
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    qty_change INTEGER NOT NULL,  -- Positive: in, Negative: out
    operation TEXT NOT NULL CHECK (operation IN ('sale', 'restock', 'adjustment', 'return')),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_operation ON inventory(operation);
CREATE INDEX IF NOT EXISTS idx_inventory_timestamp ON inventory(created_at);


-- ============================================================================
-- 3. ACTIVITY LOGGING TABLES - Security & Audit Trail
-- ============================================================================

-- Activity logs for security and compliance
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT NOT NULL,
    action TEXT NOT NULL,  -- login, logout, create_transaction, delete_product, etc
    resource_type TEXT,    -- transaction, product, user, etc
    resource_id TEXT,      -- ID of affected resource
    details TEXT,          -- JSON-formatted details
    status TEXT DEFAULT 'success' CHECK (status IN ('success', 'failure')),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_action ON activity_logs(action);
CREATE INDEX IF NOT EXISTS idx_activity_resource ON activity_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_status ON activity_logs(status);


-- ============================================================================
-- 4. ONLINE ORDER TABLES - E-Commerce Support
-- ============================================================================

-- Online orders from e-commerce platforms
CREATE TABLE IF NOT EXISTS online_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_order_id TEXT NOT NULL UNIQUE,  -- Order ID from platform
    platform TEXT NOT NULL,                   -- shopify, woocommerce, tokopedia, shopee, etc
    customer_name TEXT NOT NULL,
    customer_phone TEXT,
    customer_email TEXT,
    shipping_address TEXT,
    items_count INTEGER,
    total INTEGER NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'packed', 'shipped', 'delivered', 'cancelled')),
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    delivery_date DATETIME,
    tracking_number TEXT,
    transaction_id INTEGER,                  -- Link to POS transaction if fulfilled
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_online_orders_external ON online_orders(external_order_id);
CREATE INDEX IF NOT EXISTS idx_online_orders_platform ON online_orders(platform);
CREATE INDEX IF NOT EXISTS idx_online_orders_status ON online_orders(status);
CREATE INDEX IF NOT EXISTS idx_online_orders_customer ON online_orders(customer_email);
CREATE INDEX IF NOT EXISTS idx_online_orders_date ON online_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_online_orders_transaction ON online_orders(transaction_id);


-- ============================================================================
-- 5. ALTER EXISTING TRANSACTIONS TABLE - Multi-Payment Support
-- ============================================================================

-- Add new columns to transactions table to support online orders and multi-payment
-- Note: If you don't want to alter existing table, you can keep using legacy fields

-- Add these columns to transactions table:
-- ALTER TABLE transactions ADD COLUMN channel TEXT DEFAULT 'offline' CHECK (channel IN ('offline', 'online'));
-- ALTER TABLE transactions ADD COLUMN order_id TEXT;
-- ALTER TABLE transactions ADD COLUMN customer_name TEXT;
-- ALTER TABLE transactions ADD COLUMN customer_phone TEXT;
-- ALTER TABLE transactions ADD COLUMN customer_email TEXT;
-- ALTER TABLE transactions ADD COLUMN shipping_address TEXT;
-- ALTER TABLE transactions ADD COLUMN reference_number TEXT UNIQUE;
-- ALTER TABLE transactions ADD COLUMN completed_at DATETIME;

-- NOTE: Since we've updated the Transaction model with these fields,
-- you may need to:
-- 1. Backup existing database
-- 2. Create new tables with updated schema, or
-- 3. Use ALTER TABLE carefully (recommend backup first)


-- ============================================================================
-- 6. MIGRATE DATA - Helper Tables
-- ============================================================================

-- Table to track migration status
CREATE TABLE IF NOT EXISTS migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Record this migration
INSERT OR IGNORE INTO migrations (name) VALUES ('enterprise_features_v1_0');


-- ============================================================================
-- 7. VIEWS - Useful Analytics Views
-- ============================================================================

-- View: Daily Sales Summary
CREATE VIEW IF NOT EXISTS v_daily_sales AS
SELECT
    DATE(t.tanggal) as sale_date,
    COUNT(DISTINCT t.id) as transaction_count,
    COUNT(DISTINCT ti.product_id) as unique_products,
    SUM(ti.qty) as total_items,
    SUM(t.total) as total_revenue,
    SUM(t.total_pajak) as total_tax
FROM transactions t
LEFT JOIN transaction_items ti ON t.id = ti.transaction_id
WHERE t.status IN ('completed', 'paid')
GROUP BY DATE(t.tanggal)
ORDER BY sale_date DESC;


-- View: Product Performance
CREATE VIEW IF NOT EXISTS v_product_performance AS
SELECT
    p.id,
    p.kode,
    p.nama,
    COUNT(DISTINCT ti.transaction_id) as sales_count,
    SUM(ti.qty) as total_qty_sold,
    SUM(ti.qty * ti.harga_satuan) as total_revenue,
    AVG(ti.qty) as avg_qty_per_sale,
    p.stok as current_stock
FROM products p
LEFT JOIN transaction_items ti ON p.id = ti.product_id
GROUP BY p.id
ORDER BY total_revenue DESC;


-- View: Payment Methods Analysis
CREATE VIEW IF NOT EXISTS v_payment_analysis AS
SELECT
    method,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_count,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count
FROM payments
GROUP BY method
ORDER BY total_amount DESC;


-- View: User Activity Summary
CREATE VIEW IF NOT EXISTS v_user_activity AS
SELECT
    user_id,
    username,
    COUNT(*) as total_actions,
    COUNT(CASE WHEN action LIKE '%login%' THEN 1 END) as login_count,
    COUNT(CASE WHEN status = 'failure' THEN 1 END) as failure_count,
    MAX(timestamp) as last_activity
FROM activity_logs
GROUP BY user_id
ORDER BY last_activity DESC;


-- ============================================================================
-- 8. INITIAL DATA - Payment Methods Configuration
-- ============================================================================

-- No initial data needed - handled by PaymentService initialization


-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Next steps:
-- 1. Run this migration: sqlite3 kasir_pos.db < enterprise_features_migration.sql
-- 2. Update service factory to include new repositories
-- 3. Test new services with existing data
-- 4. Update GUI to use multi-payment features
-- 5. Configure e-commerce integrations if needed
