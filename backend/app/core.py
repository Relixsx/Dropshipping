import os
import secrets
from datetime import datetime

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------------------------------------------------------------- settings

# Load a local .env file if one exists. In production the platform
# supplies real environment variables and this does nothing.
ENV_DIAGNOSTIC = {}
try:
    from dotenv import load_dotenv, find_dotenv

    _found = find_dotenv(usecwd=True)
    load_dotenv(_found)
    ENV_DIAGNOSTIC = {
        "dotenv_installed": True,
        "env_file_found": bool(_found),
        "env_file_path": _found or "no .env file found from " + os.getcwd(),
    }
except ImportError:
    ENV_DIAGNOSTIC = {
        "dotenv_installed": False,
        "env_file_found": False,
        "env_file_path": "python-dotenv is not installed: pip install python-dotenv",
    }


class Settings:
    # Secrets come from the environment. They are never written into source.
    PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./relixsx.db")
    # Where Paystack sends the customer back to after payment.
    PAYMENT_RETURN_URL = os.environ.get(
        "PAYMENT_RETURN_URL", "http://127.0.0.1:5500/success.html"
    )
    # Comma separated list of origins allowed to call this API.
    ALLOWED_ORIGINS = [
        o.strip()
        for o in os.environ.get(
            "ALLOWED_ORIGINS",
            # Local development defaults: VS Code Live Server, and "null"
            # which is the origin a page opened straight from disk sends.
            "http://127.0.0.1:5500,http://localhost:5500,"
            "http://localhost:3000,null",
        ).split(",")
        if o.strip()
    ]
    WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "2347040408716")
    # Where paid-order details are emailed. e.g. https://formspree.io/f/xxxxxxxx
    FORMSPREE_ENDPOINT = os.environ.get("FORMSPREE_ENDPOINT", "")

    def require_paystack(self) -> str:
        if not self.PAYSTACK_SECRET_KEY:
            raise RuntimeError(
                "PAYSTACK_SECRET_KEY is not set. Add it to your deployment "
                "environment variables. Never commit it to the repository."
            )
        return self.PAYSTACK_SECRET_KEY


settings = Settings()

# ---------------------------------------------------------------- database

def _normalise(url: str) -> str:
    """
    Railway and Render hand out URLs like postgresql://... which SQLAlchemy
    resolves to psycopg2. We use psycopg 3, so point it at the right driver.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(
    _normalise(settings.DATABASE_URL),
    pool_pre_ping=True,
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def new_order_number() -> str:
    return "RXS-SB-" + secrets.token_hex(4).upper()


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String(24), unique=True, index=True, nullable=False)

    # What was bought. Copied from the server-side catalogue, not the browser.
    bag_variant = Column(String(32), nullable=False)
    bag_label = Column(String(64), nullable=False)
    quantity = Column(Integer, nullable=False)
    lunchbox_variant = Column(String(32))
    lunchbox_label = Column(String(64))

    # Money, in kobo, as calculated on the server.
    subtotal_kobo = Column(Integer, nullable=False)
    lunchbox_kobo = Column(Integer, nullable=False, default=0)
    delivery_kobo = Column(Integer, nullable=False, default=0)
    total_kobo = Column(Integer, nullable=False)

    # Customer
    full_name = Column(String(120), nullable=False)
    phone = Column(String(24), nullable=False)
    whatsapp = Column(String(24))
    email = Column(String(160), nullable=False)

    # Delivery
    state = Column(String(64), nullable=False)
    lga = Column(String(96), nullable=False)
    city = Column(String(96), nullable=False)
    street = Column(String(255), nullable=False)
    landmark = Column(String(255), nullable=False)
    instructions = Column(String(500))

    # Payment
    payment_reference = Column(String(96), unique=True, index=True, nullable=False)
    payment_status = Column(String(24), default="PAYMENT_PENDING", nullable=False)
    fulfilment_status = Column(String(32), default="AWAITING_PAYMENT", nullable=False)
    paid_at = Column(DateTime)
    purchase_event_sent = Column(Boolean, default=False, nullable=False)
    email_sent = Column(Boolean, default=False, nullable=False)

    # Attribution, so you can tell which advert produced the sale.
    utm_source = Column(String(120))
    utm_medium = Column(String(120))
    utm_campaign = Column(String(160))
    utm_content = Column(String(160))
    fbclid = Column(String(255))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def summary(self) -> dict:
        return {
            "order_number": self.order_number,
            "product": "Astronaut 3-Piece School Set",
            "design": self.bag_label,
            "quantity": self.quantity,
            "lunchbox": self.lunchbox_label,
            "subtotal_kobo": self.subtotal_kobo,
            "lunchbox_kobo": self.lunchbox_kobo,
            "delivery_kobo": self.delivery_kobo,
            "total_kobo": self.total_kobo,
            "payment_status": self.payment_status,
            "fulfilment_status": self.fulfilment_status,
            "full_name": self.full_name,
            "state": self.state,
            "lga": self.lga,
            "city": self.city,
        }


def init_db() -> None:
    Base.metadata.create_all(engine)
