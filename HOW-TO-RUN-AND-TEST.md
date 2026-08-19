# How to run and test this, step by step

Two stages. **Test on your own laptop first.** Nothing is deployed and no
real money moves. Only when a test payment works end to end do you go live.

---

# STAGE 1: TEST ON YOUR LAPTOP

## Step 1. Create your Formspree form

You need a new one. Do not reuse an old form, or school bag orders will
land in the wrong project's inbox.

1. Go to **formspree.io** and sign in with `airebirth5@gmail.com`
2. Click **+ New Form**
3. Name it **Relixsx School Bag Orders**
4. Copy the endpoint. It looks like `https://formspree.io/f/abcdwxyz`
5. **Check your Gmail and click Formspree's confirmation link.** Without
   this, nothing gets delivered and you will think the code is broken.

## Step 2. Put the backend on your machine

Download the `backend` folder, open a terminal in it, and run:

```bash
pip install -r requirements.txt
```

## Step 3. Set your keys for this session

Mac or Linux:

```bash
export PAYSTACK_SECRET_KEY="sk_test_your_new_test_key"
export FORMSPREE_ENDPOINT="https://formspree.io/f/abcdwxyz"
```

Windows PowerShell:

```powershell
$env:PAYSTACK_SECRET_KEY="sk_test_your_new_test_key"
$env:FORMSPREE_ENDPOINT="https://formspree.io/f/abcdwxyz"
```

Use the **new** test key, since the old one was pasted into a chat.

## Step 4. Start the server

```bash
uvicorn app.main:app --reload
```

You should see `Uvicorn running on http://127.0.0.1:8000`. Leave this
terminal open. Visit `http://localhost:8000/health` in your browser: it
should say `paystack_configured: true`.

## Step 5. Open the landing page

Double-click the HTML file. It opens in your browser and already points
at `http://localhost:8000`.

## Step 6. Place a test order

Fill the form with your own real details and press Pay. Paystack's test
checkout opens. Use:

```
Card    4084 0840 8408 4081
Expiry  any future date
CVV     408
PIN     0000
OTP     123456
```

## Step 7. Check the three things that must all be true

1. Paystack says the payment succeeded
2. **An email arrives at `airebirth5@gmail.com`** with the full order
3. Visit `http://localhost:8000/api/orders/RXS-SB-XXXXXXXX/verify`
   (use the order number from your email) and confirm it says `PAID`

If all three work, the funnel works.

## Step 8. Try to break it

Worth doing once. Open your browser's developer tools, change the price
in the page, and pay again. You will still be charged ₦20,000, because
the server ignores whatever the browser sends. That is the protection
working.

---

# STAGE 2: GO LIVE

Only after Stage 1 passes and your Paystack compliance is approved.

## Step 9. Deploy the backend

1. Push the `backend` folder to a GitHub repository
2. Go to **railway.app**, create a project, deploy from that repo
3. Add a **PostgreSQL** database in the same project. Railway sets
   `DATABASE_URL` for you
4. Under Variables, add:

```
PAYSTACK_SECRET_KEY   your LIVE secret key
FORMSPREE_ENDPOINT    https://formspree.io/f/abcdwxyz
PAYMENT_RETURN_URL    https://yourdomain.com/order/payment-return
ALLOWED_ORIGINS       https://yourdomain.com
WHATSAPP_NUMBER       2347040408716
```

Railway gives you a public URL like `https://relixsx-api.up.railway.app`.

## Step 10. Deploy the page

Put the HTML on Vercel or Netlify, and change one line near the bottom:

```javascript
var API_BASE = "https://relixsx-api.up.railway.app";
```

## Step 11. Set the webhook

In the Paystack dashboard, API Keys and Webhooks, set the webhook URL to:

```
https://relixsx-api.up.railway.app/api/paystack/webhook
```

This is what confirms payments even if a customer closes the browser
before being redirected back. Do not skip it.

## Step 12. One real payment, by you

Buy your own bag with your own card for the real ₦20,000. Confirm the
email arrives and the money settles the next working day. Then refund
yourself from the Paystack dashboard.

Only now do you spend money on adverts.

---

# WHAT TO CHANGE LATER, AND WHERE

| You want to | Edit |
|---|---|
| Change the price | `app/catalog.py`, `SET_PRICE_KOBO` |
| Change the lunch box price | `app/catalog.py`, `LUNCHBOX_PRICE_KOBO` |
| Take the product off sale | `app/catalog.py`, `PRODUCT_AVAILABLE = False` |
| Ship a different colour | `app/catalog.py`, `FEATURED_DESIGN`, and swap the photos |
| Start charging for delivery | `app/catalog.py`, `DELIVERY_FEE_KOBO` |

Every one of those is server side, so no customer can override it.
