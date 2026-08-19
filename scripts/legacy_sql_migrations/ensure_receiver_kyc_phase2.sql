-- Receiver KYC Phase 2: mobile OTP table

CREATE TABLE IF NOT EXISTS kyc_mobile_otp (
    otp_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    otp_hash VARCHAR(128) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    attempts BIGINT NOT NULL DEFAULT 0,
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kyc_mobile_otp_user_id ON kyc_mobile_otp(user_id);
