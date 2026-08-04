import enum


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    READ = "READ"


class DeliveryStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    BOUNCED = "BOUNCED"
