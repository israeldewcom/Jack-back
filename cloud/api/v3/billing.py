import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ...db.database import get_db
from ...db import models
from ...core.context import get_current_tenant
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
YOUR_DOMAIN = os.getenv("APP_DOMAIN", "http://localhost:3000")

router = APIRouter(prefix="/billing", tags=["billing"])

@router.post("/create-checkout-session")
def create_checkout_session(
    price_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()

    # Create or get Stripe customer
    if not tenant.stripe_customer_id:
        customer = stripe.Customer.create(
            email=current_user["email"],
            metadata={"tenant_id": tenant_id}
        )
        tenant.stripe_customer_id = customer.id
        db.commit()

    checkout_session = stripe.checkout.Session.create(
        customer=tenant.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=YOUR_DOMAIN + "/billing/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=YOUR_DOMAIN + "/billing/cancel",
        metadata={"tenant_id": tenant_id}
    )
    return {"checkout_url": checkout_session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        tenant_id = int(session["metadata"]["tenant_id"])
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        tenant.stripe_subscription_id = session["subscription"]
        tenant.subscription_status = "active"
        tenant.plan = "pro"  # or determine from price
        db.commit()

    elif event["type"] == "invoice.payment_succeeded":
        # Update usage, etc.
        pass

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        tenant = db.query(models.Tenant).filter(models.Tenant.stripe_subscription_id == subscription["id"]).first()
        if tenant:
            tenant.subscription_status = subscription["status"]
            db.commit()

    return {"status": "ok"}


@router.get("/usage")
def get_usage(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    tenant_id = current_user["tenant_id"]
    # For simplicity, return current month's usage
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage = db.query(models.UsageRecord).filter(
        models.UsageRecord.tenant_id == tenant_id,
        models.UsageRecord.recorded_at >= start_of_month
    ).all()
    # Aggregate by metric
    result = {}
    for u in usage:
        result[u.metric] = result.get(u.metric, 0) + u.quantity
    return result
