# GOING LIVE

Fourteen steps. Roughly two hours of your time, plus waiting on Paystack.

Do them in order. Steps 1 and 2 are the only ones that can hold you up for
days, so start them now even if you do the rest tomorrow.

---

## BEFORE ANYTHING: two blockers

### Blocker 1. Paystack compliance must be approved

You cannot get live keys until it is. Check **Settings → Compliance** in your
dashboard. If it says pending, everything below still works, but you will be
stuck in test mode at the final step.

### Blocker 2. Register as a Registered Business, not Starter

Starter has a **₦2,000,000 lifetime** collection cap. At ₦20,000 a set that is
**100 orders, ever.** Then payments switch off until you upgrade, and the
upgrade takes days to verify.

If you hit that ceiling mid-campaign, you will be paying Meta for traffic to a
page that cannot take money. Register properly before you spend on ads.

---

## STEP 1. Put the code on GitHub

```bash
cd relixsx-project
git init
git add .
git commit -m "Relixsx school bag funnel"
```

Create an empty repository on github.com, then:

```bash
git remote add origin https://github.com/YOURNAME/relixsx-schoolbags.git
git branch -M main
git push -u origin main
```

**Check before pushing:** run `git status` and confirm `.env` is NOT listed.
The `.gitignore` excludes it, but look anyway. A leaked live key is the worst
thing that can happen to this project.

---

## STEP 2. Deploy the backend on Railway

1. Go to **railway.app**, sign in with GitHub
2. **New Project → Deploy from GitHub repo**, pick your repo
3. Settings → **Root Directory**: set it to `backend`
4. Back in the project, **+ New → Database → Add PostgreSQL**

Railway sets `DATABASE_URL` automatically. Do not type it yourself.

---

## STEP 3. Add your environment variables

In Railway, your service → **Variables** → add these four:

```
PAYSTACK_SECRET_KEY   sk_live_... (or sk_test_ for now)
FORMSPREE_ENDPOINT    https://formspree.io/f/abcdwxyz
WHATSAPP_NUMBER       2347040408716
ALLOWED_ORIGINS       https://relixsxstore.xyz
PAYMENT_RETURN_URL    https://relixsxstore.xyz/schoolbags/success.html
```

Use your **test** key for now. You will swap it for live at Step 12, after the
production dry run.

The last two use your real domain. Exact values are confirmed at Step 8.

---

## STEP 4. Get your API address

Railway → Settings → Networking → **Generate Domain**.

You get something like `https://relixsx-api.up.railway.app`.

Test it: open `https://your-api-url/health` in a browser. It should say
`{"ok":true,"paystack_configured":true}`.

If `paystack_configured` is false, your variable name is misspelled.

---

## STEP 5. Point the page at the live API

In BOTH `frontend/index.html` and `frontend/success.html`, find this line near
the bottom and change it to your Railway address:

```javascript
var API_BASE = "https://relixsx-api.up.railway.app";
```

Both files. If you only change one, payment starts but confirmation fails.

---

## STEP 6. Add the page to your existing Netlify site

`relixsxstore.xyz` is already on Netlify with your MKTEL phone page at
`/phones`. The school bag page goes in beside it as another folder.

Find the site folder on your Mac that you drag to Netlify, and add a
`schoolbags` folder so it looks like this:

```
relixsxstore/
├── index.html              your existing page
├── phones/
│   └── index.html          MKTEL 5626
└── schoolbags/             NEW
    ├── index.html          the landing page
    ├── success.html        the confirmation page
    └── img/                all 10 photos
```

Copy the whole `frontend` folder contents in, renaming the folder to
`schoolbags`. The `img` folder must come with it or every photo breaks.

---

## STEP 7. Deploy

1. Go to **app.netlify.com** and open your `relixsxstore.xyz` site
2. **Deploys** tab
3. Scroll to the drag-and-drop zone at the bottom
4. Drag the **entire `relixsxstore` folder**, not just the new subfolder

Netlify redeploys in seconds. Your page is live at:

```
https://relixsxstore.xyz/schoolbags
```

**No Namecheap changes. No DNS. No propagation wait.** The domain already
points at Netlify, and folders are handled at the site level.

Open it on your phone and check the photos load.

---

## STEP 8. Set the two URL variables in Railway

Now you know the real URLs. Railway → Variables:

```
ALLOWED_ORIGINS       https://relixsxstore.xyz
PAYMENT_RETURN_URL    https://relixsxstore.xyz/schoolbags/success.html
```

No trailing slash on `ALLOWED_ORIGINS`. A mismatch here means the pay button
fails silently with a CORS error and you will not know why.

`PAYMENT_RETURN_URL` must include `/schoolbags/` and end in `success.html`,
or Paystack sends customers to a 404 after they have paid. That is the exact
error you hit locally.

Railway redeploys automatically.

---

## STEP 9. Set the Paystack webhook

Paystack dashboard → **Settings → API Keys & Webhooks**.

Webhook URL:

```
https://relixsx-api.up.railway.app/api/paystack/webhook
```

**This is the step people skip and regret.** Without it, a customer who pays
and then closes their browser before the redirect never gets recorded. Their
money leaves, your system never hears about it, and you find out when they
message you angry.

---

## STEP 10. Production dry run, still in test mode

Open https://relixsxstore.xyz/schoolbags and place a full order using Paystack's test card:

```
4084 0840 8408 4081   CVV 408   PIN 0000   OTP 123456
```

Five things must all be true:

1. The page loads over https with no console errors
2. Adding the lunch box changes the total to ₦25,000
3. You land on the confirmation page showing PAID
4. The order email arrives at `airebirth5@gmail.com`
5. Paystack dashboard → Transactions shows it

If any one fails, fix it before Step 12.

---

## STEP 11. Test the webhook specifically

Place another test order. At the Paystack payment screen, complete the payment,
then **close the tab immediately** before it redirects you.

Wait thirty seconds, then check your email. The order email should still
arrive, because the webhook caught it independently.

If it does not, your webhook URL is wrong. This test is worth the two minutes.

---

## STEP 12. Switch to live keys

Only once Steps 10 and 11 both pass.

1. Paystack dashboard, toggle from **Test** to **Live** mode, copy the live
   secret key
2. Railway → Variables → replace `PAYSTACK_SECRET_KEY` with the `sk_live_` one
3. Paystack → set the webhook URL again **in live mode** (test and live have
   separate webhook settings, and this catches almost everybody)

---

## STEP 13. Buy your own bag

One real order, your own card, real ₦20,000.

Confirm: payment succeeds, email arrives, order shows in Paystack, and the
money settles to your bank the next working day.

Then refund yourself from the Paystack dashboard, which also proves your refund
process works before a customer needs it.

**Do not spend a naira on ads before this passes.**

---

## STEP 14. Meta Pixel

The code already fires `InitiateCheckout` and `Purchase`, but only if a pixel
is present. Add yours in the `<head>` of both HTML files.

`Purchase` fires only after verified payment and is guarded against page
refresh, so your reported numbers will match your bank.

---

# AFTER LAUNCH

## Running the shop

| To do this | Change this | Then |
|---|---|---|
| Take a colour off sale | `app/catalog.py` → `"available": False` | push, Railway redeploys |
| Change the price | `app/catalog.py` → `SET_PRICE_KOBO` | push |
| Change lunch box price | `app/catalog.py` → `LUNCHBOX_PRICE_KOBO` | push |
| Pause sales entirely | `app/catalog.py` → `PRODUCT_AVAILABLE = False` | push |
| Start charging delivery | `app/catalog.py` → `DELIVERY_FEE_KOBO` | push |

Prices live on the server, so no customer can override them.

## Watch these in week one

- **Cost per purchase in Meta.** It comes out of the same ₦20,000 as your stock
  cost and your free delivery. Check the maths survives before scaling spend.
- **Where orders come from.** Every email carries the ad source. If far states
  are unprofitable under free delivery, you will see it here first.
- **Your Starter cap**, if you did not register a business. Paystack shows
  total collections in the dashboard.

## What has no page yet

You still have no return or damaged-on-arrival policy on the site. Your call,
made twice. Just know that when a dispute comes, you have nothing written down
to point at.
