-- ============================================================================
-- GIVE AWAY PLATFORM CONSOLIDATED SEED DATA (10 ROWS PER TABLE)
-- All default passwords set to: password123 
-- Hash: $2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. IDENTITY SERVICE TABLES (5 Tables)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS roles (
    role_id BIGSERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS users (
    user_id BIGSERIAL PRIMARY KEY,
    role_id BIGINT REFERENCES roles(role_id),
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    mobile VARCHAR(20) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    status VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS otp_verifications (
    otp_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    otp_code VARCHAR(10) NOT NULL,
    purpose VARCHAR(50) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified_status VARCHAR(50) DEFAULT 'PENDING'
);

-- Seed roles (5 System Roles + 5 Specialized Role Permutations)
INSERT INTO roles (role_id, role_name, description) VALUES
(1, 'SUPER_ADMIN', 'Platform Administrator with full control'),
(2, 'DONOR', 'Individual or corporate donor'),
(3, 'RECEIVER', 'Individual financial assistance seeker'),
(4, 'NGO_PARTNER', 'Verified NGO partner organization'),
(5, 'GUEST', 'Unauthenticated public site visitor'),
(6, 'AUDITOR', 'Read-only access for financial auditing'),
(7, 'VERIFICATION_OFFICER', 'Admin staff tasked with KYC/Doc review'),
(8, 'INVENTORY_MANAGER', 'Staff responsible for warehouse & item pickup'),
(9, 'FIELD_AGENT', 'On-ground verification agent'),
(10, 'FINANCE_MANAGER', 'Admin staff approving disbursements')
ON CONFLICT (role_id) DO NOTHING;

-- Seed users (10 Users across all roles)
INSERT INTO users (user_id, role_id, full_name, email, mobile, password_hash, status) VALUES
(1, 1, 'System Admin', 'admin@giveaway.org', '+919876543210', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE'),
(2, 2, 'Ananya Sharma', 'ananya.donor@gmail.com', '+919876543211', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE'),
(3, 2, 'Vikram Mehta', 'vikram.donor@yahoo.com', '+919876543212', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE'),
(4, 3, 'Ramesh Kumar', 'ramesh.receiver@gmail.com', '+919876543213', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE'),
(5, 3, 'Sita Devi', 'sita.receiver@gmail.com', '+919876543214', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE'),
(6, 4, 'Hope Foundation', 'contact@hopefoundation.org', '+919876543215', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE'),
(7, 4, 'Care & Share NGO', 'info@careshare.org', '+919876543216', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE'),
(8, 2, 'Rahul Verma', 'rahul.v@gmail.com', '+919876543217', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE'),
(9, 3, 'Gita Rani', 'gita.r@gmail.com', '+919876543218', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE'),
(10, 4, 'Smile Trust', 'help@smiletrust.org', '+919876543219', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW', 'ACTIVE')
ON CONFLICT (user_id) DO NOTHING;

-- Seed refresh_tokens (10 Rows)
INSERT INTO refresh_tokens (token_id, user_id, token, expires_at) VALUES
(1, 1, 'token_admin_1001', NOW() + INTERVAL '7 days'),
(2, 2, 'token_donor_1002', NOW() + INTERVAL '7 days'),
(3, 3, 'token_donor_1003', NOW() + INTERVAL '7 days'),
(4, 4, 'token_receiver_1004', NOW() + INTERVAL '7 days'),
(5, 5, 'token_receiver_1005', NOW() + INTERVAL '7 days'),
(6, 6, 'token_ngo_1006', NOW() + INTERVAL '7 days'),
(7, 7, 'token_ngo_1007', NOW() + INTERVAL '7 days'),
(8, 8, 'token_donor_1008', NOW() + INTERVAL '7 days'),
(9, 9, 'token_receiver_1009', NOW() + INTERVAL '7 days'),
(10, 10, 'token_ngo_1010', NOW() + INTERVAL '7 days')
ON CONFLICT (token_id) DO NOTHING;

-- Seed login_audit (10 Rows)
INSERT INTO login_audit (audit_id, user_id, ip_address, status) VALUES
(1, 1, '192.168.1.1', 'SUCCESS'),
(2, 2, '192.168.1.2', 'SUCCESS'),
(3, 3, '192.168.1.3', 'SUCCESS'),
(4, 4, '192.168.1.4', 'SUCCESS'),
(5, 5, '192.168.1.5', 'FAILED'),
(6, 6, '192.168.1.6', 'SUCCESS'),
(7, 7, '192.168.1.7', 'SUCCESS'),
(8, 8, '192.168.1.8', 'SUCCESS'),
(9, 9, '192.168.1.9', 'FAILED'),
(10, 10, '192.168.1.10', 'SUCCESS')
ON CONFLICT (audit_id) DO NOTHING;

-- Seed otp_verifications (10 Rows)
INSERT INTO otp_verifications (otp_id, user_id, otp_code, purpose, expires_at, verified_status) VALUES
(1, 1, '111111', 'LOGIN', NOW() + INTERVAL '10 mins', 'VERIFIED'),
(2, 2, '222222', 'REGISTRATION', NOW() + INTERVAL '10 mins', 'VERIFIED'),
(3, 3, '333333', 'PASSWORD_RESET', NOW() + INTERVAL '10 mins', 'VERIFIED'),
(4, 4, '444444', 'REGISTRATION', NOW() + INTERVAL '10 mins', 'VERIFIED'),
(5, 5, '555555', 'PASSWORD_RESET', NOW() + INTERVAL '10 mins', 'PENDING'),
(6, 6, '666666', 'REGISTRATION', NOW() + INTERVAL '10 mins', 'VERIFIED'),
(7, 7, '777777', 'REGISTRATION', NOW() + INTERVAL '10 mins', 'PENDING'),
(8, 8, '888888', 'LOGIN', NOW() + INTERVAL '10 mins', 'VERIFIED'),
(9, 9, '999999', 'PASSWORD_RESET', NOW() + INTERVAL '10 mins', 'PENDING'),
(10, 10, '101010', 'REGISTRATION', NOW() + INTERVAL '10 mins', 'VERIFIED')
ON CONFLICT (otp_id) DO NOTHING;


-- ----------------------------------------------------------------------------
-- 2. PROFILE & VERIFICATION SERVICE TABLES (10 Tables)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS addresses (
    address_id BIGSERIAL PRIMARY KEY,
    line1 TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS donor_profiles (
    donor_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(user_id),
    full_name VARCHAR(100) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    email VARCHAR(100) NOT NULL,
    address_id BIGINT REFERENCES addresses(address_id)
);

CREATE TABLE IF NOT EXISTS receiver_profiles (
    receiver_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(user_id),
    full_name VARCHAR(100) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    email VARCHAR(100) NOT NULL,
    address_id BIGINT REFERENCES addresses(address_id),
    verification_status VARCHAR(50) DEFAULT 'REGISTERED'
);

CREATE TABLE IF NOT EXISTS ngo_profiles (
    ngo_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(user_id),
    ngo_name VARCHAR(150) NOT NULL,
    registration_number VARCHAR(100) NOT NULL UNIQUE,
    contact_person VARCHAR(100) NOT NULL,
    mobile VARCHAR(20) NOT NULL,
    address_id BIGINT REFERENCES addresses(address_id),
    verification_status VARCHAR(50) DEFAULT 'REGISTERED'
);

CREATE TABLE IF NOT EXISTS beneficiaries (
    beneficiary_id BIGSERIAL PRIMARY KEY,
    ngo_id BIGINT REFERENCES ngo_profiles(ngo_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS programs (
    program_id BIGSERIAL PRIMARY KEY,
    program_name VARCHAR(150) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS verification_requests (
    request_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    request_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verification_documents (
    document_id BIGSERIAL PRIMARY KEY,
    request_id BIGINT REFERENCES verification_requests(request_id) ON DELETE CASCADE,
    document_type VARCHAR(100) NOT NULL,
    file_url VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verification_status_history (
    history_id BIGSERIAL PRIMARY KEY,
    request_id BIGINT REFERENCES verification_requests(request_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rejection_reasons (
    reason_id BIGSERIAL PRIMARY KEY,
    request_id BIGINT REFERENCES verification_requests(request_id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed addresses (10 Rows)
INSERT INTO addresses (address_id, line1, city, state, pincode) VALUES
(1, 'Plot 42, Jubilee Hills', 'Hyderabad', 'Telangana', '500033'),
(2, 'Flat 302, MG Road', 'Bengaluru', 'Karnataka', '560001'),
(3, 'H.No 12-3, Slum Rehab Area', 'Hyderabad', 'Telangana', '500018'),
(4, 'Door No 5-9, Rural Mandal', 'Warangal', 'Telangana', '506001'),
(5, 'Building 10B, NGO Colony', 'Hyderabad', 'Telangana', '500070'),
(6, 'Suite 400, Social Care Complex', 'Chennai', 'Tamil Nadu', '600001'),
(7, '12 Park Avenue', 'Mumbai', 'Maharashtra', '400001'),
(8, 'Street 9, Sector 4', 'Noida', 'Uttar Pradesh', '201301'),
(9, 'Village Rampur, PO Box 12', 'Guntur', 'Andhra Pradesh', '522001'),
(10, '55 City Center', 'Kolkata', 'West Bengal', '700001')
ON CONFLICT (address_id) DO NOTHING;

-- Seed donor_profiles (10 Rows)
INSERT INTO donor_profiles (donor_id, user_id, full_name, mobile, email, address_id) VALUES
(1, 2, 'Ananya Sharma', '+919876543211', 'ananya.donor@gmail.com', 1),
(2, 3, 'Vikram Mehta', '+919876543212', 'vikram.donor@yahoo.com', 2),
(3, 8, 'Rahul Verma', '+919876543217', 'rahul.v@gmail.com', 7),
(4, 1, 'Admin Extra Donor', '+919876543210', 'admin.d@giveaway.org', 1),
(5, 4, 'Receiver Donor Cross', '+919876543213', 'ramesh.d@gmail.com', 3),
(6, 5, 'Sita Donor Cross', '+919876543214', 'sita.d@gmail.com', 4),
(7, 6, 'Hope Donor Cross', '+919876543215', 'hope.d@hopefoundation.org', 5),
(8, 7, 'Care Donor Cross', '+919876543216', 'care.d@careshare.org', 6),
(9, 9, 'Gita Donor Cross', '+919876543218', 'gita.d@gmail.com', 9),
(10, 10, 'Smile Donor Cross', '+919876543219', 'smile.d@smiletrust.org', 10)
ON CONFLICT (donor_id) DO NOTHING;

-- Seed receiver_profiles (10 Rows)
INSERT INTO receiver_profiles (receiver_id, user_id, full_name, mobile, email, address_id, verification_status) VALUES
(1, 4, 'Ramesh Kumar', '+919876543213', 'ramesh.receiver@gmail.com', 3, 'VERIFIED'),
(2, 5, 'Sita Devi', '+919876543214', 'sita.receiver@gmail.com', 4, 'DOCUMENTS_SUBMITTED'),
(3, 9, 'Gita Rani', '+919876543218', 'gita.r@gmail.com', 9, 'UNDER_REVIEW'),
(4, 1, 'Dummy Rec 1', '+919800000001', 'rec1@test.com', 1, 'REGISTERED'),
(5, 2, 'Dummy Rec 2', '+919800000002', 'rec2@test.com', 2, 'VERIFIED'),
(6, 3, 'Dummy Rec 3', '+919800000003', 'rec3@test.com', 5, 'REJECTED'),
(7, 6, 'Dummy Rec 4', '+919800000004', 'rec4@test.com', 6, 'VERIFIED'),
(8, 7, 'Dummy Rec 5', '+919800000005', 'rec5@test.com', 7, 'REGISTERED'),
(9, 8, 'Dummy Rec 6', '+919800000006', 'rec6@test.com', 8, 'UNDER_REVIEW'),
(10, 10, 'Dummy Rec 7', '+919800000007', 'rec7@test.com', 10, 'VERIFIED')
ON CONFLICT (receiver_id) DO NOTHING;

-- Seed ngo_profiles (10 Rows)
INSERT INTO ngo_profiles (ngo_id, user_id, ngo_name, registration_number, contact_person, mobile, address_id, verification_status) VALUES
(1, 6, 'Hope Foundation', 'NGO-REG-2021-9981', 'Dr. Rajesh Rao', '+919876543215', 5, 'VERIFIED'),
(2, 7, 'Care & Share NGO', 'NGO-REG-2023-4412', 'Sunita Reddy', '+919876543216', 6, 'UNDER_REVIEW'),
(3, 10, 'Smile Trust', 'NGO-REG-2022-1109', 'Amitabh Das', '+919876543219', 10, 'VERIFIED'),
(4, 1, 'NGO Alpha', 'NGO-REG-2020-0001', 'Contact Alpha', '+919900000001', 1, 'VERIFIED'),
(5, 2, 'NGO Beta', 'NGO-REG-2020-0002', 'Contact Beta', '+919900000002', 2, 'REJECTED'),
(6, 3, 'NGO Gamma', 'NGO-REG-2020-0003', 'Contact Gamma', '+919900000003', 3, 'UNDER_REVIEW'),
(7, 4, 'NGO Delta', 'NGO-REG-2020-0004', 'Contact Delta', '+919900000004', 4, 'REGISTERED'),
(8, 5, 'NGO Epsilon', 'NGO-REG-2020-0005', 'Contact Epsilon', '+919900000005', 7, 'VERIFIED'),
(9, 8, 'NGO Zeta', 'NGO-REG-2020-0006', 'Contact Zeta', '+919900000006', 8, 'REGISTERED'),
(10, 9, 'NGO Eta', 'NGO-REG-2020-0007', 'Contact Eta', '+919900000007', 9, 'VERIFIED')
ON CONFLICT (ngo_id) DO NOTHING;

-- Seed beneficiaries (10 Rows)
INSERT INTO beneficiaries (beneficiary_id, ngo_id, name, age, details) VALUES
(1, 1, 'Aarav Kumar', 8, 'Orphaned child pursuing primary education.'),
(2, 1, 'Priya Singh', 12, 'Requires hearing assistance device.'),
(3, 2, 'Lakshmi Ammal', 68, 'Elderly destitute resident receiving food support.'),
(4, 3, 'Kabir Khan', 10, 'Cancer treatment support recipient.'),
(5, 1, 'Suresh Babu', 45, 'Physically disabled vocational trainee.'),
(6, 2, 'Meena Kumari', 15, 'Secondary school scholarship recipient.'),
(7, 3, 'Ravi Teja', 6, 'Malnutrition rehabilitation participant.'),
(8, 4, 'Deepa Roy', 30, 'Skill development program beneficiary.'),
(9, 5, 'Anil Kapoor', 50, 'Disaster relief shelter resident.'),
(10, 8, 'Sunil Dutt', 11, 'Rural library initiative beneficiary.')
ON CONFLICT (beneficiary_id) DO NOTHING;

-- Seed programs (10 Rows)
INSERT INTO programs (program_id, program_name, description, category, status) VALUES
(1, 'Child Healthcare Emergency', 'Medical relief fund for urgent pediatric surgeries.', 'Medical', 'ACTIVE'),
(2, 'Rural Education & Books Drive', 'Books and uniforms for government school kids.', 'Education', 'ACTIVE'),
(3, 'Winter Blanket & Clothes Distribution', 'Warm clothing distribution to homeless.', 'Relief', 'ACTIVE'),
(4, 'Elderly Medical Assistance Pool', 'Monthly medication support for destitute seniors.', 'Medical', 'ACTIVE'),
(5, 'Clean Water Project', 'Water purifier installation in rural schools.', 'Infrastructure', 'ACTIVE'),
(6, 'Disaster Food Packet Supply', 'Emergency dry ration distribution.', 'Relief', 'ACTIVE'),
(7, 'Women Empowerment Skills', 'Tailoring and craft training center funds.', 'Vocational', 'ACTIVE'),
(8, 'Orphanage Digital Classroom', 'Computers and internet for orphanages.', 'Education', 'ACTIVE'),
(9, 'Blind Student Audiobooks Drive', 'Recording and distribution of audiobooks.', 'Disability', 'INACTIVE'),
(10, 'Slum Sanitation Drive', 'Public toilet construction and hygiene kits.', 'Sanitation', 'ACTIVE')
ON CONFLICT (program_id) DO NOTHING;

-- Seed verification_requests (10 Rows)
INSERT INTO verification_requests (request_id, user_id, request_type, status, submitted_at) VALUES
(1, 4, 'RECEIVER', 'VERIFIED', NOW() - INTERVAL '5 days'),
(2, 5, 'RECEIVER', 'UNDER_REVIEW', NOW() - INTERVAL '2 days'),
(3, 6, 'NGO', 'VERIFIED', NOW() - INTERVAL '10 days'),
(4, 7, 'NGO', 'UNDER_REVIEW', NOW() - INTERVAL '1 day'),
(5, 9, 'RECEIVER', 'UNDER_REVIEW', NOW() - INTERVAL '3 days'),
(6, 10, 'NGO', 'VERIFIED', NOW() - INTERVAL '12 days'),
(7, 2, 'DONOR', 'VERIFIED', NOW() - INTERVAL '20 days'),
(8, 3, 'DONOR', 'VERIFIED', NOW() - INTERVAL '18 days'),
(9, 8, 'DONOR', 'VERIFIED', NOW() - INTERVAL '15 days'),
(10, 5, 'RECEIVER', 'REJECTED', NOW() - INTERVAL '30 days')
ON CONFLICT (request_id) DO NOTHING;

-- Seed verification_documents (10 Rows)
INSERT INTO verification_documents (document_id, request_id, document_type, file_url) VALUES
(1, 1, 'AADHAR_CARD', 'https://s3.amazonaws.com/giveaway/docs/rec_4_aadhar.pdf'),
(2, 1, 'INCOME_CERTIFICATE', 'https://s3.amazonaws.com/giveaway/docs/rec_4_income.pdf'),
(3, 2, 'MEDICAL_BILL', 'https://s3.amazonaws.com/giveaway/docs/rec_5_hospital.pdf'),
(4, 3, 'NGO_DARPAN_CERTIFICATE', 'https://s3.amazonaws.com/giveaway/docs/ngo_6_darpan.pdf'),
(5, 4, 'TRUST_DEED', 'https://s3.amazonaws.com/giveaway/docs/ngo_7_trust.pdf'),
(6, 5, 'AADHAR_CARD', 'https://s3.amazonaws.com/giveaway/docs/rec_9_aadhar.pdf'),
(7, 6, '80G_CERTIFICATE', 'https://s3.amazonaws.com/giveaway/docs/ngo_10_80g.pdf'),
(8, 7, 'PAN_CARD', 'https://s3.amazonaws.com/giveaway/docs/donor_2_pan.pdf'),
(9, 8, 'PAN_CARD', 'https://s3.amazonaws.com/giveaway/docs/donor_3_pan.pdf'),
(10, 10, 'INVALID_DOC', 'https://s3.amazonaws.com/giveaway/docs/rec_5_invalid.pdf')
ON CONFLICT (document_id) DO NOTHING;

-- Seed verification_status_history (10 Rows)
INSERT INTO verification_status_history (history_id, request_id, status) VALUES
(1, 1, 'REGISTERED'),
(2, 1, 'DOCUMENTS_SUBMITTED'),
(3, 1, 'VERIFIED'),
(4, 2, 'REGISTERED'),
(5, 2, 'DOCUMENTS_SUBMITTED'),
(6, 3, 'VERIFIED'),
(7, 4, 'UNDER_REVIEW'),
(8, 5, 'UNDER_REVIEW'),
(9, 6, 'VERIFIED'),
(10, 10, 'REJECTED')
ON CONFLICT (history_id) DO NOTHING;

-- Seed rejection_reasons (10 Rows)
INSERT INTO rejection_reasons (reason_id, request_id, reason) VALUES
(1, 10, 'Expired document provided. Needs updated income proof.'),
(2, 10, 'Blurry document image. Details unreadable.'),
(3, 4, 'Trust deed missing page number 4.'),
(4, 2, 'Income certificate name mismatched with Aadhar.'),
(5, 5, 'Bank passbook copy missing account number.'),
(6, 10, 'Duplicate application detected.'),
(7, 4, 'FCRA registration number invalid.'),
(8, 2, 'Aadhar card copy expired or unverified.'),
(9, 5, 'Medical estimate bill missing doctor official seal.'),
(10, 10, 'Provided PAN card belongs to a different individual.')
ON CONFLICT (reason_id) DO NOTHING;


-- ----------------------------------------------------------------------------
-- 3. CORE CHARITY SERVICE TABLES (14 Tables)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fund_pools (
    pool_id BIGSERIAL PRIMARY KEY,
    pool_name VARCHAR(150) NOT NULL,
    balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00
);

CREATE TABLE IF NOT EXISTS money_donations (
    donation_id BIGSERIAL PRIMARY KEY,
    donor_id BIGINT NOT NULL REFERENCES donor_profiles(donor_id),
    program_id BIGINT NOT NULL REFERENCES programs(program_id),
    amount DECIMAL(10, 2) NOT NULL,
    payment_status VARCHAR(50) NOT NULL DEFAULT 'INITIATED',
    donated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS item_donations (
    item_donation_id BIGSERIAL PRIMARY KEY,
    donor_id BIGINT NOT NULL REFERENCES donor_profiles(donor_id),
    category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    quantity INT NOT NULL,
    pickup_address_id BIGINT NOT NULL REFERENCES addresses(address_id),
    status VARCHAR(50) NOT NULL DEFAULT 'LISTED'
);

CREATE TABLE IF NOT EXISTS assistance_applications (
    application_id BIGSERIAL PRIMARY KEY,
    receiver_id BIGINT NOT NULL REFERENCES receiver_profiles(receiver_id),
    purpose VARCHAR(255) NOT NULL,
    amount_requested DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ngo_item_requests (
    request_id BIGSERIAL PRIMARY KEY,
    ngo_id BIGINT NOT NULL REFERENCES ngo_profiles(ngo_id),
    item_category VARCHAR(100) NOT NULL,
    quantity_requested INT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED'
);

CREATE TABLE IF NOT EXISTS ngo_fund_requests (
    request_id BIGSERIAL PRIMARY KEY,
    ngo_id BIGINT NOT NULL REFERENCES ngo_profiles(ngo_id),
    amount_requested DECIMAL(10, 2) NOT NULL,
    purpose TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'SUBMITTED'
);

CREATE TABLE IF NOT EXISTS donation_status_history (
    history_id BIGSERIAL PRIMARY KEY,
    donation_id BIGINT NOT NULL,
    donation_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS application_status_history (
    history_id BIGSERIAL PRIMARY KEY,
    application_id BIGINT REFERENCES assistance_applications(application_id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_items (
    item_id BIGSERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    status VARCHAR(50) DEFAULT 'IN_STOCK'
);

CREATE TABLE IF NOT EXISTS inventory_transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    item_id BIGINT REFERENCES inventory_items(item_id),
    transaction_type VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pickup_schedules (
    pickup_id BIGSERIAL PRIMARY KEY,
    item_donation_id BIGINT REFERENCES item_donations(item_donation_id) ON DELETE CASCADE,
    pickup_date DATE NOT NULL,
    pickup_time TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'SCHEDULED'
);

CREATE TABLE IF NOT EXISTS fund_ledger (
    ledger_id BIGSERIAL PRIMARY KEY,
    pool_id BIGINT REFERENCES fund_pools(pool_id),
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS disbursements (
    disbursement_id BIGSERIAL PRIMARY KEY,
    application_id BIGINT REFERENCES assistance_applications(application_id),
    amount DECIMAL(10, 2) NOT NULL,
    disbursed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'COMPLETED'
);

CREATE TABLE IF NOT EXISTS allocations (
    allocation_id BIGSERIAL PRIMARY KEY,
    ngo_request_id BIGINT REFERENCES ngo_item_requests(request_id),
    item_id BIGINT REFERENCES inventory_items(item_id),
    quantity_allocated INT NOT NULL,
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed fund_pools (10 Rows)
INSERT INTO fund_pools (pool_id, pool_name, balance) VALUES
(1, 'General Emergency Medical Pool', 150000.00),
(2, 'Education & Literacy Pool', 85000.00),
(3, 'Disaster Relief Pool', 50000.00),
(4, 'Elderly Care Fund', 30000.00),
(5, 'Clean Water Initiative', 45000.00),
(6, 'Women Empowerment Fund', 20000.00),
(7, 'Orphan Welfare Reserve', 60000.00),
(8, 'Sanitation & Hygiene Pool', 15000.00),
(9, 'Animal Welfare Pool', 10000.00),
(10, 'General Unrestricted Fund', 250000.00)
ON CONFLICT (pool_id) DO NOTHING;

-- Seed money_donations (10 Rows)
INSERT INTO money_donations (donation_id, donor_id, program_id, amount, payment_status) VALUES
(1, 1, 1, 50000.00, 'CONFIRMED'),
(2, 2, 2, 10000.00, 'CONFIRMED'),
(3, 1, 3, 25000.00, 'PAYMENT_PENDING'),
(4, 3, 4, 15000.00, 'CONFIRMED'),
(5, 1, 5, 5000.00, 'FAILED'),
(6, 2, 6, 20000.00, 'CONFIRMED'),
(7, 3, 7, 12000.00, 'CONFIRMED'),
(8, 1, 8, 8000.00, 'CONFIRMED'),
(9, 2, 9, 3000.00, 'INITIATED'),
(10, 3, 10, 50000.00, 'CONFIRMED')
ON CONFLICT (donation_id) DO NOTHING;

-- Seed item_donations (10 Rows)
INSERT INTO item_donations (item_donation_id, donor_id, category, description, quantity, pickup_address_id, status) VALUES
(1, 1, 'Clothing', 'Warm winter jackets and sweaters', 50, 1, 'RECEIVED'),
(2, 2, 'Electronics', 'Refurbished Laptops for students', 10, 2, 'PICKUP_SCHEDULED'),
(3, 1, 'Medical Supplies', 'First Aid Kits and Wheelchairs', 5, 1, 'LISTED'),
(4, 3, 'Books', 'Primary School Textbooks Set', 100, 7, 'RECEIVED'),
(5, 1, 'Food Packs', 'Rice and Pulses 5kg Bags', 40, 1, 'RECEIVED'),
(6, 2, 'Furniture', 'Study Tables for Orphanage', 15, 2, 'LISTED'),
(7, 3, 'Toys', 'Children Learning Toys', 30, 7, 'PICKUP_SCHEDULED'),
(8, 1, 'Blankets', 'Woolen Blankets', 60, 1, 'RECEIVED'),
(9, 2, 'Footwear', 'School Shoes', 50, 2, 'LISTED'),
(10, 3, 'Utensils', 'Kitchen Utensils Set', 20, 7, 'RECEIVED')
ON CONFLICT (item_donation_id) DO NOTHING;

-- Seed assistance_applications (10 Rows)
INSERT INTO assistance_applications (application_id, receiver_id, purpose, amount_requested, status) VALUES
(1, 1, 'Kidney Dialysis Medical Relief', 30000.00, 'APPROVED'),
(2, 2, 'Children School Tuition Fees Assistance', 15000.00, 'UNDER_REVIEW'),
(3, 3, 'Heart Surgery Fund Request', 75000.00, 'SUBMITTED'),
(4, 4, 'House Repair Post Flood', 25000.00, 'APPROVED'),
(5, 5, 'Wheelchair Purchase Request', 10000.00, 'COMPLETED'),
(6, 6, 'Higher Education College Fee', 40000.00, 'REJECTED'),
(7, 7, 'Cancer Treatment Support', 60000.00, 'APPROVED'),
(8, 8, 'Monthly Grocery Aid', 5000.00, 'APPROVED'),
(9, 9, 'Hearing Aid Support', 12000.00, 'UNDER_REVIEW'),
(10, 10, 'Emergency Funeral Expenses', 8000.00, 'COMPLETED')
ON CONFLICT (application_id) DO NOTHING;

-- Seed ngo_item_requests (10 Rows)
INSERT INTO ngo_item_requests (request_id, ngo_id, item_category, quantity_requested, status) VALUES
(1, 1, 'Clothing', 20, 'APPROVED'),
(2, 2, 'Electronics', 5, 'UNDER_REVIEW'),
(3, 3, 'Books', 50, 'APPROVED'),
(4, 1, 'Food Packs', 30, 'COMPLETED'),
(5, 2, 'Blankets', 40, 'APPROVED'),
(6, 3, 'Furniture', 10, 'SUBMITTED'),
(7, 4, 'Medical Supplies', 5, 'APPROVED'),
(8, 5, 'Footwear', 25, 'UNDER_REVIEW'),
(9, 8, 'Toys', 15, 'REJECTED'),
(10, 10, 'Utensils', 10, 'APPROVED')
ON CONFLICT (request_id) DO NOTHING;

-- Seed ngo_fund_requests (10 Rows)
INSERT INTO ngo_fund_requests (request_id, ngo_id, amount_requested, purpose, status) VALUES
(1, 1, 40000.00, 'Community Health Camp Medical Setup', 'APPROVED'),
(2, 2, 20000.00, 'Homeless Shelter Food Drive Supply', 'SUBMITTED'),
(3, 3, 50000.00, 'School Building Roof Repair', 'APPROVED'),
(4, 4, 15000.00, 'Free Medical Checkup Camp', 'UNDER_REVIEW'),
(5, 5, 30000.00, 'Women Vocational Center Sewing Machines', 'APPROVED'),
(6, 6, 10000.00, 'Tree Plantation Drive', 'REJECTED'),
(7, 7, 25000.00, 'Slum Nutrition Awareness Camp', 'SUBMITTED'),
(8, 8, 60000.00, 'Orphanage Winter Cloth Drive', 'APPROVED'),
(9, 9, 18000.00, 'Elderly Health Kit Distribution', 'UNDER_REVIEW'),
(10, 10, 35000.00, 'Clean Drinking Water Tank Installation', 'APPROVED')
ON CONFLICT (request_id) DO NOTHING;

-- Seed donation_status_history (10 Rows)
INSERT INTO donation_status_history (history_id, donation_id, donation_type, status) VALUES
(1, 1, 'MONEY', 'INITIATED'),
(2, 1, 'MONEY', 'CONFIRMED'),
(3, 2, 'MONEY', 'CONFIRMED'),
(4, 3, 'MONEY', 'PAYMENT_PENDING'),
(5, 1, 'ITEM', 'LISTED'),
(6, 1, 'ITEM', 'RECEIVED'),
(7, 2, 'ITEM', 'PICKUP_SCHEDULED'),
(8, 4, 'ITEM', 'RECEIVED'),
(9, 5, 'ITEM', 'RECEIVED'),
(10, 8, 'ITEM', 'RECEIVED')
ON CONFLICT (history_id) DO NOTHING;

-- Seed application_status_history (10 Rows)
INSERT INTO application_status_history (history_id, application_id, status) VALUES
(1, 1, 'SUBMITTED'),
(2, 1, 'UNDER_REVIEW'),
(3, 1, 'APPROVED'),
(4, 2, 'SUBMITTED'),
(5, 2, 'UNDER_REVIEW'),
(6, 4, 'APPROVED'),
(7, 5, 'COMPLETED'),
(8, 6, 'REJECTED'),
(9, 7, 'APPROVED'),
(10, 10, 'COMPLETED')
ON CONFLICT (history_id) DO NOTHING;

-- Seed inventory_items (10 Rows)
INSERT INTO inventory_items (item_id, category, description, quantity, status) VALUES
(1, 'Clothing', 'Warm Winter Jackets', 30, 'IN_STOCK'),
(2, 'Electronics', 'Refurbished Laptops', 0, 'OUT_OF_STOCK'),
(3, 'Medical Supplies', 'Wheelchairs', 5, 'IN_STOCK'),
(4, 'Books', 'Primary Textbooks', 50, 'IN_STOCK'),
(5, 'Food Packs', 'Rice Bags 5kg', 10, 'IN_STOCK'),
(6, 'Furniture', 'Study Chairs', 15, 'IN_STOCK'),
(7, 'Toys', 'Board Games', 30, 'IN_STOCK'),
(8, 'Blankets', 'Woolen Blankets', 20, 'IN_STOCK'),
(9, 'Footwear', 'Leather Shoes', 50, 'IN_STOCK'),
(10, 'Utensils', 'Steel Plates', 10, 'IN_STOCK')
ON CONFLICT (item_id) DO NOTHING;

-- Seed inventory_transactions (10 Rows)
INSERT INTO inventory_transactions (transaction_id, item_id, transaction_type, quantity) VALUES
(1, 1, 'IN', 50),
(2, 1, 'OUT', 20),
(3, 3, 'IN', 5),
(4, 4, 'IN', 100),
(5, 4, 'OUT', 50),
(6, 5, 'IN', 40),
(7, 5, 'OUT', 30),
(8, 8, 'IN', 60),
(9, 8, 'OUT', 40),
(10, 10, 'IN', 20)
ON CONFLICT (transaction_id) DO NOTHING;

-- Seed pickup_schedules (10 Rows)
INSERT INTO pickup_schedules (pickup_id, item_donation_id, pickup_date, pickup_time, status) VALUES
(1, 1, CURRENT_DATE - INTERVAL '2 days', '10:00:00', 'COMPLETED'),
(2, 2, CURRENT_DATE + INTERVAL '1 day', '10:30:00', 'SCHEDULED'),
(3, 3, CURRENT_DATE + INTERVAL '2 days', '11:00:00', 'SCHEDULED'),
(4, 4, CURRENT_DATE - INTERVAL '5 days', '14:00:00', 'COMPLETED'),
(5, 5, CURRENT_DATE - INTERVAL '3 days', '15:30:00', 'COMPLETED'),
(6, 6, CURRENT_DATE + INTERVAL '3 days', '09:00:00', 'SCHEDULED'),
(7, 7, CURRENT_DATE + INTERVAL '1 day', '16:00:00', 'SCHEDULED'),
(8, 8, CURRENT_DATE - INTERVAL '1 day', '12:00:00', 'COMPLETED'),
(9, 9, CURRENT_DATE + INTERVAL '4 days', '11:30:00', 'SCHEDULED'),
(10, 10, CURRENT_DATE - INTERVAL '4 days', '10:00:00', 'COMPLETED')
ON CONFLICT (pickup_id) DO NOTHING;

-- Seed fund_ledger (10 Rows)
INSERT INTO fund_ledger (ledger_id, pool_id, transaction_type, amount) VALUES
(1, 1, 'CREDIT', 50000.00),
(2, 2, 'CREDIT', 10000.00),
(3, 1, 'DEBIT', 30000.00),
(4, 3, 'CREDIT', 25000.00),
(5, 4, 'CREDIT', 15000.00),
(6, 6, 'CREDIT', 20000.00),
(7, 7, 'CREDIT', 12000.00),
(8, 8, 'CREDIT', 8000.00),
(9, 10, 'CREDIT', 50000.00),
(10, 4, 'DEBIT', 10000.00)
ON CONFLICT (ledger_id) DO NOTHING;

-- Seed disbursements (10 Rows)
INSERT INTO disbursements (disbursement_id, application_id, amount, status) VALUES
(1, 1, 30000.00, 'COMPLETED'),
(2, 4, 25000.00, 'COMPLETED'),
(3, 5, 10000.00, 'COMPLETED'),
(4, 7, 60000.00, 'PENDING_BANK_TRANSFER'),
(5, 8, 5000.00, 'COMPLETED'),
(6, 10, 8000.00, 'COMPLETED'),
(7, 1, 5000.00, 'COMPLETED'),
(8, 4, 5000.00, 'COMPLETED'),
(9, 7, 10000.00, 'PROCESSING'),
(10, 5, 2000.00, 'COMPLETED')
ON CONFLICT (disbursement_id) DO NOTHING;

-- Seed allocations (10 Rows)
INSERT INTO allocations (allocation_id, ngo_request_id, item_id, quantity_allocated) VALUES
(1, 1, 1, 20),
(2, 3, 4, 50),
(3, 4, 5, 30),
(4, 5, 8, 40),
(5, 7, 3, 5),
(6, 10, 10, 10),
(7, 1, 1, 10),
(8, 3, 4, 20),
(9, 4, 5, 10),
(10, 5, 8, 10)
ON CONFLICT (allocation_id) DO NOTHING;


-- ----------------------------------------------------------------------------
-- 4. NOTIFICATION SERVICE TABLES (4 Tables)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'UNREAD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notification_templates (
    template_id BIGSERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL UNIQUE,
    channel VARCHAR(50) NOT NULL,
    content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_delivery_logs (
    log_id BIGSERIAL PRIMARY KEY,
    notification_id BIGINT REFERENCES notifications(notification_id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL,
    delivery_status VARCHAR(50) NOT NULL,
    delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_notification_preferences (
    preference_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    channel VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE
);

-- Seed notifications (10 Rows)
INSERT INTO notifications (notification_id, user_id, title, message, status) VALUES
(1, 2, 'Donation Received', 'Thank you for donating INR 10,000 to Education Pool.', 'READ'),
(2, 4, 'Application Update', 'Your financial assistance request #1 has been approved.', 'UNREAD'),
(3, 6, 'Item Allocation', '20 jackets have been allocated to your NGO request.', 'UNREAD'),
(4, 3, 'Pickup Scheduled', 'Item pickup scheduled for tomorrow at 10:30 AM.', 'READ'),
(5, 5, 'Doc Required', 'Please upload your updated medical bills.', 'UNREAD'),
(6, 7, 'NGO Under Review', 'Your NGO documents are currently under review.', 'READ'),
(7, 1, 'System Alert', 'New NGO registration submitted for review.', 'UNREAD'),
(8, 8, 'Donation Receipt', 'Receipt generated for INR 12,000 contribution.', 'READ'),
(9, 9, 'KYC Pending', 'Complete your profile verification.', 'UNREAD'),
(10, 10, 'Fund Approved', 'Fund request for INR 35,000 has been approved.', 'UNREAD')
ON CONFLICT (notification_id) DO NOTHING;

-- Seed notification_templates (10 Rows)
INSERT INTO notification_templates (template_id, template_name, channel, content) VALUES
(1, 'DONATION_CONFIRMED', 'EMAIL', 'Dear Donor, Thank you! Your donation of INR {{amount}} has been confirmed.'),
(2, 'PICKUP_SCHEDULED', 'SMS', 'Your item pickup is scheduled on {{date}} at {{time}}.'),
(3, 'ASSISTANCE_APPROVED', 'PUSH', 'Your application for assistance #{{app_id}} has been APPROVED.'),
(4, 'NGO_VERIFIED', 'EMAIL', 'Congratulations! Your NGO profile has been successfully verified.'),
(5, 'DOC_REJECTED', 'SMS', 'Your verification doc was rejected. Reason: {{reason}}'),
(6, 'OTP_CODE', 'SMS', 'Your OTP for Giveaway platform login is {{otp}}'),
(7, 'DISBURSEMENT_SENT', 'PUSH', 'Financial aid of INR {{amount}} transferred to your account.'),
(8, 'ITEM_ALLOCATED', 'IN_APP', 'Requested item {{item_name}} allocated to your NGO.'),
(9, 'PASSWORD_CHANGED', 'EMAIL', 'Your password was changed successfully.'),
(10, 'WELCOME_USER', 'EMAIL', 'Welcome to Give Away Platform!')
ON CONFLICT (template_id) DO NOTHING;

-- Seed notification_delivery_logs (10 Rows)
INSERT INTO notification_delivery_logs (log_id, notification_id, channel, delivery_status) VALUES
(1, 1, 'EMAIL', 'DELIVERED'),
(2, 2, 'PUSH', 'DELIVERED'),
(3, 3, 'IN_APP', 'DELIVERED'),
(4, 4, 'SMS', 'DELIVERED'),
(5, 5, 'SMS', 'FAILED'),
(6, 6, 'EMAIL', 'DELIVERED'),
(7, 7, 'IN_APP', 'DELIVERED'),
(8, 8, 'EMAIL', 'DELIVERED'),
(9, 9, 'PUSH', 'DELIVERED'),
(10, 10, 'EMAIL', 'DELIVERED')
ON CONFLICT (log_id) DO NOTHING;

-- Seed user_notification_preferences (10 Rows)
INSERT INTO user_notification_preferences (preference_id, user_id, channel, enabled) VALUES
(1, 1, 'EMAIL', TRUE),
(2, 2, 'EMAIL', TRUE),
(3, 2, 'SMS', TRUE),
(4, 3, 'PUSH', FALSE),
(5, 4, 'SMS', TRUE),
(6, 5, 'PUSH', TRUE),
(7, 6, 'EMAIL', TRUE),
(8, 7, 'SMS', FALSE),
(9, 8, 'EMAIL', TRUE),
(10, 10, 'PUSH', TRUE)
ON CONFLICT (preference_id) DO NOTHING;

-- Sync sequences for auto-increment IDs
SELECT setval('roles_role_id_seq', (SELECT MAX(role_id) FROM roles));
SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users));
SELECT setval('refresh_tokens_token_id_seq', (SELECT MAX(token_id) FROM refresh_tokens));
SELECT setval('login_audit_audit_id_seq', (SELECT MAX(audit_id) FROM login_audit));
SELECT setval('otp_verifications_otp_id_seq', (SELECT MAX(otp_id) FROM otp_verifications));
SELECT setval('addresses_address_id_seq', (SELECT MAX(address_id) FROM addresses));
SELECT setval('donor_profiles_donor_id_seq', (SELECT MAX(donor_id) FROM donor_profiles));
SELECT setval('receiver_profiles_receiver_id_seq', (SELECT MAX(receiver_id) FROM receiver_profiles));
SELECT setval('ngo_profiles_ngo_id_seq', (SELECT MAX(ngo_id) FROM ngo_profiles));
SELECT setval('beneficiaries_beneficiary_id_seq', (SELECT MAX(beneficiary_id) FROM beneficiaries));
SELECT setval('programs_program_id_seq', (SELECT MAX(program_id) FROM programs));
SELECT setval('verification_requests_request_id_seq', (SELECT MAX(request_id) FROM verification_requests));
SELECT setval('verification_documents_document_id_seq', (SELECT MAX(document_id) FROM verification_documents));
SELECT setval('verification_status_history_history_id_seq', (SELECT MAX(history_id) FROM verification_status_history));
SELECT setval('rejection_reasons_reason_id_seq', (SELECT MAX(reason_id) FROM rejection_reasons));
SELECT setval('fund_pools_pool_id_seq', (SELECT MAX(pool_id) FROM fund_pools));
SELECT setval('money_donations_donation_id_seq', (SELECT MAX(donation_id) FROM money_donations));
SELECT setval('item_donations_item_donation_id_seq', (SELECT MAX(item_donation_id) FROM item_donations));
SELECT setval('assistance_applications_application_id_seq', (SELECT MAX(application_id) FROM assistance_applications));
SELECT setval('ngo_item_requests_request_id_seq', (SELECT MAX(request_id) FROM ngo_item_requests));
SELECT setval('ngo_fund_requests_request_id_seq', (SELECT MAX(request_id) FROM ngo_fund_requests));
SELECT setval('donation_status_history_history_id_seq', (SELECT MAX(history_id) FROM donation_status_history));
SELECT setval('application_status_history_history_id_seq', (SELECT MAX(history_id) FROM application_status_history));
SELECT setval('inventory_items_item_id_seq', (SELECT MAX(item_id) FROM inventory_items));
SELECT setval('inventory_transactions_transaction_id_seq', (SELECT MAX(transaction_id) FROM inventory_transactions));
SELECT setval('pickup_schedules_pickup_id_seq', (SELECT MAX(pickup_id) FROM pickup_schedules));
SELECT setval('fund_ledger_ledger_id_seq', (SELECT MAX(ledger_id) FROM fund_ledger));
SELECT setval('disbursements_disbursement_id_seq', (SELECT MAX(disbursement_id) FROM disbursements));
SELECT setval('allocations_allocation_id_seq', (SELECT MAX(allocation_id) FROM allocations));
SELECT setval('notifications_notification_id_seq', (SELECT MAX(notification_id) FROM notifications));
SELECT setval('notification_templates_template_id_seq', (SELECT MAX(template_id) FROM notification_templates));
SELECT setval('notification_delivery_logs_log_id_seq', (SELECT MAX(log_id) FROM notification_delivery_logs));
SELECT setval('user_notification_preferences_preference_id_seq', (SELECT MAX(preference_id) FROM user_notification_preferences));
