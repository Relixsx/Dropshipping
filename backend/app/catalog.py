"""
Single source of truth for what can be sold and for how much.

NOTHING about price or availability is ever taken from the browser.
The frontend sends a variant key and a quantity; every naira is
recomputed here.

To change a price or take a colour off sale, edit this file and redeploy.
"""

PRODUCT_NAME = "Astronaut 3-Piece School Set"

# The customer chooses a bag design. Flip `available` to False to take one
# off sale: it shows SOLD OUT and cannot be bought, whatever the browser sends.
BAG_VARIANTS = {
    "teal":   {"label": "Teal",     "available": True},
    "sky":    {"label": "Sky Blue", "available": True},
    "purple": {"label": "Purple",   "available": True},
    "pink":   {"label": "Pink",     "available": True},
}

# Price in kobo. 20,000 naira = 2,000,000 kobo.
SET_PRICE_KOBO = 20_000 * 100
LUNCHBOX_PRICE_KOBO = 5_000 * 100

MAX_QUANTITY = 10

# Set to False to take the whole product off sale.
PRODUCT_AVAILABLE = True

# The lunch box is a simple yes/no add-on. No colour is chosen.
LUNCHBOX_AVAILABLE = True
LUNCHBOX_LABEL = "Compartment lunch box"

# Free delivery nationwide. If this ever changes, the fee is computed
# here, server side, and never accepted from the browser.
DELIVERY_FEE_KOBO = 0


class CatalogError(ValueError):
    """Raised when the browser asks for something that is not on sale."""


def price_order(bag_variant: str, quantity: int, add_lunchbox: bool) -> dict:
    """Recompute the authoritative total. Returns amounts in kobo."""
    if not PRODUCT_AVAILABLE:
        raise CatalogError("This item is currently sold out.")

    variant = BAG_VARIANTS.get(bag_variant)
    if variant is None:
        raise CatalogError("That design is not available.")
    if not variant["available"]:
        raise CatalogError(f"{variant['label']} is sold out.")

    if not isinstance(quantity, int) or quantity < 1 or quantity > MAX_QUANTITY:
        raise CatalogError(f"Quantity must be between 1 and {MAX_QUANTITY}.")

    lunchbox_total = 0
    if add_lunchbox:
        if not LUNCHBOX_AVAILABLE:
            raise CatalogError("The lunch box is currently sold out.")
        lunchbox_total = LUNCHBOX_PRICE_KOBO * quantity

    subtotal = SET_PRICE_KOBO * quantity
    total = subtotal + lunchbox_total + DELIVERY_FEE_KOBO

    return {
        "bag_label": variant["label"],
        "lunchbox_label": LUNCHBOX_LABEL if add_lunchbox else None,
        "quantity": quantity,
        "subtotal_kobo": subtotal,
        "lunchbox_kobo": lunchbox_total,
        "delivery_kobo": DELIVERY_FEE_KOBO,
        "total_kobo": total,
    }


def public_catalog() -> dict:
    """What the frontend is allowed to know. Prices here are for display only."""
    return {
        "product": PRODUCT_NAME,
        "set_price_kobo": SET_PRICE_KOBO,
        "lunchbox_price_kobo": LUNCHBOX_PRICE_KOBO,
        "delivery_kobo": DELIVERY_FEE_KOBO,
        "max_quantity": MAX_QUANTITY,
        "available": PRODUCT_AVAILABLE,
        "bags": [{"key": k, **v} for k, v in BAG_VARIANTS.items()],
        "lunchbox_available": LUNCHBOX_AVAILABLE,
    }
