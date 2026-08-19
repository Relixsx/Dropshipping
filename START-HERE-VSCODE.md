# Running this in VS Code

Everything is in the `relixsx-project` folder. Open **that folder** in VS
Code, not one of the files inside it.

```
relixsx-project/
  backend/          the API that handles orders and payment
  frontend/         the landing page and the confirmation page
```

---

## Step 1. Extensions you need

Open the Extensions panel (`Ctrl+Shift+X` or `Cmd+Shift+X`) and install:

- **Python** by Microsoft
- **Live Server** by Ritwick Dey

Live Server matters. If you open the HTML by double-clicking it, the
browser treats it as a file from disk and blocks it from talking to your
API. Live Server serves it properly and the problem disappears.

---

## Step 2. Create your Formspree form

1. Go to **formspree.io**, sign in with `airebirth5@gmail.com`
2. **+ New Form**, name it `Relixsx School Bag Orders`, create
3. Copy the endpoint: `https://formspree.io/f/abcdwxyz`
4. **Open your Gmail and click Formspree's confirmation link.** Skip this
   and no emails arrive, and you will waste an hour thinking the code is
   broken.

---

## Step 3. Make your `.env` file

In VS Code, right-click the `backend` folder, **New File**, name it
exactly `.env` (with the dot). Paste in:

```
PAYSTACK_SECRET_KEY=sk_test_your_new_test_key
FORMSPREE_ENDPOINT=https://formspree.io/f/abcdwxyz
```

That is it. No `export` commands, no terminal variables. The app reads
this file automatically.

`.gitignore` already excludes `.env`, so your key never reaches GitHub.

Use a **new** test key. The old one was pasted into a chat.

---

## Step 4. Install the Python packages

Open the terminal in VS Code with `Ctrl+\`` (backtick). Then:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows the activate line is `.venv\Scripts\activate` instead.

If VS Code asks whether to select a Python interpreter, say yes and pick
the one inside `.venv`.

**If a package fails to build**, your Python is newer than some packages
have wheels for. Nothing is wrong with the code. Install Python 3.12 or
3.13 and rebuild the virtual environment with it:

```bash
rm -rf .venv
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You do not need PostgreSQL on your laptop. Local testing uses SQLite,
which is built into Python. The Postgres driver lives in
`requirements-prod.txt` and is only installed when you deploy.

---

## Step 5. Start the API

Still in that terminal:

```bash
uvicorn app.main:app --reload
```

You want to see `Uvicorn running on http://127.0.0.1:8000`.

Check it worked: open `http://localhost:8000/health` in your browser. It
should say `"paystack_configured": true`. If it says `false`, your `.env`
is in the wrong folder or misspelled.

**Leave this terminal running.** Open a second terminal for anything else
with the `+` icon in the terminal panel.

*Shortcut:* press `F5` instead and VS Code starts it for you, using the
launch config already in `backend/.vscode/launch.json`.

---

## Step 6. Open the landing page

In the VS Code file explorer, right-click `frontend/index.html` and choose
**Open with Live Server**.

Your browser opens at `http://127.0.0.1:5500/index.html`.

---

## Step 7. Place a test order

Fill the form with your own real details. Press Pay.

Paystack's test checkout opens. Use:

```
Card    4084 0840 8408 4081
Expiry  any future date
CVV     408
PIN     0000
OTP     123456
```

You are redirected back to the confirmation page, which asks your server
to check with Paystack before showing anything. It should show
**Payment successful** with your order number.

---

## Step 8. Confirm all three things

1. The confirmation page says PAID with an order number
2. **An email arrives at `airebirth5@gmail.com`** with the full order
3. The uvicorn terminal shows `Order email sent for RXS-SB-...`

If all three are true, your funnel works end to end.

---

## Step 9. Try to cheat it, once

Worth doing so you trust it. In the browser, press `F12`, go to Console,
and type:

```javascript
SET = 100; paint();
```

The button now says ₦100. Pay anyway. Paystack still charges ₦20,000,
because the server ignores whatever the browser claims the price is.

---

## Common problems

| What you see | What it means |
|---|---|
| `paystack_configured: false` | `.env` is not inside `backend/`, or the name is wrong |
| "Could not reach the payment service" | The uvicorn terminal has stopped. Restart it |
| Payment works but no email | You did not click Formspree's confirmation link |
| CORS error in the console | You opened the HTML by double-clicking instead of Live Server |
| `ModuleNotFoundError: app` | You are in the wrong folder. `cd backend` first |

---

## When you go live

The webhook is the piece that only works in production, because Paystack
cannot reach your laptop. Locally, payment is confirmed when the customer
returns to the confirmation page. In production both paths run, so a
customer who closes their browser mid-payment still gets recorded.

Deploy steps are in `HOW-TO-RUN-AND-TEST.md`, from Step 9 onward.
