-- Refine Schema: Drop and Recreate with ENUMs

-- 1. Drop existing tables
DROP TABLE IF EXISTS analysis_results CASCADE;
DROP TABLE IF EXISTS credit_transactions CASCADE;
DROP TABLE IF EXISTS files CASCADE;

-- 2. Create ENUM types
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'file_type_enum') THEN
        CREATE TYPE file_type_enum AS ENUM ('cover', 'secret', 'stego');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'file_status_enum') THEN
        CREATE TYPE file_status_enum AS ENUM ('active', 'expired', 'deleted');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transaction_type_enum') THEN
        CREATE TYPE transaction_type_enum AS ENUM ('usage', 'reward', 'purchase');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'analysis_verdict_enum') THEN
        CREATE TYPE analysis_verdict_enum AS ENUM ('CLEAN', 'SUSPICIOUS', 'DETECTED');
    END IF;
END $$;

-- 3. Recreate Tables
CREATE TABLE files (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename CHARACTER VARYING NOT NULL,
    file_path CHARACTER VARYING NOT NULL,
    file_type file_type_enum NOT NULL,
    status file_status_enum DEFAULT 'active' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,
    transaction_type transaction_type_enum NOT NULL,
    description CHARACTER VARYING,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE analysis_results (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    verdict analysis_verdict_enum DEFAULT 'CLEAN' NOT NULL,
    static_details JSONB,
    confidence_score DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 4. Create Indexes
CREATE INDEX idx_files_user_created ON files(user_id, created_at);
CREATE INDEX idx_credit_trans_user ON credit_transactions(user_id);
CREATE INDEX idx_analysis_results_file ON analysis_results(file_id);
