-- CRM Database Schema for Cloudflare D1
-- Version 1.0

-- Bảng leads chính
CREATE TABLE IF NOT EXISTS leads (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name        TEXT NOT NULL,
    phone       TEXT,
    email       TEXT,
    facebook_url TEXT,
    zalo_phone  TEXT,
    avatar_url  TEXT,
    industry    TEXT,
    industry_slug TEXT,
    source      TEXT DEFAULT 'manual',
    class       TEXT,
    status      TEXT DEFAULT 'new' CHECK(status IN ('new','contacted','qualified','negotiating','converted','lost')),
    health      TEXT DEFAULT 'green' CHECK(health IN ('green','yellow','red')),
    score       INTEGER DEFAULT 0,
    notes       TEXT DEFAULT '[]',
    tags        TEXT DEFAULT '[]',
    assigned_to TEXT,
    company     TEXT,
    address     TEXT,
    custom_fields TEXT DEFAULT '{}',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now')),
    synced_at   TEXT,
    deleted_at  TEXT
);

-- Index cho tìm kiếm nhanh
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_industry ON leads(industry_slug);

-- Bảng lịch sử tương tác
CREATE TABLE IF NOT EXISTS interactions (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    lead_id     TEXT NOT NULL,
    type        TEXT NOT NULL CHECK(type IN ('call','sms','zalo','facebook_dm','email','note','meeting','purchase')),
    direction   TEXT CHECK(direction IN ('inbound','outbound')),
    content     TEXT,
    duration    INTEGER,
    metadata    TEXT DEFAULT '{}',
    created_by  TEXT DEFAULT 'system',
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_interactions_lead ON interactions(lead_id);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(type);
CREATE INDEX IF NOT EXISTS idx_interactions_created ON interactions(created_at);

-- Bảng pipeline stages (customizable)
CREATE TABLE IF NOT EXISTS pipeline_stages (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    color       TEXT DEFAULT '#6B7280',
    sort_order  INTEGER DEFAULT 0,
    is_default  INTEGER DEFAULT 0
);

-- Bảng products/services
CREATE TABLE IF NOT EXISTS products (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    name        TEXT NOT NULL,
    price       REAL,
    description TEXT,
    active      INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Bảng cấu hình
CREATE TABLE IF NOT EXISTS config (
    key         TEXT PRIMARY KEY,
    value       TEXT,
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- Bảng import logs
CREATE TABLE IF NOT EXISTS import_logs (
    id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(8)))),
    source      TEXT,
    filename    TEXT,
    total_rows  INTEGER,
    imported    INTEGER,
    skipped     INTEGER,
    errors      TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Bảng sessions (for auth)
CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    created_at  TEXT DEFAULT (datetime('now')),
    expires_at  TEXT
);

-- Seed pipeline stages
INSERT OR IGNORE INTO pipeline_stages (id, name, color, sort_order, is_default) VALUES
    ('new', 'Mới', '#3B82F6', 0, 1),
    ('contacted', 'Đã liên hệ', '#F59E0B', 1, 0),
    ('qualified', 'Tiềm năng', '#8B5CF6', 2, 0),
    ('negotiating', 'Đang thương lượng', '#EC4899', 3, 0),
    ('converted', 'Đã chuyển đổi', '#10B981', 4, 0),
    ('lost', 'Đã mất', '#6B7280', 5, 0);

-- Seed default config
INSERT OR IGNORE INTO config (key, value) VALUES
    ('business_name', 'My Business'),
    ('currency', 'VND'),
    ('timezone', 'Asia/Ho_Chi_Minh'),
    ('sync_platform', 'auto'),
    ('telegram_bot_token', ''),
    ('telegram_chat_id', '');
