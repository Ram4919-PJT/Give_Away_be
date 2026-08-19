-- ============================================================================
-- IAM DB seed — roles + test users for Give Away
-- Password for every user is set by seed_database.py (default: Test@1234)
-- Placeholder: __PASSWORD_HASH__
-- ============================================================================

-- Roles (match IAM RoleName enum)
INSERT INTO roles (role_id, role_name, description) VALUES
  (1, 'SUPER_ADMIN', 'Platform administrator'),
  (2, 'DONOR', 'Individual or corporate donor'),
  (3, 'RECEIVER', 'Financial assistance seeker'),
  (4, 'NGO', 'NGO partner organization')
ON CONFLICT (role_id) DO UPDATE
SET role_name = EXCLUDED.role_name,
    description = EXCLUDED.description;

-- Users (stable IDs used by core + communication seeds)
-- 1 admin | 2 verified donor | 3 pending donor | 4 verified receiver
-- 5 pending receiver | 6 verified NGO | 7 pending NGO
-- 8 verified donor | 9 under-review receiver | 10 verified NGO
INSERT INTO users (user_id, role_id, full_name, email, mobile, password_hash, status) VALUES
  (1,  1, 'System Admin',        'admin@giveaway.org',           '9876543210', '__PASSWORD_HASH__', 'ACTIVE'),
  (2,  2, 'Ananya Sharma',       'ananya.donor@gmail.com',       '9876543211', '__PASSWORD_HASH__', 'ACTIVE'),
  (3,  2, 'Pending Donor',       'pending.donor@gmail.com',      '9876543212', '__PASSWORD_HASH__', 'ACTIVE'),
  (4,  3, 'Ramesh Kumar',        'ramesh.receiver@gmail.com',    '9876543213', '__PASSWORD_HASH__', 'ACTIVE'),
  (5,  3, 'Sita Devi',           'sita.receiver@gmail.com',      '9876543214', '__PASSWORD_HASH__', 'ACTIVE'),
  (6,  4, 'Hope Foundation',     'contact@hopefoundation.org',   '9876543215', '__PASSWORD_HASH__', 'ACTIVE'),
  (7,  4, 'Care & Share NGO',    'info@careshare.org',           '9876543216', '__PASSWORD_HASH__', 'ACTIVE'),
  (8,  2, 'Vikram Mehta',        'vikram.donor@yahoo.com',       '9876543217', '__PASSWORD_HASH__', 'ACTIVE'),
  (9,  3, 'Gita Rani',           'gita.r@gmail.com',             '9876543218', '__PASSWORD_HASH__', 'ACTIVE'),
  (10, 4, 'Smile Trust',         'help@smiletrust.org',          '9876543219', '__PASSWORD_HASH__', 'ACTIVE')
ON CONFLICT (user_id) DO UPDATE
SET role_id = EXCLUDED.role_id,
    full_name = EXCLUDED.full_name,
    email = EXCLUDED.email,
    mobile = EXCLUDED.mobile,
    password_hash = EXCLUDED.password_hash,
    status = EXCLUDED.status;

INSERT INTO login_audit (audit_id, user_id, ip_address, user_agent, status) VALUES
  (1, 1, '127.0.0.1', 'seed/admin', 'SUCCESS'),
  (2, 2, '127.0.0.1', 'seed/donor', 'SUCCESS'),
  (3, 4, '127.0.0.1', 'seed/receiver', 'SUCCESS'),
  (4, 6, '127.0.0.1', 'seed/ngo', 'SUCCESS'),
  (5, 5, '127.0.0.1', 'seed/receiver', 'FAILED')
ON CONFLICT (audit_id) DO NOTHING;

SELECT setval('roles_role_id_seq', GREATEST((SELECT MAX(role_id) FROM roles), 1));
SELECT setval('users_user_id_seq', GREATEST((SELECT MAX(user_id) FROM users), 1));
SELECT setval('login_audit_audit_id_seq', GREATEST((SELECT MAX(audit_id) FROM login_audit), 1));
