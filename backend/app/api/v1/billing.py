"""Stripe-backed billing endpoints (skeleton)."""
from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import CurrentPrincipal

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/billing", tags=["Billing"])

PLANS = [
    {"id": "free", "name": "Free", "price_usd": 0, "limits": {"websites": 1, "pages": 50, "chats": 200}},
    {"id": "starter", "name": "Starter", "price_usd": 49, "limits": {"websites": 3, "pages": 1000, "chats": 5000}},
    {"id": "pro", "name": "Pro", "price_usd": 149, "limits": {"websites": 10, "pages": 10000, "chats": 25000}},
    {"id": "enterprise", "name": "Enterprise", "price_usd": None, "limits": {}},
]


@router.get("/plans")
async def plans():
    return {"data": PLANS}


@router.post("/subscribe")
async def subscribe(principal: CurrentPrincipal, price_id: str):
    if not settings.STRIPE_SECRET_KEY:
        return {"data": {"checkout_url": None, "note": "Stripe not configured"}}
    checkout = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.FRONTEND_URL}/billing/success",
        cancel_url=f"{settings.FRONTEND_URL}/billing/cancel",
        client_reference_id=str(principal.workspace_id),
    )
    return {"data": {"checkout_url": checkout.url}}


@router.post("/cancel")
async def cancel(principal: CurrentPrincipal):
    return {"data": {"status": "cancellation_requested", "workspace_id": str(principal.workspace_id)}}


@router.post("/portal")
async def portal(principal: CurrentPrincipal):
    return {"data": {"portal_url": f"{settings.FRONTEND_URL}/account/billing"}}
