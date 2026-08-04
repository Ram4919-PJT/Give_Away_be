import enum


class ProfileStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VerificationEntityType(str, enum.Enum):
    DONOR = "DONOR"
    RECEIVER = "RECEIVER"
    NGO = "NGO"


class DocumentType(str, enum.Enum):
    ID_PROOF = "ID_PROOF"
    ADDRESS_PROOF = "ADDRESS_PROOF"
    REGISTRATION_CERT = "REGISTRATION_CERT"
    PAN = "PAN"
    OTHER = "OTHER"


class DonationType(str, enum.Enum):
    MONEY = "MONEY"
    ITEM = "ITEM"


class DonationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class AssistanceRequestStatus(str, enum.Enum):
    OPEN = "OPEN"
    MATCHED = "MATCHED"
    FULFILLED = "FULFILLED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PickupStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class InventoryStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    ALLOCATED = "ALLOCATED"
    DISBURSED = "DISBURSED"


class FundLedgerEntryType(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class FundDisbursementStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DISBURSED = "DISBURSED"
    REJECTED = "REJECTED"


class ProgramStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
