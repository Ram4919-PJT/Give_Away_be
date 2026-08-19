-- KYC Phase 1: extend verification tables for secure document workflow

CREATE TABLE IF NOT EXISTS verification_requests (
    request_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    request_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
    submitted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verification_documents (
    document_id BIGSERIAL PRIMARY KEY,
    request_id BIGINT NOT NULL REFERENCES verification_requests(request_id) ON DELETE CASCADE,
    document_type VARCHAR(100) NOT NULL,
    file_url VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verification_status_history (
    history_id BIGSERIAL PRIMARY KEY,
    request_id BIGINT NOT NULL REFERENCES verification_requests(request_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    changed_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rejection_reasons (
    reason_id BIGSERIAL PRIMARY KEY,
    request_id BIGINT NOT NULL REFERENCES verification_requests(request_id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS reference_code VARCHAR(32);
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS reviewed_by BIGINT;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS risk_level VARCHAR(32);
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS risk_flags JSONB;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS consent_given BOOLEAN DEFAULT FALSE;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS consent_version VARCHAR(32);
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS payload JSONB;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS current_step BIGINT DEFAULT 1;
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE verification_requests ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS storage_key VARCHAR(512);
ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255);
ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS mime_type VARCHAR(100);
ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS size_bytes BIGINT;
ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS verification_status VARCHAR(50) DEFAULT 'UPLOADED';
ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS rejection_reason TEXT;
ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS verification_source VARCHAR(32) DEFAULT 'MANUAL';
ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS metadata_json JSONB;
ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;
ALTER TABLE verification_documents ADD COLUMN IF NOT EXISTS verified_by BIGINT;

ALTER TABLE verification_status_history ADD COLUMN IF NOT EXISTS note TEXT;
ALTER TABLE verification_status_history ADD COLUMN IF NOT EXISTS changed_by BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_verification_requests_reference_code
    ON verification_requests(reference_code) WHERE reference_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_verification_requests_user_id
    ON verification_requests(user_id);

CREATE INDEX IF NOT EXISTS idx_verification_requests_status
    ON verification_requests(status);

CREATE TABLE IF NOT EXISTS verification_audit_log (
    audit_id BIGSERIAL PRIMARY KEY,
    admin_user_id BIGINT NOT NULL,
    request_id BIGINT NOT NULL,
    action VARCHAR(64) NOT NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_verification_audit_request
    ON verification_audit_log(request_id);

-- Backfill storage_key from legacy file_url where missing
UPDATE verification_documents
SET storage_key = file_url
WHERE storage_key IS NULL AND file_url IS NOT NULL AND file_url <> '';
