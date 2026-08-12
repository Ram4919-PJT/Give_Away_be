-- ============================================================================
-- COMMUNICATION DB seed — notifications, templates, preferences
-- user_id values are logical links to iam_db.users (no cross-DB FK)
-- ============================================================================

INSERT INTO notifications (notification_id, user_id, title, message, status) VALUES
  (1, 2, 'Donation Received', 'Thank you for donating INR 10,000 to the Education Pool.', 'READ'),
  (2, 2, 'Pickup Scheduled', 'Item pickup for your clothing donation is scheduled tomorrow at 10:30 AM.', 'UNREAD'),
  (3, 3, 'Verification Pending', 'Upload a clear PAN card to complete donor verification.', 'UNREAD'),
  (4, 4, 'Application Update', 'Your financial assistance request #1 has been approved.', 'UNREAD'),
  (5, 4, 'Disbursement Sent', 'INR 30,000 for dialysis relief was transferred to your account.', 'READ'),
  (6, 5, 'Documents Required', 'Please upload updated medical bills for your assistance request.', 'UNREAD'),
  (7, 6, 'Item Allocation', '20 jackets have been allocated to your NGO request.', 'UNREAD'),
  (8, 6, 'Fund Approved', 'Fund request for community health camp was approved.', 'READ'),
  (9, 7, 'NGO Under Review', 'Your NGO documents are currently under review.', 'READ'),
  (10, 1, 'System Alert', 'New NGO registration submitted for review.', 'UNREAD'),
  (11, 8, 'Donation Receipt', 'Receipt generated for INR 15,000 contribution.', 'READ'),
  (12, 9, 'KYC Pending', 'Complete your profile verification to unlock assistance features.', 'UNREAD'),
  (13, 10, 'Fund Approved', 'Fund request for INR 35,000 has been approved.', 'UNREAD')
ON CONFLICT (notification_id) DO UPDATE
SET user_id = EXCLUDED.user_id, title = EXCLUDED.title, message = EXCLUDED.message, status = EXCLUDED.status;

INSERT INTO notification_templates (template_id, template_name, channel, content) VALUES
  (1, 'DONATION_CONFIRMED', 'EMAIL', 'Dear Donor, thank you! Your donation of INR {{amount}} has been confirmed.'),
  (2, 'PICKUP_SCHEDULED', 'SMS', 'Your item pickup is scheduled on {{date}} at {{time}}.'),
  (3, 'ASSISTANCE_APPROVED', 'PUSH', 'Your assistance application #{{app_id}} has been APPROVED.'),
  (4, 'NGO_VERIFIED', 'EMAIL', 'Congratulations! Your NGO profile has been verified.'),
  (5, 'DOC_REJECTED', 'SMS', 'Your verification document was rejected. Reason: {{reason}}'),
  (6, 'OTP_CODE', 'SMS', 'Your OTP for Give Away is {{otp}}'),
  (7, 'DISBURSEMENT_SENT', 'PUSH', 'Financial aid of INR {{amount}} was transferred to your account.'),
  (8, 'ITEM_ALLOCATED', 'IN_APP', 'Requested item {{item_name}} allocated to your NGO.'),
  (9, 'PASSWORD_CHANGED', 'EMAIL', 'Your password was changed successfully.'),
  (10, 'WELCOME_USER', 'EMAIL', 'Welcome to the Give Away platform!')
ON CONFLICT (template_id) DO UPDATE
SET template_name = EXCLUDED.template_name, channel = EXCLUDED.channel, content = EXCLUDED.content;

INSERT INTO notification_delivery_logs (log_id, notification_id, channel, delivery_status) VALUES
  (1, 1, 'EMAIL', 'DELIVERED'),
  (2, 2, 'SMS', 'DELIVERED'),
  (3, 4, 'PUSH', 'DELIVERED'),
  (4, 5, 'EMAIL', 'DELIVERED'),
  (5, 6, 'SMS', 'FAILED'),
  (6, 7, 'IN_APP', 'DELIVERED'),
  (7, 9, 'EMAIL', 'DELIVERED'),
  (8, 10, 'IN_APP', 'DELIVERED'),
  (9, 11, 'EMAIL', 'DELIVERED'),
  (10, 13, 'EMAIL', 'DELIVERED')
ON CONFLICT (log_id) DO NOTHING;

INSERT INTO user_notification_preferences (preference_id, user_id, channel, enabled) VALUES
  (1, 1, 'EMAIL', TRUE),
  (2, 2, 'EMAIL', TRUE),
  (3, 2, 'SMS', TRUE),
  (4, 3, 'EMAIL', TRUE),
  (5, 4, 'SMS', TRUE),
  (6, 4, 'PUSH', TRUE),
  (7, 5, 'EMAIL', TRUE),
  (8, 6, 'EMAIL', TRUE),
  (9, 7, 'SMS', FALSE),
  (10, 8, 'EMAIL', TRUE),
  (11, 9, 'PUSH', TRUE),
  (12, 10, 'EMAIL', TRUE)
ON CONFLICT (preference_id) DO UPDATE
SET user_id = EXCLUDED.user_id, channel = EXCLUDED.channel, enabled = EXCLUDED.enabled;

SELECT setval('notifications_notification_id_seq', GREATEST((SELECT MAX(notification_id) FROM notifications), 1));
SELECT setval('notification_templates_template_id_seq', GREATEST((SELECT MAX(template_id) FROM notification_templates), 1));
SELECT setval('notification_delivery_logs_log_id_seq', GREATEST((SELECT MAX(log_id) FROM notification_delivery_logs), 1));
SELECT setval('user_notification_preferences_preference_id_seq', GREATEST((SELECT MAX(preference_id) FROM user_notification_preferences), 1));
