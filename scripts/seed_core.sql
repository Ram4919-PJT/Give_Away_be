-- ============================================================================
-- CORE DB seed — profiles, programs, donations, requests, inventory
-- user_id values are logical links to iam_db.users (no cross-DB FK)
-- Document / image URLs stored in verification_documents.file_url
-- ============================================================================

-- Addresses
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
ON CONFLICT (address_id) DO UPDATE
SET line1 = EXCLUDED.line1, city = EXCLUDED.city, state = EXCLUDED.state, pincode = EXCLUDED.pincode;

-- Donor profiles (user 2 verified, 3 pending, 8 verified)
INSERT INTO donor_profiles (donor_id, user_id, full_name, mobile, email, address_id) VALUES
  (1, 2, 'Ananya Sharma', '9876543211', 'ananya.donor@gmail.com', 1),
  (2, 3, 'Pending Donor', '9876543212', 'pending.donor@gmail.com', 2),
  (3, 8, 'Vikram Mehta', '9876543217', 'vikram.donor@yahoo.com', 7)
ON CONFLICT (donor_id) DO UPDATE
SET user_id = EXCLUDED.user_id, full_name = EXCLUDED.full_name, mobile = EXCLUDED.mobile,
    email = EXCLUDED.email, address_id = EXCLUDED.address_id;

-- Receiver profiles
INSERT INTO receiver_profiles (receiver_id, user_id, full_name, mobile, email, address_id, verification_status) VALUES
  (1, 4, 'Ramesh Kumar', '9876543213', 'ramesh.receiver@gmail.com', 3, 'VERIFIED'),
  (2, 5, 'Sita Devi', '9876543214', 'sita.receiver@gmail.com', 4, 'DOCUMENTS_SUBMITTED'),
  (3, 9, 'Gita Rani', '9876543218', 'gita.r@gmail.com', 9, 'UNDER_REVIEW')
ON CONFLICT (receiver_id) DO UPDATE
SET user_id = EXCLUDED.user_id, full_name = EXCLUDED.full_name, mobile = EXCLUDED.mobile,
    email = EXCLUDED.email, address_id = EXCLUDED.address_id,
    verification_status = EXCLUDED.verification_status;

-- NGO profiles
INSERT INTO ngo_profiles (ngo_id, user_id, ngo_name, registration_number, contact_person, mobile, address_id, verification_status) VALUES
  (1, 6, 'Hope Foundation', 'NGO-REG-2021-9981', 'Dr. Rajesh Rao', '9876543215', 5, 'VERIFIED'),
  (2, 7, 'Care & Share NGO', 'NGO-REG-2023-4412', 'Sunita Reddy', '9876543216', 6, 'UNDER_REVIEW'),
  (3, 10, 'Smile Trust', 'NGO-REG-2022-1109', 'Amitabh Das', '9876543219', 10, 'VERIFIED')
ON CONFLICT (ngo_id) DO UPDATE
SET user_id = EXCLUDED.user_id, ngo_name = EXCLUDED.ngo_name,
    registration_number = EXCLUDED.registration_number, contact_person = EXCLUDED.contact_person,
    mobile = EXCLUDED.mobile, address_id = EXCLUDED.address_id,
    verification_status = EXCLUDED.verification_status;

INSERT INTO beneficiaries (beneficiary_id, ngo_id, name, age, details) VALUES
  (1, 1, 'Aarav Kumar', 8, 'Orphaned child pursuing primary education.'),
  (2, 1, 'Priya Singh', 12, 'Requires hearing assistance device.'),
  (3, 1, 'Suresh Babu', 45, 'Physically disabled vocational trainee.'),
  (4, 2, 'Lakshmi Ammal', 68, 'Elderly destitute resident receiving food support.'),
  (5, 2, 'Meena Kumari', 15, 'Secondary school scholarship recipient.'),
  (6, 3, 'Kabir Khan', 10, 'Cancer treatment support recipient.'),
  (7, 3, 'Ravi Teja', 6, 'Malnutrition rehabilitation participant.')
ON CONFLICT (beneficiary_id) DO UPDATE
SET ngo_id = EXCLUDED.ngo_id, name = EXCLUDED.name, age = EXCLUDED.age, details = EXCLUDED.details;

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
ON CONFLICT (program_id) DO UPDATE
SET program_name = EXCLUDED.program_name, description = EXCLUDED.description,
    category = EXCLUDED.category, status = EXCLUDED.status;

-- Verification requests (drive verified vs pending UX)
INSERT INTO verification_requests (request_id, user_id, request_type, status, submitted_at) VALUES
  (1, 4, 'RECEIVER', 'VERIFIED', NOW() - INTERVAL '5 days'),
  (2, 5, 'RECEIVER', 'UNDER_REVIEW', NOW() - INTERVAL '2 days'),
  (3, 6, 'NGO', 'VERIFIED', NOW() - INTERVAL '10 days'),
  (4, 7, 'NGO', 'UNDER_REVIEW', NOW() - INTERVAL '1 day'),
  (5, 9, 'RECEIVER', 'UNDER_REVIEW', NOW() - INTERVAL '3 days'),
  (6, 10, 'NGO', 'VERIFIED', NOW() - INTERVAL '12 days'),
  (7, 2, 'DONOR', 'VERIFIED', NOW() - INTERVAL '20 days'),
  (8, 3, 'DONOR', 'SUBMITTED', NOW() - INTERVAL '1 day'),
  (9, 8, 'DONOR', 'VERIFIED', NOW() - INTERVAL '15 days')
ON CONFLICT (request_id) DO UPDATE
SET user_id = EXCLUDED.user_id, request_type = EXCLUDED.request_type,
    status = EXCLUDED.status, submitted_at = EXCLUDED.submitted_at;

-- Document / image URLs (FE can load these from API)
INSERT INTO verification_documents (document_id, request_id, document_type, file_url) VALUES
  (1, 1, 'AADHAR_CARD', '/assets/seed/docs/rec_ramesh_aadhar.pdf'),
  (2, 1, 'INCOME_CERTIFICATE', '/assets/seed/docs/rec_ramesh_income.pdf'),
  (3, 2, 'MEDICAL_BILL', '/assets/seed/docs/rec_sita_medical.pdf'),
  (4, 3, 'NGO_DARPAN_CERTIFICATE', '/assets/seed/docs/ngo_hope_darpan.pdf'),
  (5, 3, 'LOGO_IMAGE', '/assets/seed/images/ngo_hope_logo.png'),
  (6, 4, 'TRUST_DEED', '/assets/seed/docs/ngo_care_trust.pdf'),
  (7, 5, 'AADHAR_CARD', '/assets/seed/docs/rec_gita_aadhar.pdf'),
  (8, 6, '80G_CERTIFICATE', '/assets/seed/docs/ngo_smile_80g.pdf'),
  (9, 6, 'LOGO_IMAGE', '/assets/seed/images/ngo_smile_logo.png'),
  (10, 7, 'PAN_CARD', '/assets/seed/docs/donor_ananya_pan.pdf'),
  (11, 8, 'PAN_CARD', '/assets/seed/docs/donor_pending_pan.pdf'),
  (12, 9, 'PAN_CARD', '/assets/seed/docs/donor_vikram_pan.pdf')
ON CONFLICT (document_id) DO UPDATE
SET request_id = EXCLUDED.request_id, document_type = EXCLUDED.document_type, file_url = EXCLUDED.file_url;

INSERT INTO verification_status_history (history_id, request_id, status) VALUES
  (1, 1, 'REGISTERED'),
  (2, 1, 'DOCUMENTS_SUBMITTED'),
  (3, 1, 'VERIFIED'),
  (4, 2, 'REGISTERED'),
  (5, 2, 'DOCUMENTS_SUBMITTED'),
  (6, 3, 'VERIFIED'),
  (7, 4, 'UNDER_REVIEW'),
  (8, 7, 'VERIFIED'),
  (9, 8, 'SUBMITTED'),
  (10, 9, 'VERIFIED')
ON CONFLICT (history_id) DO NOTHING;

INSERT INTO rejection_reasons (reason_id, request_id, reason) VALUES
  (1, 4, 'Trust deed missing page number 4.'),
  (2, 2, 'Income certificate name mismatched with Aadhar.'),
  (3, 5, 'Bank passbook copy missing account number.')
ON CONFLICT (reason_id) DO NOTHING;

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
ON CONFLICT (pool_id) DO UPDATE
SET pool_name = EXCLUDED.pool_name, balance = EXCLUDED.balance;

INSERT INTO money_donations (donation_id, donor_id, program_id, amount, payment_status, donated_at) VALUES
  (1, 1, 1, 5000.00,  'CONFIRMED',       NOW() - INTERVAL '150 days'),
  (2, 1, 2, 10800.00, 'CONFIRMED',       NOW() - INTERVAL '120 days'),
  (3, 1, 3, 2500.00,  'CONFIRMED',       NOW() - INTERVAL '90 days'),
  (4, 1, 4, 4200.00,  'CONFIRMED',       NOW() - INTERVAL '60 days'),
  (5, 1, 5, 2950.00,  'CONFIRMED',       NOW() - INTERVAL '35 days'),
  (6, 1, 7, 2000.00,  'CONFIRMED',       NOW() - INTERVAL '21 days'),
  (7, 1, 8, 1000.00,  'CONFIRMED',       NOW() - INTERVAL '14 days'),
  (8, 1, 2, 2500.00,  'CONFIRMED',       NOW() - INTERVAL '7 days'),
  (9, 1, 3, 25000.00, 'PAYMENT_PENDING', NOW() - INTERVAL '3 days'),
  (10, 3, 4, 15000.00, 'CONFIRMED',      NOW() - INTERVAL '40 days'),
  (11, 3, 5, 8000.00,  'CONFIRMED',      NOW() - INTERVAL '18 days'),
  (12, 2, 6, 5000.00,  'INITIATED',      NOW() - INTERVAL '2 days')
ON CONFLICT (donation_id) DO UPDATE
SET donor_id = EXCLUDED.donor_id, program_id = EXCLUDED.program_id,
    amount = EXCLUDED.amount, payment_status = EXCLUDED.payment_status,
    donated_at = EXCLUDED.donated_at;

INSERT INTO item_donations (item_donation_id, donor_id, category, description, quantity, pickup_address_id, status) VALUES
  (1, 1, 'Clothing', 'Warm winter jackets and sweaters', 50, 1, 'RECEIVED'),
  (2, 1, 'Medical Supplies', 'First Aid Kits and Wheelchairs', 5, 1, 'LISTED'),
  (3, 3, 'Electronics', 'Refurbished Laptops for students', 10, 7, 'PICKUP_SCHEDULED'),
  (4, 3, 'Books', 'Primary School Textbooks Set', 100, 7, 'RECEIVED'),
  (5, 2, 'Food Packs', 'Rice and Pulses 5kg Bags', 20, 2, 'LISTED')
ON CONFLICT (item_donation_id) DO UPDATE
SET donor_id = EXCLUDED.donor_id, category = EXCLUDED.category, description = EXCLUDED.description,
    quantity = EXCLUDED.quantity, pickup_address_id = EXCLUDED.pickup_address_id, status = EXCLUDED.status;

INSERT INTO assistance_applications (application_id, receiver_id, purpose, amount_requested, status) VALUES
  (1, 1, 'Kidney Dialysis Medical Relief', 30000.00, 'APPROVED'),
  (2, 1, 'Monthly Medicine Support', 8000.00, 'COMPLETED'),
  (3, 2, 'Children School Tuition Fees Assistance', 15000.00, 'UNDER_REVIEW'),
  (4, 3, 'Heart Surgery Fund Request', 75000.00, 'SUBMITTED')
ON CONFLICT (application_id) DO UPDATE
SET receiver_id = EXCLUDED.receiver_id, purpose = EXCLUDED.purpose,
    amount_requested = EXCLUDED.amount_requested, status = EXCLUDED.status;

INSERT INTO ngo_item_requests (request_id, ngo_id, item_category, quantity_requested, status) VALUES
  (1, 1, 'Clothing', 20, 'APPROVED'),
  (2, 1, 'Food Packs', 30, 'COMPLETED'),
  (3, 2, 'Electronics', 5, 'UNDER_REVIEW'),
  (4, 2, 'Blankets', 40, 'SUBMITTED'),
  (5, 3, 'Books', 50, 'APPROVED'),
  (6, 3, 'Furniture', 10, 'SUBMITTED')
ON CONFLICT (request_id) DO UPDATE
SET ngo_id = EXCLUDED.ngo_id, item_category = EXCLUDED.item_category,
    quantity_requested = EXCLUDED.quantity_requested, status = EXCLUDED.status;

INSERT INTO ngo_fund_requests (request_id, ngo_id, amount_requested, purpose, status) VALUES
  (1, 1, 40000.00, 'Community Health Camp Medical Setup', 'APPROVED'),
  (2, 2, 20000.00, 'Homeless Shelter Food Drive Supply', 'SUBMITTED'),
  (3, 3, 50000.00, 'School Building Roof Repair', 'APPROVED'),
  (4, 3, 35000.00, 'Clean Drinking Water Tank Installation', 'APPROVED')
ON CONFLICT (request_id) DO UPDATE
SET ngo_id = EXCLUDED.ngo_id, amount_requested = EXCLUDED.amount_requested,
    purpose = EXCLUDED.purpose, status = EXCLUDED.status;

INSERT INTO donation_status_history (history_id, donation_id, donation_type, status) VALUES
  (1, 1, 'MONEY', 'INITIATED'),
  (2, 1, 'MONEY', 'CONFIRMED'),
  (3, 2, 'MONEY', 'CONFIRMED'),
  (4, 1, 'ITEM', 'LISTED'),
  (5, 1, 'ITEM', 'RECEIVED'),
  (6, 3, 'ITEM', 'PICKUP_SCHEDULED')
ON CONFLICT (history_id) DO NOTHING;

INSERT INTO application_status_history (history_id, application_id, status) VALUES
  (1, 1, 'SUBMITTED'),
  (2, 1, 'UNDER_REVIEW'),
  (3, 1, 'APPROVED'),
  (4, 3, 'SUBMITTED'),
  (5, 3, 'UNDER_REVIEW'),
  (6, 4, 'SUBMITTED')
ON CONFLICT (history_id) DO NOTHING;

INSERT INTO inventory_items (item_id, category, description, quantity, status) VALUES
  (1, 'Clothing', 'Warm Winter Jackets', 30, 'IN_STOCK'),
  (2, 'Electronics', 'Refurbished Laptops', 0, 'OUT_OF_STOCK'),
  (3, 'Medical Supplies', 'Wheelchairs', 5, 'IN_STOCK'),
  (4, 'Books', 'Primary Textbooks', 50, 'IN_STOCK'),
  (5, 'Food Packs', 'Rice Bags 5kg', 10, 'IN_STOCK'),
  (6, 'Furniture', 'Study Chairs', 15, 'IN_STOCK'),
  (7, 'Blankets', 'Woolen Blankets', 20, 'IN_STOCK'),
  (8, 'Toys', 'Board Games', 30, 'IN_STOCK')
ON CONFLICT (item_id) DO UPDATE
SET category = EXCLUDED.category, description = EXCLUDED.description,
    quantity = EXCLUDED.quantity, status = EXCLUDED.status;

INSERT INTO inventory_transactions (transaction_id, item_id, transaction_type, quantity) VALUES
  (1, 1, 'IN', 50),
  (2, 1, 'OUT', 20),
  (3, 3, 'IN', 5),
  (4, 4, 'IN', 100),
  (5, 4, 'OUT', 50),
  (6, 5, 'IN', 40),
  (7, 5, 'OUT', 30),
  (8, 7, 'IN', 60)
ON CONFLICT (transaction_id) DO NOTHING;

INSERT INTO pickup_schedules (pickup_id, item_donation_id, pickup_date, pickup_time, status) VALUES
  (1, 1, CURRENT_DATE - INTERVAL '2 days', '10:00:00', 'COMPLETED'),
  (2, 3, CURRENT_DATE + INTERVAL '1 day', '10:30:00', 'SCHEDULED'),
  (3, 2, CURRENT_DATE + INTERVAL '2 days', '11:00:00', 'SCHEDULED'),
  (4, 4, CURRENT_DATE - INTERVAL '5 days', '14:00:00', 'COMPLETED'),
  (5, 5, CURRENT_DATE + INTERVAL '3 days', '09:00:00', 'SCHEDULED')
ON CONFLICT (pickup_id) DO UPDATE
SET item_donation_id = EXCLUDED.item_donation_id, pickup_date = EXCLUDED.pickup_date,
    pickup_time = EXCLUDED.pickup_time, status = EXCLUDED.status;

INSERT INTO fund_ledger (ledger_id, pool_id, transaction_type, amount) VALUES
  (1, 1, 'CREDIT', 50000.00),
  (2, 2, 'CREDIT', 10000.00),
  (3, 1, 'DEBIT', 30000.00),
  (4, 3, 'CREDIT', 25000.00),
  (5, 4, 'CREDIT', 15000.00),
  (6, 10, 'CREDIT', 50000.00)
ON CONFLICT (ledger_id) DO NOTHING;

INSERT INTO disbursements (disbursement_id, application_id, amount, status) VALUES
  (1, 1, 30000.00, 'COMPLETED'),
  (2, 2, 8000.00, 'COMPLETED')
ON CONFLICT (disbursement_id) DO UPDATE
SET application_id = EXCLUDED.application_id, amount = EXCLUDED.amount, status = EXCLUDED.status;

INSERT INTO allocations (allocation_id, ngo_request_id, item_id, quantity_allocated) VALUES
  (1, 1, 1, 20),
  (2, 2, 5, 30),
  (3, 5, 4, 50)
ON CONFLICT (allocation_id) DO UPDATE
SET ngo_request_id = EXCLUDED.ngo_request_id, item_id = EXCLUDED.item_id,
    quantity_allocated = EXCLUDED.quantity_allocated;

SELECT setval('addresses_address_id_seq', GREATEST((SELECT MAX(address_id) FROM addresses), 1));
SELECT setval('donor_profiles_donor_id_seq', GREATEST((SELECT MAX(donor_id) FROM donor_profiles), 1));
SELECT setval('receiver_profiles_receiver_id_seq', GREATEST((SELECT MAX(receiver_id) FROM receiver_profiles), 1));
SELECT setval('ngo_profiles_ngo_id_seq', GREATEST((SELECT MAX(ngo_id) FROM ngo_profiles), 1));
SELECT setval('beneficiaries_beneficiary_id_seq', GREATEST((SELECT MAX(beneficiary_id) FROM beneficiaries), 1));
SELECT setval('programs_program_id_seq', GREATEST((SELECT MAX(program_id) FROM programs), 1));
SELECT setval('verification_requests_request_id_seq', GREATEST((SELECT MAX(request_id) FROM verification_requests), 1));
SELECT setval('verification_documents_document_id_seq', GREATEST((SELECT MAX(document_id) FROM verification_documents), 1));
SELECT setval('verification_status_history_history_id_seq', GREATEST((SELECT MAX(history_id) FROM verification_status_history), 1));
SELECT setval('rejection_reasons_reason_id_seq', GREATEST((SELECT MAX(reason_id) FROM rejection_reasons), 1));
SELECT setval('fund_pools_pool_id_seq', GREATEST((SELECT MAX(pool_id) FROM fund_pools), 1));
SELECT setval('money_donations_donation_id_seq', GREATEST((SELECT MAX(donation_id) FROM money_donations), 1));
SELECT setval('item_donations_item_donation_id_seq', GREATEST((SELECT MAX(item_donation_id) FROM item_donations), 1));
SELECT setval('assistance_applications_application_id_seq', GREATEST((SELECT MAX(application_id) FROM assistance_applications), 1));
SELECT setval('ngo_item_requests_request_id_seq', GREATEST((SELECT MAX(request_id) FROM ngo_item_requests), 1));
SELECT setval('ngo_fund_requests_request_id_seq', GREATEST((SELECT MAX(request_id) FROM ngo_fund_requests), 1));
SELECT setval('donation_status_history_history_id_seq', GREATEST((SELECT MAX(history_id) FROM donation_status_history), 1));
SELECT setval('application_status_history_history_id_seq', GREATEST((SELECT MAX(history_id) FROM application_status_history), 1));
SELECT setval('inventory_items_item_id_seq', GREATEST((SELECT MAX(item_id) FROM inventory_items), 1));
SELECT setval('inventory_transactions_transaction_id_seq', GREATEST((SELECT MAX(transaction_id) FROM inventory_transactions), 1));
SELECT setval('pickup_schedules_pickup_id_seq', GREATEST((SELECT MAX(pickup_id) FROM pickup_schedules), 1));
SELECT setval('fund_ledger_ledger_id_seq', GREATEST((SELECT MAX(ledger_id) FROM fund_ledger), 1));
SELECT setval('disbursements_disbursement_id_seq', GREATEST((SELECT MAX(disbursement_id) FROM disbursements), 1));
SELECT setval('allocations_allocation_id_seq', GREATEST((SELECT MAX(allocation_id) FROM allocations), 1));
