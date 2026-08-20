"""
Relixsx school bag funnel: order and payment API.

Rules this file enforces and never bends:
  1. The amount charged is calculated here, never accepted from the browser.
  2. An order is only PAID after Paystack confirms it to us directly.
  3. Reaching the return URL proves nothing on its own.
  4. Webhooks are signature-checked and safe to receive twice.
"""

import hashlib
import hmac
import logging
import os
import re
import time
from datetime import datetime

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from .catalog import CatalogError, price_order, public_catalog
from .notify import send_order_email
from .core import Order, SessionLocal, init_db, new_order_number, settings

log = logging.getLogger("relixsx")

PAYSTACK_API = "https://api.paystack.co"

# Meta Conversions API is optional. Missing or invalid configuration disables
# reporting without affecting checkout, payment verification, or fulfilment.
META_PIXEL_ID = os.getenv("META_PIXEL_ID", "").strip()
META_CAPI_ACCESS_TOKEN = os.getenv("META_CAPI_ACCESS_TOKEN", "").strip()
META_GRAPH_API_VERSION = (
    os.getenv("META_GRAPH_API_VERSION", "v26.0").strip() or "v26.0"
)
META_TEST_EVENT_CODE = os.getenv("META_TEST_EVENT_CODE", "").strip()

if META_PIXEL_ID and not META_PIXEL_ID.isdigit():
    log.warning("Meta CAPI disabled because META_PIXEL_ID is invalid.")
    META_PIXEL_ID = ""
if not re.fullmatch(r"v\d+\.\d+", META_GRAPH_API_VERSION):
    log.warning("Invalid META_GRAPH_API_VERSION; using v26.0.")
    META_GRAPH_API_VERSION = "v26.0"
if not META_PIXEL_ID or not META_CAPI_ACCESS_TOKEN:
    log.warning(
        "Meta CAPI disabled because META_PIXEL_ID or "
        "META_CAPI_ACCESS_TOKEN is missing."
    )

app = FastAPI(title="Relixsx School Bag Orders")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------- validation

# 0803..., 234803..., +234803... all normalise to 234XXXXXXXXXX
NG_PHONE = re.compile(r"^(?:\+?234|0)(70|71|80|81|90|91|78)\d{8}$")


def normalise_phone(raw: str) -> str:
    digits = re.sub(r"[\s\-()]", "", raw or "")
    if not NG_PHONE.match(digits):
        raise ValueError("Enter a valid Nigerian phone number, e.g. 0803 123 4567")
    digits = digits.lstrip("+")
    if digits.startswith("0"):
        digits = "234" + digits[1:]
    return digits


def _meta_hash(value: str) -> str:
    """Normalize and SHA-256 hash customer data before sending it to Meta."""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _meta_event_id(order: Order) -> str:
    """Shared deterministic identifier used by CAPI and the browser Pixel."""
    return f"purchase_{order.order_number}"


def _send_meta_purchase(order: Order) -> dict | None:
    """Send a verified Purchase to Meta without exposing raw customer data."""
    if not META_PIXEL_ID or not META_CAPI_ACCESS_TOKEN:
        return None

    user_data: dict[str, list[str]] = {}
    if order.email:
        user_data["em"] = [_meta_hash(order.email)]
    if order.phone:
        user_data["ph"] = [_meta_hash(order.phone)]

    body = {
        "data": [
            {
                "event_name": "Purchase",
                "event_time": int(time.time()),
                "event_id": _meta_event_id(order),
                "action_source": "website",
                "event_source_url": settings.PAYMENT_RETURN_URL,
                "user_data": user_data,
                "custom_data": {
                    "currency": "NGN",
                    "value": order.total_kobo / 100,
                },
            }
        ]
    }
    if META_TEST_EVENT_CODE:
        body["test_event_code"] = META_TEST_EVENT_CODE

    url = (
        f"https://graph.facebook.com/{META_GRAPH_API_VERSION}/"
        f"{META_PIXEL_ID}/events"
    )
    with httpx.Client(timeout=20) as client:
        res = client.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {META_CAPI_ACCESS_TOKEN}"},
        )

    if not res.is_success:
        error_code = None
        error_type = None
        try:
            error = res.json().get("error", {})
            error_code = error.get("code")
            error_type = error.get("type")
        except (TypeError, ValueError):
            pass
        log.error(
            "Meta CAPI rejected Purchase for %s: status=%s code=%s type=%s",
            order.order_number,
            res.status_code,
            error_code,
            error_type,
        )
    res.raise_for_status()

    result = res.json()
    log.warning(
        "Meta CAPI Purchase accepted for %s: events_received=%s",
        order.order_number,
        result.get("events_received"),
    )
    return result


class OrderIn(BaseModel):
    bag_variant: str
    quantity: int = Field(ge=1, le=10)
    add_lunchbox: bool = False

    full_name: str = Field(min_length=2, max_length=120)
    phone: str
    whatsapp: str | None = None
    email: EmailStr

    state: str = Field(min_length=2, max_length=64)
    lga: str = Field(min_length=2, max_length=96)
    city: str = Field(min_length=2, max_length=96)
    street: str = Field(min_length=5, max_length=255)
    landmark: str = Field(min_length=2, max_length=255)
    instructions: str | None = Field(default=None, max_length=500)

    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    fbclid: str | None = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalise_phone(v)

    @field_validator("whatsapp")
    @classmethod
    def _whatsapp(cls, v: str | None) -> str | None:
        return normalise_phone(v) if v else None


# ---------------------------------------------------------------- endpoints

@app.get("/api/catalog")
def catalog():
    """Lets the page grey out sold-out colours without hardcoding them."""
    return public_catalog()


@app.post("/api/orders")
def create_order(payload: OrderIn, db: Session = Depends(db_session)):
    """Create a pending order and hand back a Paystack payment link."""
    try:
        priced = price_order(
            payload.bag_variant, payload.quantity, payload.add_lunchbox
        )
    except CatalogError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    order = Order(
        order_number=new_order_number(),
        bag_variant=payload.bag_variant,
        bag_label=priced["bag_label"],
        quantity=priced["quantity"],
        lunchbox_variant="standard" if payload.add_lunchbox else None,
        lunchbox_label=priced["lunchbox_label"],
        subtotal_kobo=priced["subtotal_kobo"],
        lunchbox_kobo=priced["lunchbox_kobo"],
        delivery_kobo=priced["delivery_kobo"],
        total_kobo=priced["total_kobo"],
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        whatsapp=payload.whatsapp or payload.phone,
        email=str(payload.email).lower(),
        state=payload.state.strip(),
        lga=payload.lga.strip(),
        city=payload.city.strip(),
        street=payload.street.strip(),
        landmark=payload.landmark.strip(),
        instructions=(payload.instructions or "").strip() or None,
        payment_reference="",
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_content=payload.utm_content,
        fbclid=payload.fbclid,
    )
    order.payment_reference = order.order_number
    db.add(order)
    db.commit()
    db.refresh(order)

    try:
        checkout = _paystack_initialise(order)
    except Exception:
        log.exception("Paystack initialise failed for %s", order.order_number)
        raise HTTPException(
            status_code=502,
            detail="We could not start the payment just now. Please try again.",
        )

    return {
        "order_number": order.order_number,
        "total_kobo": order.total_kobo,
        "authorization_url": checkout["authorization_url"],
    }


def _paystack_initialise(order: Order) -> dict:
    body = {
        # The amount Paystack charges comes from our own calculation only.
        "amount": order.total_kobo,
        "email": order.email,
        "currency": "NGN",
        "reference": order.payment_reference,
        "callback_url": settings.PAYMENT_RETURN_URL,
        "metadata": {
            "order_number": order.order_number,
            "design": order.bag_label,
            "quantity": order.quantity,
            "lunchbox": order.lunchbox_label,
            "phone": order.phone,
        },
    }
    with httpx.Client(timeout=20) as client:
        res = client.post(
            f"{PAYSTACK_API}/transaction/initialize",
            json=body,
            headers={"Authorization": f"Bearer {settings.require_paystack()}"},
        )
    res.raise_for_status()
    return res.json()["data"]


@app.get("/api/orders/{reference}/verify")
def verify_order(reference: str, db: Session = Depends(db_session)):
    """
    Called when the customer lands back on the return URL.

    Landing there is not proof of payment, so we ask Paystack directly
    before changing anything.
    """
    order = db.query(Order).filter(Order.payment_reference == reference).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found.")

    if order.payment_status != "PAID":
        with httpx.Client(timeout=20) as client:
            res = client.get(
                f"{PAYSTACK_API}/transaction/verify/{reference}",
                headers={"Authorization": f"Bearer {settings.require_paystack()}"},
            )
        if res.status_code == 200:
            data = res.json().get("data", {})
            _apply_payment(db, order, data)

    payload = order.summary()
    payload["whatsapp_url"] = (
        f"https://wa.me/{settings.WHATSAPP_NUMBER}"
        f"?text=Hello%2C%20I%20just%20paid%20for%20order%20{order.order_number}."
        if order.payment_status == "PAID"
        else None
    )
    return payload


@app.post("/api/paystack/webhook")
async def paystack_webhook(request: Request, db: Session = Depends(db_session)):
    """
    Paystack calls this directly. It is the authoritative source of truth,
    because it does not depend on the customer's browser doing anything.
    """
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    expected = hmac.new(
        settings.require_paystack().encode(), raw, hashlib.sha512
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid signature.")

    event = await request.json()
    if event.get("event") != "charge.success":
        return {"status": "ignored"}

    data = event.get("data", {})
    order = (
        db.query(Order)
        .filter(Order.payment_reference == data.get("reference"))
        .first()
    )
    if order is None:
        log.warning("Webhook for unknown reference %s", data.get("reference"))
        return {"status": "unknown reference"}

    _apply_payment(db, order, data)
    return {"status": "ok"}


def _apply_payment(db: Session, order: Order, data: dict) -> None:
    """Mark an order paid. Safe to call repeatedly with the same event."""
    if order.payment_status == "PAID":
        return  # idempotent: a duplicate webhook changes nothing
    if data.get("status") != "success":
        return
    # Guard against an amount that does not match what we asked for.
    if int(data.get("amount", 0)) != order.total_kobo:
        log.error(
            "Amount mismatch on %s: charged %s, expected %s",
            order.order_number,
            data.get("amount"),
            order.total_kobo,
        )
        return

    order.payment_status = "PAID"
    order.fulfilment_status = "READY_FOR_DISPATCH"
    order.paid_at = datetime.utcnow()
    db.commit()

    # Only now, with money confirmed, does the order reach your inbox.
    if not order.email_sent:
        send_order_email(order)
        order.email_sent = True
        db.commit()

    # Meta reporting is secondary. A failure here must never undo or hide a
    # valid Paystack payment, block fulfilment, or suppress the success page.
    try:
        _send_meta_purchase(order)
    except Exception:
        log.exception(
            "Meta CAPI Purchase failed for %s",
            order.order_number,
        )


@app.get("/health")
def health():
    return {
        "ok": True,
        "paystack_configured": bool(settings.PAYSTACK_SECRET_KEY),
        "meta_pixel_configured": bool(META_PIXEL_ID),
        "meta_capi_configured": bool(META_CAPI_ACCESS_TOKEN),
        "meta_test_mode": bool(META_TEST_EVENT_CODE),
        "meta_api_version": META_GRAPH_API_VERSION,
    }
