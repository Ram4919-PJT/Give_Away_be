-- Run against core_mgmt_db when upgrading assistance_applications for admin review fields.

ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS amount_approved NUMERIC(10, 2);
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS category VARCHAR(100);
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS expense_breakdown TEXT;
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS rejection_reason TEXT;
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP;
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS reviewed_by_user_id BIGINT;
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS payout_status VARCHAR(50);
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS bank_account_holder VARCHAR(150);
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS bank_name VARCHAR(150);
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS bank_ifsc VARCHAR(20);
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS bank_account_last4 VARCHAR(4);
ALTER TABLE assistance_applications ADD COLUMN IF NOT EXISTS bank_details_submitted_at TIMESTAMP;
ALTER TABLE assistance_applications ALTER COLUMN purpose TYPE TEXT;
