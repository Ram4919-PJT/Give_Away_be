from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ItemCategoryOut(BaseModel):
    category_id: int
    name: str
    slug: str
    description: str | None = None
    is_active: bool
    sort_order: int
    model_config = {"from_attributes": True}


class ItemDonationDocumentOut(BaseModel):
    document_id: int
    document_type: str
    file_url: str
    uploaded_at: datetime
    model_config = {"from_attributes": True}


class ItemDonationOut(BaseModel):
    item_donation_id: int
    donor_id: int
    category_id: int | None = None
    item_name: str | None = None
    category: str
    subcategory: str | None = None
    description: str
    quantity: int
    quantity_available: int = 0
    quantity_reserved: int = 0
    pickup_address_id: int
    condition: str | None = None
    condition_note: str | None = None
    brand: str | None = None
    model_variant: str | None = None
    category_details: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None
    display_city: str | None = None
    display_state: str | None = None
    display_pincode: str | None = None
    pickup_availability: str | None = None
    preferred_pickup_time: str | None = None
    delivery_available: bool = False
    urgency: str | None = None
    additional_notes: str | None = None
    status: str
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    change_request_comment: str | None = None
    inventory_item_id: int | None = None
    documents: list[ItemDonationDocumentOut] = Field(default_factory=list)
    request_count: int = 0
    photo_urls: list[str] = Field(default_factory=list)
    donor_verified: bool | None = None
    donor_name: str | None = None
    donor_email: str | None = None
    model_config = {"from_attributes": True}


class ItemDonationCreate(BaseModel):
    item_name: str = Field(min_length=2, max_length=200)
    category_id: int
    subcategory: str | None = Field(default=None, max_length=100)
    description: str = Field(min_length=3, max_length=2000)
    quantity: int = Field(ge=1, le=10000)
    condition: str = Field(description="NEW|LIKE_NEW|GOOD|USED|NEEDS_REPAIR")
    condition_note: str | None = Field(default=None, max_length=255)
    brand: str | None = Field(default=None, max_length=100)
    model_variant: str | None = Field(default=None, max_length=100)
    category_details: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None
    pickup_address_id: int | None = None
    pickup_line1: str = Field(min_length=3, max_length=500)
    pickup_city: str = Field(min_length=2, max_length=100)
    pickup_state: str = Field(min_length=2, max_length=100)
    pickup_pincode: str = Field(min_length=4, max_length=20)
    pickup_availability: str | None = None
    preferred_pickup_time: str | None = None
    delivery_available: bool = False
    urgency: str | None = None
    additional_notes: str | None = None


class ItemDonationUpdate(BaseModel):
    item_name: str | None = Field(default=None, min_length=2, max_length=200)
    category_id: int | None = None
    subcategory: str | None = None
    description: str | None = Field(default=None, min_length=3, max_length=2000)
    quantity: int | None = Field(default=None, ge=1, le=10000)
    condition: str | None = None
    condition_note: str | None = None
    brand: str | None = None
    model_variant: str | None = None
    category_details: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None
    pickup_line1: str | None = None
    pickup_city: str | None = None
    pickup_state: str | None = None
    pickup_pincode: str | None = None
    pickup_availability: str | None = None
    preferred_pickup_time: str | None = None
    delivery_available: bool | None = None
    urgency: str | None = None
    additional_notes: str | None = None


class ItemDonationReviewRequest(BaseModel):
    action: str = Field(description="approve | reject | request_changes")
    rejection_reason: str | None = Field(default=None, max_length=1000)
    change_comment: str | None = Field(default=None, max_length=1000)


class CatalogItemOut(BaseModel):
    item_donation_id: int
    item_name: str
    category: str
    category_slug: str | None = None
    description: str
    quantity: int
    quantity_available: int
    condition: str | None = None
    condition_note: str | None = None
    display_city: str | None = None
    display_state: str | None = None
    photo_urls: list[str] = Field(default_factory=list)
    listed_at: datetime | None = None


class CatalogItemDetailOut(CatalogItemOut):
    subcategory: str | None = None
    brand: str | None = None
    model_variant: str | None = None
    category_details: dict[str, Any] | None = None
    display_pincode: str | None = None
    delivery_available: bool = False
    additional_notes: str | None = None


class CatalogListResponse(BaseModel):
    items: list[CatalogItemOut]
    total: int
    page: int
    page_size: int


class ItemDonationRequestCreate(BaseModel):
    quantity_requested: int = Field(ge=1, le=1000)
    message: str | None = Field(default=None, max_length=1000)
    pickup_or_delivery: str | None = Field(default=None, max_length=50)


class ItemDonationRequestOut(BaseModel):
    request_id: int
    item_donation_id: int
    receiver_id: int
    receiver_name: str | None = None
    item_name: str | None = None
    category: str | None = None
    condition: str | None = None
    photo_urls: list[str] = Field(default_factory=list)
    quantity_requested: int
    message: str | None = None
    status: str
    donor_response: str | None = None
    fulfillment_status: str
    pickup_or_delivery: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    completed_at: datetime | None = None


class ItemRequestAction(BaseModel):
    action: str = Field(description="accept | reject")
    response: str | None = Field(default=None, max_length=500)
