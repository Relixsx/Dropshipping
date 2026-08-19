# Relixsx School Bag Funnel: Order and Payment API

## Run it locally

```bash
cd backend
pip install -r requirements.txt
export PAYSTACK_SECRET_KEY=sk_test_your_test_key_here
uvicorn app.main:app --reload
```

It runs on `http://localhost:8000`. Interactive docs at `/docs`.

The landing page already points at that address, so open the HTML file
and the checkout works end to end in test mode.

## Test the whole flow

1. Start the API with your **test** secret key.
2. Open the landing page, fill the form, press Pay.
3. Paystack's test checkout opens. Use their test card `4084 0840 8408 4081`,
   any future expiry, CVV `408`, PIN `0000`, OTP `123456`.
4. You are returned to `PAYMENT_RETURN_URL`.
5. Confirm the order flipped to PAID by calling
   `GET /api/orders/RXS-SB-XXXXXXXX/verify`.

## Going live

Set these as environment variables in Railway or Render. Never in a file,
never in git.

```
PAYSTACK_SECRET_KEY   your live secret key
DATABASE_URL          your Postgres connection string
PAYMENT_RETURN_URL    https://yourdomain.com/order/payment-return
ALLOWED_ORIGINS       https://yourdomain.com
WHATSAPP_NUMBER       2347040408716
```

Then in the Paystack dashboard, under API Keys and Webhooks, set the
webhook URL to `https://your-api-domain.com/api/paystack/webhook`.

## Changing prices or taking a colour off sale

Edit `app/catalog.py` and redeploy. Set `"available": False` on any colour
and it is immediately blocked at checkout, whatever the browser sends.

## What protects the money

- The browser sends a variant key and a quantity. Never a price.
- `price_order()` recalculates the total from the server-side catalogue.
- Paystack is initialised with that server-calculated amount only.
- Returning to the callback URL does not mark anything paid. We verify
  with Paystack directly.
- The webhook signature is checked with HMAC SHA512 against your secret key.
- `_apply_payment()` returns early if the order is already paid, so a
  duplicate webhook cannot double-process an order.
- The charged amount is compared against the expected amount before an
  order is marked paid.
