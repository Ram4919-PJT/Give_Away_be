CREATE TABLE IF NOT EXISTS recurring_gifts (
    gift_id BIGSERIAL PRIMARY KEY,
    donor_id BIGINT NOT NULL REFERENCES donor_profiles(donor_id),
    program_id BIGINT NOT NULL REFERENCES programs(program_id),
    organization_name VARCHAR(150) NOT NULL DEFAULT 'Aja Abayahastham',
    amount DECIMAL(10, 2) NOT NULL,
    frequency VARCHAR(20) NOT NULL DEFAULT 'MONTHLY',
    start_date DATE NOT NULL,
    next_payment_date DATE,
    payments_made INT NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    payment_method VARCHAR(50),
    paused_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO recurring_gifts (
  gift_id, donor_id, program_id, organization_name, amount, frequency,
  start_date, next_payment_date, payments_made, status, payment_method
) VALUES
  (1, 1, 2, 'Asha Kiran Foundation', 2000.00, 'MONTHLY', (CURRENT_DATE - INTERVAL '120 days')::date, (CURRENT_DATE + INTERVAL '5 days')::date, 4, 'ACTIVE', 'UPI AutoPay'),
  (2, 1, 1, 'Hope Health Trust', 1500.00, 'MONTHLY', (CURRENT_DATE - INTERVAL '180 days')::date, (CURRENT_DATE + INTERVAL '12 days')::date, 6, 'ACTIVE', 'Card'),
  (3, 1, 6, 'Care & Share Relief', 1000.00, 'MONTHLY', (CURRENT_DATE - INTERVAL '90 days')::date, (CURRENT_DATE + INTERVAL '20 days')::date, 3, 'ACTIVE', 'UPI AutoPay'),
  (4, 1, 5, 'Green Earth Initiative', 1500.00, 'QUARTERLY', (CURRENT_DATE - INTERVAL '240 days')::date, (CURRENT_DATE + INTERVAL '40 days')::date, 2, 'ACTIVE', 'Net Banking'),
  (5, 1, 4, 'Elder Care Mission', 500.00, 'MONTHLY', (CURRENT_DATE - INTERVAL '60 days')::date, (CURRENT_DATE + INTERVAL '8 days')::date, 2, 'ACTIVE', 'UPI'),
  (6, 1, 8, 'Smile Education Trust', 400.00, 'WEEKLY', (CURRENT_DATE - INTERVAL '45 days')::date, (CURRENT_DATE + INTERVAL '3 days')::date, 6, 'ACTIVE', 'UPI AutoPay'),
  (7, 1, 3, 'Care & Share Relief', 2000.00, 'MONTHLY', (CURRENT_DATE - INTERVAL '150 days')::date, NULL, 4, 'PAUSED', 'Card'),
  (8, 1, 7, 'Women Rise Collective', 1000.00, 'MONTHLY', (CURRENT_DATE - INTERVAL '300 days')::date, NULL, 2, 'CANCELLED', 'UPI AutoPay'),
  (9, 1, 2, 'Asha Kiran Foundation', 2500.00, 'MONTHLY', (CURRENT_DATE - INTERVAL '400 days')::date, NULL, 12, 'COMPLETED', 'Card'),
  (10, 3, 2, 'Asha Kiran Foundation', 800.00, 'MONTHLY', (CURRENT_DATE - INTERVAL '70 days')::date, (CURRENT_DATE + INTERVAL '9 days')::date, 2, 'ACTIVE', 'Card')
ON CONFLICT (gift_id) DO UPDATE SET
  donor_id = EXCLUDED.donor_id,
  program_id = EXCLUDED.program_id,
  organization_name = EXCLUDED.organization_name,
  amount = EXCLUDED.amount,
  frequency = EXCLUDED.frequency,
  start_date = EXCLUDED.start_date,
  next_payment_date = EXCLUDED.next_payment_date,
  payments_made = EXCLUDED.payments_made,
  status = EXCLUDED.status,
  payment_method = EXCLUDED.payment_method;

SELECT setval('recurring_gifts_gift_id_seq', COALESCE((SELECT MAX(gift_id) FROM recurring_gifts), 1));
