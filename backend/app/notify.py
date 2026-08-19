"""
Sends the full customer and order details to your inbox via Formspree,
but ONLY after Paystack has confirmed the payment.

An abandoned checkout never reaches here, so your inbox stays clean.
"""

import logging

import httpx

from .core import Order, settings

log = logging.getLogger("relixsx.notify")


def naira(kobo: int) -> str:
    return "NGN {:,}".format(kobo // 100)


def send_order_email(order: Order) -> None:
    """Fire-and-forget. A failure here must never break the payment flow."""
    if not settings.FORMSPREE_ENDPOINT:
        log.warning("FORMSPREE_ENDPOINT not set: no email sent for %s",
                    order.order_number)
        return

    payload = {
        "_subject": f"PAID ORDER {order.order_number} — {order.full_name}",
        "Order number": order.order_number,
        "Payment status": "PAID",
        "Amount paid": naira(order.total_kobo),
        "Product": f"Astronaut 3-Piece School Set ({order.bag_label})",
        "Quantity": order.quantity,
        "Lunch box": order.lunchbox_label or "Not added",
        "Customer name": order.full_name,
        "Phone": "+" + order.phone,
        "WhatsApp": "+" + (order.whatsapp or order.phone),
        "Email": order.email,
        "State": order.state,
        "LGA": order.lga,
        "City / Town": order.city,
        "Street address": order.street,
        "Nearest landmark": order.landmark,
        "Delivery instructions": order.instructions or "None",
        "Paystack reference": order.payment_reference,
        "Ad source": order.utm_source or "Direct",
        "Ad campaign": order.utm_campaign or "None",
        "Paid at (UTC)": order.paid_at.strftime("%Y-%m-%d %H:%M") if order.paid_at else "",
    }

    try:
        with httpx.Client(timeout=15) as client:
            res = client.post(
                settings.FORMSPREE_ENDPOINT,
                json=payload,
                headers={"Accept": "application/json"},
            )
        if res.status_code >= 300:
            log.error("Formspree rejected %s: %s %s",
                      order.order_number, res.status_code, res.text[:200])
        else:
            log.info("Order email sent for %s", order.order_number)
    except Exception:
        # Never let a mail failure affect whether the order is marked paid.
        log.exception("Formspree call failed for %s", order.order_number)
