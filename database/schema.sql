-- Track 1 & 2: Civic Resource Prioritization Platform Database Schema
-- Execute this raw SQL in your Supabase SQL Editor

-- 1. Create the Citizens table
CREATE TABLE IF NOT EXISTS citizens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(15) NOT NULL UNIQUE,
    name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create the Wards table (Optional, but good for linking data)
CREATE TABLE IF NOT EXISTS wards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    ward_number INT UNIQUE,
    population INT,
    equity_weight DECIMAL(3, 2) DEFAULT 0.5 -- Ranging from 0.0 to 1.0
);

-- 3. Create the Issues table
CREATE TABLE IF NOT EXISTS issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID REFERENCES citizens(id) ON DELETE SET NULL,
    ward_id UUID REFERENCES wards(id) ON DELETE SET NULL,
    category VARCHAR(50) NOT NULL, -- e.g., 'pothole', 'flooding', 'drainage'
    description TEXT,
    photo_url TEXT,
    phash VARCHAR(64), -- Perceptual hash for deduplication
    lat DECIMAL(9,6),
    lon DECIMAL(9,6),
    status VARCHAR(20) DEFAULT 'OPEN', -- 'OPEN', 'PRIORITIZED', 'DEFERRED', 'SCHEDULED', 'RESOLVED'
    duplicate_of_issue_id UUID REFERENCES issues(id) ON DELETE SET NULL,
    community_multiplier INT DEFAULT 1,
    criteria_scores JSONB, -- Stores the raw criteria weights e.g., {"infra_criticality": [0.7,0.8,0.9], "safety_risk": [0.8,0.9,1.0]}
    topsis_score DECIMAL(5, 4), -- Calculated by the Prioritization engine
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create the Daily Resources table
CREATE TABLE IF NOT EXISTS daily_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_date DATE UNIQUE NOT NULL DEFAULT CURRENT_DATE,
    budget_limit DECIMAL(12, 2) NOT NULL,
    budget_used DECIMAL(12, 2) DEFAULT 0,
    workforce_limit DECIMAL(8, 2) NOT NULL,
    workforce_used DECIMAL(8, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_phash ON issues(phash);
