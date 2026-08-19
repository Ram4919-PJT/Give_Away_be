CREATE TABLE IF NOT EXISTS email_delivery_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    recipient_email VARCHAR(255) NOT NULL,
    notification_type VARCHAR(50) NOT NULL DEFAULT 'ACCOUNT',
    event_type VARCHAR(80),
    subject VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    related_entity_type VARCHAR(50),
    related_entity_id BIGINT,
    idempotency_key VARCHAR(120) UNIQUE,
    provider_message_id VARCHAR(255),
    error_message TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_delivery_logs_user_id ON email_delivery_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_email_delivery_logs_status ON email_delivery_logs(status);
