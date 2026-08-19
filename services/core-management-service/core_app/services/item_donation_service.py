from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import class_mapper, selectinload

from core_app.config import settings
from core_app.integrations.notification_client import notify_user
from core_app.integrations.storage.local_storage import local_storage
from core_app.utils.portal_urls import admin_item_verification_url
from core_app.models.donations import DonationStatusHistory, ItemDonation
from core_app.models.enums import (
    CATALOG_VISIBLE_STATUSES,
    PENDING_ADMIN_STATUSES,
    ItemDocumentType,
    ItemDonationStatus,
    ItemRequestStatus,
)
from core_app.models.inventory import InventoryItem, InventoryTransaction
from core_app.models.item_category import ItemCategory
from core_app.models.item_donation_document import ItemDonationDocument
from core_app.models.item_donation_request import (
    ItemDonationRequest,
    ItemDonationVerificationHistory,
)
from core_app.models.profiles import Address, DonorProfile, ReceiverProfile
from core_app.models.verification import VerificationRequest
from core_app.schemas.item_donation import (
    CatalogItemDetailOut,
    CatalogItemOut,
    ItemDonationCreate,
    ItemDonationDocumentOut,
    ItemDonationOut,
    ItemDonationRequestCreate,
    ItemDonationRequestOut,
    ItemDonationUpdate,
    ItemRequestAction,
)
from core_app.services.donor_verification import DonorNotVerifiedError, require_verified_donor
from core_app.services.receiver_verification import ReceiverNotVerifiedError, require_verified_receiver


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def serialize_item_donation(item: ItemDonation) -> ItemDonationOut:
    insp = sa_inspect(item)
    documents = list(item.documents) if "documents" not in insp.unloaded else []
    requests = list(item.requests) if "requests" not in insp.unloaded else []
    payload = {col.key: getattr(item, col.key) for col in class_mapper(ItemDonation).columns}
    payload.update(
        {
            "documents": [ItemDonationDocumentOut.model_validate(doc) for doc in documents],
            "request_count": len(requests),
            "photo_urls": [doc.file_url for doc in documents],
        }
    )
    return ItemDonationOut.model_validate(payload)


def serialize_request(req: ItemDonationRequest) -> ItemDonationRequestOut:
    receiver_name = req.receiver.full_name if req.receiver else None
    item = req.item_donation
    item_name = item.item_name if item else None
    category = item.category if item else None
    condition = item.condition if item else None
    photo_urls: list[str] = []
    if item and item.documents:
        photo_urls = [
            d.file_url for d in item.documents if d.document_type == ItemDocumentType.ITEM_PHOTO.value
        ] or [d.file_url for d in item.documents]
    return ItemDonationRequestOut(
        request_id=req.request_id,
        item_donation_id=req.item_donation_id,
        receiver_id=req.receiver_id,
        receiver_name=receiver_name,
        item_name=item_name,
        category=category,
        condition=condition,
        photo_urls=photo_urls,
        quantity_requested=req.quantity_requested,
        message=req.message,
        status=req.status,
        donor_response=req.donor_response,
        fulfillment_status=req.fulfillment_status,
        pickup_or_delivery=req.pickup_or_delivery,
        created_at=req.created_at,
        updated_at=req.updated_at,
        accepted_at=req.accepted_at,
        rejected_at=req.rejected_at,
        completed_at=req.completed_at,
    )


async def get_donor_profile(db: AsyncSession, user_id: int) -> DonorProfile:
    result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
    donor = result.scalar_one_or_none()
    if donor is None:
        raise LookupError("Donor profile not found for this user")
    return donor


async def get_receiver_profile(db: AsyncSession, user_id: int) -> ReceiverProfile:
    result = await db.execute(select(ReceiverProfile).where(ReceiverProfile.user_id == user_id))
    receiver = result.scalar_one_or_none()
    if receiver is None:
        raise LookupError("Receiver profile not found for this user")
    return receiver


async def get_active_category(db: AsyncSession, category_id: int) -> ItemCategory:
    result = await db.execute(
        select(ItemCategory).where(
            ItemCategory.category_id == category_id,
            ItemCategory.is_active.is_(True),
        )
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise LookupError("Invalid or inactive category")
    return category


async def _get_item_for_donor(
    db: AsyncSession, user_id: int, item_donation_id: int
) -> ItemDonation:
    donor = await get_donor_profile(db, user_id)
    result = await db.execute(
        select(ItemDonation)
        .options(
            selectinload(ItemDonation.documents),
            selectinload(ItemDonation.requests),
        )
        .where(
            ItemDonation.item_donation_id == item_donation_id,
            ItemDonation.donor_id == donor.donor_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise LookupError("Item donation not found")
    return item


async def _record_history(
    db: AsyncSession, item_donation_id: int, status: str, admin_user_id: int | None = None, reason: str | None = None, action: str | None = None
) -> None:
    db.add(
        DonationStatusHistory(
            donation_id=item_donation_id,
            donation_type="ITEM",
            status=status,
        )
    )
    if admin_user_id and action:
        db.add(
            ItemDonationVerificationHistory(
                item_donation_id=item_donation_id,
                admin_user_id=admin_user_id,
                action=action,
                reason=reason,
            )
        )


async def create_or_update_address(
    db: AsyncSession,
    *,
    line1: str,
    city: str,
    state: str,
    pincode: str,
    address_id: int | None = None,
) -> Address:
    if address_id:
        result = await db.execute(select(Address).where(Address.address_id == address_id))
        address = result.scalar_one_or_none()
        if address:
            address.line1 = line1
            address.city = city
            address.state = state
            address.pincode = pincode
            await db.flush()
            return address
    address = Address(line1=line1, city=city, state=state, pincode=pincode)
    db.add(address)
    await db.flush()
    return address


def _apply_item_fields(item: ItemDonation, data: ItemDonationCreate | ItemDonationUpdate, category_name: str | None = None) -> None:
    fields = data.model_dump(exclude_unset=True)
    if category_name:
        item.category = category_name
    for key, value in fields.items():
        if key == "category_id":
            continue
        if hasattr(item, key):
            setattr(item, key, value)


async def create_item_donation_draft(
    db: AsyncSession,
    user_id: int,
    data: ItemDonationCreate,
) -> ItemDonationOut:
    await require_verified_donor(db, user_id)
    donor = await get_donor_profile(db, user_id)
    category = await get_active_category(db, data.category_id)

    address = await create_or_update_address(
        db,
        line1=data.pickup_line1,
        city=data.pickup_city,
        state=data.pickup_state,
        pincode=data.pickup_pincode,
        address_id=data.pickup_address_id,
    )

    item = ItemDonation(
        donor_id=donor.donor_id,
        category_id=category.category_id,
        category=category.name,
        item_name=data.item_name,
        description=data.description,
        quantity=data.quantity,
        quantity_available=0,
        quantity_reserved=0,
        pickup_address_id=address.address_id,
        status=ItemDonationStatus.DRAFT.value,
        display_city=data.pickup_city,
        display_state=data.pickup_state,
        display_pincode=data.pickup_pincode,
    )
    _apply_item_fields(item, data, category.name)
    db.add(item)
    await db.commit()
    item = await _get_item_for_donor(db, user_id, item.item_donation_id)
    return serialize_item_donation(item)


async def list_my_item_donations(db: AsyncSession, user_id: int) -> list[ItemDonationOut]:
    donor = await get_donor_profile(db, user_id)
    result = await db.execute(
        select(ItemDonation)
        .options(selectinload(ItemDonation.documents), selectinload(ItemDonation.requests))
        .where(ItemDonation.donor_id == donor.donor_id)
        .order_by(ItemDonation.item_donation_id.desc())
    )
    return [serialize_item_donation(row) for row in result.scalars().all()]


async def get_owned_item_donation(db: AsyncSession, user_id: int, item_donation_id: int) -> ItemDonationOut:
    item = await _get_item_for_donor(db, user_id, item_donation_id)
    return serialize_item_donation(item)


async def update_item_donation_draft(
    db: AsyncSession,
    user_id: int,
    item_donation_id: int,
    data: ItemDonationUpdate,
) -> ItemDonationOut:
    item = await _get_item_for_donor(db, user_id, item_donation_id)
    editable = {
        ItemDonationStatus.DRAFT.value,
        ItemDonationStatus.REJECTED.value,
    }
    if item.change_request_comment:
        editable.add(ItemDonationStatus.PENDING_VERIFICATION.value)
    if item.status not in editable:
        raise ValueError("This item cannot be edited in its current status")

    if data.category_id is not None:
        category = await get_active_category(db, data.category_id)
        item.category_id = category.category_id
        item.category = category.name

    if data.pickup_line1 and data.pickup_city and data.pickup_state and data.pickup_pincode:
        address = await create_or_update_address(
            db,
            line1=data.pickup_line1,
            city=data.pickup_city,
            state=data.pickup_state,
            pincode=data.pickup_pincode,
            address_id=item.pickup_address_id,
        )
        item.pickup_address_id = address.address_id
        item.display_city = data.pickup_city
        item.display_state = data.pickup_state
        item.display_pincode = data.pickup_pincode

    _apply_item_fields(item, data)
    if data.quantity is not None:
        item.quantity = data.quantity

    await db.commit()
    item = await _get_item_for_donor(db, user_id, item_donation_id)
    return serialize_item_donation(item)


async def delete_item_donation_draft(db: AsyncSession, user_id: int, item_donation_id: int) -> None:
    item = await _get_item_for_donor(db, user_id, item_donation_id)
    if item.status != ItemDonationStatus.DRAFT.value:
        raise ValueError("Only draft items can be deleted")
    await db.delete(item)
    await db.commit()


async def upload_item_document(
    db: AsyncSession,
    user_id: int,
    item_donation_id: int,
    upload: UploadFile,
    document_type: str = ItemDocumentType.ITEM_PHOTO.value,
) -> ItemDonationOut:
    item = await _get_item_for_donor(db, user_id, item_donation_id)
    if item.status not in {
        ItemDonationStatus.DRAFT.value,
        ItemDonationStatus.REJECTED.value,
        ItemDonationStatus.PENDING_VERIFICATION.value,
    }:
        raise ValueError("Documents can only be uploaded for editable donations")

    file_url = await local_storage.save_item_donation_file(item_donation_id, upload)
    db.add(
        ItemDonationDocument(
            item_donation_id=item_donation_id,
            document_type=document_type.upper(),
            file_url=file_url,
        )
    )
    await db.commit()
    item = await _get_item_for_donor(db, user_id, item_donation_id)
    return serialize_item_donation(item)


async def submit_item_donation(db: AsyncSession, user_id: int, item_donation_id: int) -> ItemDonationOut:
    await require_verified_donor(db, user_id)
    item = await _get_item_for_donor(db, user_id, item_donation_id)
    allowed = {ItemDonationStatus.DRAFT.value, ItemDonationStatus.REJECTED.value}
    if item.change_request_comment:
        allowed.add(ItemDonationStatus.PENDING_VERIFICATION.value)
    if item.status not in allowed:
        raise ValueError("Only draft or rejected donations can be submitted")

    if not item.item_name or not item.category_id:
        raise ValueError("Item name and category are required")
    if not item.documents:
        raise ValueError("At least one photo is required")
    if item.quantity < 1:
        raise ValueError("Quantity must be at least 1")

    item.status = ItemDonationStatus.PENDING_VERIFICATION.value
    item.submitted_at = _now()
    item.reviewed_at = None
    item.reviewed_by_user_id = None
    item.rejection_reason = None
    item.change_request_comment = None

    await _record_history(db, item.item_donation_id, item.status)
    await db.commit()
    await db.refresh(item)

    donor = await get_donor_profile(db, user_id)
    await notify_user(
        user_id=donor.user_id,
        title="Donation item submitted",
        message="Your donation item has been submitted for admin review. It will appear to receivers only after approval.",
        notification_type="DONATION",
        related_entity_type="ITEM_DONATION",
        related_entity_id=item.item_donation_id,
        action_url=f"/dashboard/donor-item-donation/{item.item_donation_id}",
    )
    await notify_user(
        user_id=settings.ADMIN_NOTIFY_USER_ID,
        title="New item awaiting review",
        message=f"\"{item.item_name or item.category}\" was submitted by a donor and needs admin verification.",
        notification_type="ACCOUNT",
        related_entity_type="ITEM_DONATION",
        related_entity_id=item.item_donation_id,
        action_url=admin_item_verification_url(item_donation_id=int(item.item_donation_id)),
    )
    await db.commit()
    item = await _get_item_for_donor(db, user_id, item_donation_id)
    return serialize_item_donation(item)


async def list_verification_queue(db: AsyncSession, status: str | None = None) -> list[ItemDonationOut]:
    statuses = [status.upper()] if status else list(PENDING_ADMIN_STATUSES)
    result = await db.execute(
        select(ItemDonation)
        .options(selectinload(ItemDonation.documents), selectinload(ItemDonation.requests))
        .where(ItemDonation.status.in_(statuses))
        .order_by(ItemDonation.submitted_at.asc().nullslast())
    )
    items = []
    for row in result.scalars().all():
        donor_prof = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == row.donor_id))
        donor = donor_prof.scalar_one_or_none()
        donor_verified = False
        if donor:
            vr = await db.execute(
                select(VerificationRequest).where(
                    VerificationRequest.user_id == donor.user_id,
                    VerificationRequest.request_type == "DONOR",
                    VerificationRequest.status == "VERIFIED",
                )
            )
            donor_verified = vr.scalar_one_or_none() is not None
        items.append(
            serialize_item_donation(row).model_copy(
                update={
                    "donor_verified": donor_verified,
                    "donor_name": donor.full_name if donor else None,
                    "donor_email": donor.email if donor else None,
                }
            )
        )
    return items


async def get_admin_item_detail(db: AsyncSession, item_donation_id: int) -> ItemDonationOut:
    result = await db.execute(
        select(ItemDonation)
        .options(selectinload(ItemDonation.documents), selectinload(ItemDonation.requests))
        .where(ItemDonation.item_donation_id == item_donation_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise LookupError("Item donation not found")
    donor_result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == item.donor_id))
    donor = donor_result.scalar_one_or_none()
    return serialize_item_donation(item).model_copy(
        update={
            "donor_name": donor.full_name if donor else None,
            "donor_email": donor.email if donor else None,
        }
    )


async def review_item_donation(
    db: AsyncSession,
    admin_user_id: int,
    item_donation_id: int,
    action: str,
    rejection_reason: str | None = None,
    change_comment: str | None = None,
) -> ItemDonationOut:
    result = await db.execute(
        select(ItemDonation)
        .options(selectinload(ItemDonation.documents), selectinload(ItemDonation.requests))
        .where(ItemDonation.item_donation_id == item_donation_id)
        .with_for_update()
    )
    item = result.scalar_one_or_none()
    if not item:
        raise LookupError("Item donation not found")
    if item.status not in PENDING_ADMIN_STATUSES:
        raise ValueError("Only pending items can be reviewed")

    normalized = action.strip().lower()
    now = _now()
    donor_result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == item.donor_id))
    donor = donor_result.scalar_one()

    if normalized == "approve":
        item.status = ItemDonationStatus.AVAILABLE.value
        item.reviewed_at = now
        item.reviewed_by_user_id = admin_user_id
        item.rejection_reason = None
        item.change_request_comment = None
        item.quantity_available = item.quantity
        item.quantity_reserved = 0

        if item.inventory_item_id is None:
            inv = InventoryItem(
                category=item.category,
                description=item.description,
                quantity=item.quantity,
                status="IN_STOCK",
            )
            db.add(inv)
            await db.flush()
            db.add(InventoryTransaction(item_id=inv.item_id, transaction_type="IN", quantity=item.quantity))
            item.inventory_item_id = inv.item_id

        await _record_history(db, item.item_donation_id, item.status, admin_user_id, action="APPROVE")
        await notify_user(
            user_id=donor.user_id,
            title="Donation item approved",
            message=f"Your donation item \"{item.item_name or item.category}\" has been approved and is now available.",
            notification_type="DONATION",
            related_entity_type="ITEM_DONATION",
            related_entity_id=item.item_donation_id,
            action_url=f"/dashboard/donor-item-donation/{item.item_donation_id}",
        )
    elif normalized == "reject":
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("Rejection reason is required")
        item.status = ItemDonationStatus.REJECTED.value
        item.reviewed_at = now
        item.reviewed_by_user_id = admin_user_id
        item.rejection_reason = rejection_reason.strip()
        await _record_history(db, item.item_donation_id, item.status, admin_user_id, rejection_reason, "REJECT")
        await notify_user(
            user_id=donor.user_id,
            title="Donation item not approved",
            message=f"Your donation item was not approved. Reason: {item.rejection_reason}",
            notification_type="DONATION",
            related_entity_type="ITEM_DONATION",
            related_entity_id=item.item_donation_id,
            action_url=f"/dashboard/donor-item-donation/{item.item_donation_id}",
        )
    elif normalized in {"request_changes", "request-changes"}:
        if not change_comment or not change_comment.strip():
            raise ValueError("Change request comment is required")
        item.status = ItemDonationStatus.DRAFT.value
        item.change_request_comment = change_comment.strip()
        item.reviewed_at = now
        item.reviewed_by_user_id = admin_user_id
        await _record_history(db, item.item_donation_id, "CHANGES_REQUESTED", admin_user_id, change_comment, "REQUEST_CHANGES")
        await notify_user(
            user_id=donor.user_id,
            title="Changes required",
            message=f"Changes are required for your donation item: {item.change_request_comment}",
            notification_type="DONATION",
            related_entity_type="ITEM_DONATION",
            related_entity_id=item.item_donation_id,
            action_url=f"/dashboard/donor-item-donation/{item.item_donation_id}/edit",
        )
    else:
        raise ValueError("action must be approve, reject, or request_changes")

    await db.commit()
    return await get_admin_item_detail(db, item_donation_id)

async def list_available_catalog_items(
    db: AsyncSession,
    *,
    category_slug: str | None = None,
    condition: str | None = None,
    city: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CatalogItemOut], int]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    filters = [
        ItemDonation.status.in_(tuple(CATALOG_VISIBLE_STATUSES)),
        ItemDonation.quantity_available > 0,
    ]
    if category_slug:
        filters.append(
            or_(
                ItemCategory.slug == category_slug,
                ItemDonation.category.ilike(category_slug.replace("-", " ")),
            )
        )
    if condition:
        filters.append(ItemDonation.condition == condition.upper())
    if city:
        filters.append(ItemDonation.display_city.ilike(f"%{city}%"))
    if search:
        term = f"%{search}%"
        filters.append(
            or_(
                ItemDonation.item_name.ilike(term),
                ItemDonation.description.ilike(term),
                ItemDonation.category.ilike(term),
            )
        )

    base = (
        select(ItemDonation, ItemCategory.slug)
        .outerjoin(ItemCategory, ItemCategory.category_id == ItemDonation.category_id)
        .where(*filters)
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    result = await db.execute(
        base.options(selectinload(ItemDonation.documents))
        .order_by(ItemDonation.reviewed_at.desc().nullslast(), ItemDonation.item_donation_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    catalog = []
    for item, slug in result.all():
        photos = [d.file_url for d in item.documents if d.document_type == ItemDocumentType.ITEM_PHOTO.value] or [
            d.file_url for d in item.documents
        ]
        catalog.append(
            CatalogItemOut(
                item_donation_id=item.item_donation_id,
                item_name=item.item_name or item.category,
                category=item.category,
                category_slug=slug,
                description=item.description,
                quantity=item.quantity,
                quantity_available=item.quantity_available,
                condition=item.condition,
                condition_note=item.condition_note,
                display_city=item.display_city,
                display_state=item.display_state,
                photo_urls=photos,
                listed_at=item.reviewed_at or item.submitted_at,
            )
        )
    return catalog, total


async def get_catalog_item_detail(db: AsyncSession, item_donation_id: int) -> CatalogItemDetailOut:
    result = await db.execute(
        select(ItemDonation, ItemCategory.slug)
        .outerjoin(ItemCategory, ItemCategory.category_id == ItemDonation.category_id)
        .options(selectinload(ItemDonation.documents))
        .where(
            ItemDonation.item_donation_id == item_donation_id,
            ItemDonation.status.in_(tuple(CATALOG_VISIBLE_STATUSES)),
            ItemDonation.quantity_available > 0,
        )
    )
    row = result.first()
    if not row:
        raise LookupError("Item not found or not available")
    item, slug = row
    photos = [d.file_url for d in item.documents]
    return CatalogItemDetailOut(
        item_donation_id=item.item_donation_id,
        item_name=item.item_name or item.category,
        category=item.category,
        category_slug=slug,
        subcategory=item.subcategory,
        description=item.description,
        quantity=item.quantity,
        quantity_available=item.quantity_available,
        condition=item.condition,
        condition_note=item.condition_note,
        brand=item.brand,
        model_variant=item.model_variant,
        category_details=item.category_details,
        display_city=item.display_city,
        display_state=item.display_state,
        display_pincode=item.display_pincode,
        delivery_available=item.delivery_available,
        additional_notes=item.additional_notes,
        photo_urls=photos,
        listed_at=item.reviewed_at or item.submitted_at,
    )


# Active receiver requests block duplicate submissions for the same item.
ACTIVE_RECEIVER_REQUEST_STATUSES = {
    ItemRequestStatus.PENDING.value,
    ItemRequestStatus.ACCEPTED.value,
    ItemRequestStatus.RESERVED.value,
    ItemRequestStatus.FULFILLMENT_IN_PROGRESS.value,
}


def _request_load_options():
    return (
        selectinload(ItemDonationRequest.receiver),
        selectinload(ItemDonationRequest.item_donation).selectinload(ItemDonation.documents),
    )


async def create_item_request(
    db: AsyncSession,
    user_id: int,
    item_donation_id: int,
    data: ItemDonationRequestCreate,
) -> ItemDonationRequestOut:
    await require_verified_receiver(db, user_id)
    receiver = await get_receiver_profile(db, user_id)
    result = await db.execute(
        select(ItemDonation)
        .where(ItemDonation.item_donation_id == item_donation_id)
        .with_for_update()
    )
    item = result.scalar_one_or_none()
    if not item or item.status not in CATALOG_VISIBLE_STATUSES:
        raise LookupError("Item not available")
    if item.quantity_available <= 0:
        raise LookupError("Item not available")
    if data.quantity_requested < 1:
        raise ValueError("Quantity must be at least 1")
    if data.quantity_requested > item.quantity_available:
        raise ValueError(f"Only {item.quantity_available} units available")

    dup_result = await db.execute(
        select(ItemDonationRequest.request_id).where(
            ItemDonationRequest.receiver_id == receiver.receiver_id,
            ItemDonationRequest.item_donation_id == item_donation_id,
            ItemDonationRequest.status.in_(ACTIVE_RECEIVER_REQUEST_STATUSES),
        )
    )
    if dup_result.scalar_one_or_none() is not None:
        raise ValueError("You already have an active request for this item")

    item.quantity_available -= data.quantity_requested
    if item.quantity_available == 0:
        item.status = ItemDonationStatus.UNAVAILABLE.value
    elif item.status == ItemDonationStatus.AVAILABLE.value:
        item.status = ItemDonationStatus.REQUESTED.value

    req = ItemDonationRequest(
        item_donation_id=item_donation_id,
        receiver_id=receiver.receiver_id,
        quantity_requested=data.quantity_requested,
        message=data.message,
        pickup_or_delivery=data.pickup_or_delivery,
        status=ItemRequestStatus.PENDING.value,
    )
    db.add(req)
    await db.flush()

    donor_result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == item.donor_id))
    donor = donor_result.scalar_one()
    await notify_user(
        user_id=donor.user_id,
        title="New item request",
        message=f"Someone has requested your donated item \"{item.item_name or item.category}\".",
        notification_type="DONATION",
        related_entity_type="ITEM_DONATION_REQUEST",
        related_entity_id=req.request_id,
        action_url=f"/dashboard/donor-item-requests?item={item_donation_id}",
    )
    await db.commit()
    await db.refresh(req)
    req_result = await db.execute(
        select(ItemDonationRequest)
        .options(*_request_load_options())
        .where(ItemDonationRequest.request_id == req.request_id)
    )
    return serialize_request(req_result.scalar_one())


async def list_receiver_requests(db: AsyncSession, user_id: int) -> list[ItemDonationRequestOut]:
    receiver = await get_receiver_profile(db, user_id)
    result = await db.execute(
        select(ItemDonationRequest)
        .options(*_request_load_options())
        .where(ItemDonationRequest.receiver_id == receiver.receiver_id)
        .order_by(ItemDonationRequest.created_at.desc())
    )
    return [serialize_request(r) for r in result.scalars().all()]


async def list_donor_requests(db: AsyncSession, user_id: int, item_donation_id: int | None = None) -> list[ItemDonationRequestOut]:
    donor = await get_donor_profile(db, user_id)
    query = (
        select(ItemDonationRequest)
        .join(ItemDonation, ItemDonation.item_donation_id == ItemDonationRequest.item_donation_id)
        .options(selectinload(ItemDonationRequest.receiver), selectinload(ItemDonationRequest.item_donation))
        .where(ItemDonation.donor_id == donor.donor_id)
    )
    if item_donation_id:
        query = query.where(ItemDonationRequest.item_donation_id == item_donation_id)
    result = await db.execute(query.order_by(ItemDonationRequest.created_at.desc()))
    return [serialize_request(r) for r in result.scalars().all()]


async def respond_to_request(
    db: AsyncSession,
    user_id: int,
    request_id: int,
    data: ItemRequestAction,
) -> ItemDonationRequestOut:
    donor = await get_donor_profile(db, user_id)
    result = await db.execute(
        select(ItemDonationRequest)
        .join(ItemDonation, ItemDonation.item_donation_id == ItemDonationRequest.item_donation_id)
        .options(selectinload(ItemDonationRequest.receiver), selectinload(ItemDonationRequest.item_donation))
        .where(
            ItemDonationRequest.request_id == request_id,
            ItemDonation.donor_id == donor.donor_id,
        )
        .with_for_update()
    )
    req = result.scalar_one_or_none()
    if not req:
        raise LookupError("Request not found")
    if req.status != ItemRequestStatus.PENDING.value:
        raise ValueError("Only pending requests can be responded to")

    item_result = await db.execute(
        select(ItemDonation).where(ItemDonation.item_donation_id == req.item_donation_id).with_for_update()
    )
    item = item_result.scalar_one()
    now = _now()
    action = data.action.strip().lower()
    receiver_result = await db.execute(
        select(ReceiverProfile).where(ReceiverProfile.receiver_id == req.receiver_id)
    )
    receiver = receiver_result.scalar_one()

    if action == "accept":
        req.status = ItemRequestStatus.ACCEPTED.value
        req.accepted_at = now
        req.fulfillment_status = ItemRequestStatus.FULFILLMENT_IN_PROGRESS.value
        req.donor_response = data.response
        item.quantity_reserved += req.quantity_requested
        await notify_user(
            user_id=receiver.user_id,
            title="Request accepted",
            message=f"Your request for \"{item.item_name or item.category}\" has been accepted.",
            notification_type="DONATION",
            related_entity_type="ITEM_DONATION_REQUEST",
            related_entity_id=req.request_id,
            action_url="/dashboard/receiver-my-requests",
        )
    elif action == "reject":
        req.status = ItemRequestStatus.REJECTED.value
        req.rejected_at = now
        req.donor_response = data.response or "Request declined by donor"
        item.quantity_available += req.quantity_requested
        if item.status == ItemDonationStatus.UNAVAILABLE.value and item.quantity_available > 0:
            item.status = ItemDonationStatus.AVAILABLE.value
        await notify_user(
            user_id=receiver.user_id,
            title="Request declined",
            message=f"Your request for \"{item.item_name or item.category}\" was declined.",
            notification_type="DONATION",
            related_entity_type="ITEM_DONATION_REQUEST",
            related_entity_id=req.request_id,
            action_url="/dashboard/receiver-my-requests",
        )
    else:
        raise ValueError("action must be accept or reject")

    await db.commit()
    await db.refresh(req)
    return serialize_request(req)


async def complete_request_fulfillment(
    db: AsyncSession,
    user_id: int,
    request_id: int,
    *,
    as_donor: bool = True,
) -> ItemDonationRequestOut:
    if as_donor:
        donor = await get_donor_profile(db, user_id)
        result = await db.execute(
            select(ItemDonationRequest)
            .join(ItemDonation)
            .where(
                ItemDonationRequest.request_id == request_id,
                ItemDonation.donor_id == donor.donor_id,
            )
            .with_for_update()
        )
    else:
        receiver = await get_receiver_profile(db, user_id)
        result = await db.execute(
            select(ItemDonationRequest)
            .where(
                ItemDonationRequest.request_id == request_id,
                ItemDonationRequest.receiver_id == receiver.receiver_id,
            )
            .with_for_update()
        )
    req = result.scalar_one_or_none()
    if not req:
        raise LookupError("Request not found")
    if req.status != ItemRequestStatus.ACCEPTED.value:
        raise ValueError("Only accepted requests can be completed")

    item_result = await db.execute(
        select(ItemDonation).where(ItemDonation.item_donation_id == req.item_donation_id).with_for_update()
    )
    item = item_result.scalar_one()
    req.status = ItemRequestStatus.COMPLETED.value
    req.fulfillment_status = ItemRequestStatus.COMPLETED.value
    req.completed_at = _now()
    item.quantity_reserved = max(0, item.quantity_reserved - req.quantity_requested)

    donor_result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == item.donor_id))
    donor = donor_result.scalar_one()
    receiver_result = await db.execute(select(ReceiverProfile).where(ReceiverProfile.receiver_id == req.receiver_id))
    receiver = receiver_result.scalar_one()

    for uid, msg in [
        (donor.user_id, f"Your donation of \"{item.item_name or item.category}\" has been successfully completed."),
        (receiver.user_id, f"You have received \"{item.item_name or item.category}\". Thank you!"),
    ]:
        await notify_user(
            user_id=uid,
            title="Donation completed",
            message=msg,
            notification_type="DONATION",
            related_entity_type="ITEM_DONATION_REQUEST",
            related_entity_id=req.request_id,
            action_url="/dashboard/donor-item-requests" if uid == donor.user_id else "/dashboard/receiver-my-requests",
        )

    await db.commit()
    req_loaded = await db.execute(
        select(ItemDonationRequest)
        .options(selectinload(ItemDonationRequest.receiver), selectinload(ItemDonationRequest.item_donation))
        .where(ItemDonationRequest.request_id == request_id)
    )
    return serialize_request(req_loaded.scalar_one())


async def cancel_item_request(db: AsyncSession, user_id: int, request_id: int) -> ItemDonationRequestOut:
    receiver = await get_receiver_profile(db, user_id)
    result = await db.execute(
        select(ItemDonationRequest)
        .where(
            ItemDonationRequest.request_id == request_id,
            ItemDonationRequest.receiver_id == receiver.receiver_id,
        )
        .with_for_update()
    )
    req = result.scalar_one_or_none()
    if not req:
        raise LookupError("Request not found")
    if req.status != ItemRequestStatus.PENDING.value:
        raise ValueError("Only pending requests can be cancelled")

    item_result = await db.execute(
        select(ItemDonation).where(ItemDonation.item_donation_id == req.item_donation_id).with_for_update()
    )
    item = item_result.scalar_one()
    req.status = ItemRequestStatus.CANCELLED.value
    item.quantity_available += req.quantity_requested
    if item.status == ItemDonationStatus.UNAVAILABLE.value and item.quantity_available > 0:
        item.status = ItemDonationStatus.AVAILABLE.value

    await db.commit()
    req_loaded = await db.execute(
        select(ItemDonationRequest)
        .options(selectinload(ItemDonationRequest.receiver), selectinload(ItemDonationRequest.item_donation))
        .where(ItemDonationRequest.request_id == request_id)
    )
    return serialize_request(req_loaded.scalar_one())
