"""Redis key naming conventions for Give Away platform."""

EVENTS_STREAM = "giveaway:events"

# Rate limiting
LOGIN_RATE = "iam:rate:login:{email}"
OTP_RATE = "iam:rate:otp:{identifier}"

# Counters
UNREAD_COUNT = "comm:unread:{user_id}"

# Event deduplication
EVENT_PROCESSED = "event:processed:{consumer}:{event_id}"
