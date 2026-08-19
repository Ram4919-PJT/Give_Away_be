from fastapi import APIRouter

from core_app.api.v1 import (
    admin_applications,
    admin_item_verification,
    admin_verification,
    applications,
    config,
    donations,
    donor_dashboard,
    donor_items,
    donor_settings,
    funds,
    inventory,
    item_catalog,
    item_categories,
    item_requests,
    location,
    ngo_dashboard,
    payments,
    profiles,
    public,
    verification,
)

api_router = APIRouter()
api_router.include_router(config.router)
api_router.include_router(public.router)
api_router.include_router(profiles.router)
api_router.include_router(verification.router)
api_router.include_router(donations.router)
api_router.include_router(payments.router)
api_router.include_router(donor_dashboard.router)
api_router.include_router(ngo_dashboard.router)
api_router.include_router(donor_settings.router)
api_router.include_router(donor_items.router)
api_router.include_router(item_requests.donor_router)
api_router.include_router(item_requests.receiver_router)
api_router.include_router(item_categories.router)
api_router.include_router(admin_item_verification.router)
api_router.include_router(admin_verification.router)
api_router.include_router(admin_applications.router)
api_router.include_router(item_catalog.router)
api_router.include_router(location.router)
api_router.include_router(applications.router)
api_router.include_router(inventory.router)
api_router.include_router(funds.router)
