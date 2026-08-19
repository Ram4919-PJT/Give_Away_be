-- Assistance disbursement tracking

ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS disbursement_reference VARCHAR(100);
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS disbursed_at TIMESTAMP;
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS disbursed_by BIGINT;
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS payment_destination_type VARCHAR(50);
