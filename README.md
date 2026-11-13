# Avocado Market Kenya

A small, complete avocado trading website: public storefront, buyer accounts, and an admin
panel for products, quotations and invoices. Built with Flask + SQLite, plain HTML/CSS/JS.

## What it does

**Public storefront**
- Product grid with photo, description, price per kg, minimum order, origin and stock
- Search and variety filters (Hass, Fuerte, Jumbo, Pinkerton, organic)
- Product pages with full specs and an "Order on WhatsApp" button on every card and page
- Floating WhatsApp button and click-to-chat links that pre-fill the message
- About and contact pages, plus an enquiry form

**Buyer accounts (email sign-in)**
- Register or sign in with email + password
- Ask for a quote from any product page
- "My account" lists every quote and invoice issued to that buyer, with status and print/PDF view

**Admin panel** (single login, no setup needed)
- Dashboard: products, buyers, open quotes, unpaid invoices, outstanding and paid totals
- Products: add, edit, hide, delete; set name, variety, grade, description, price per kg,
  MOQ, stock, origin, packaging and photo
- Quotes: create with line items (price auto-fills from the product), edit, change status
  (requested / sent / accepted / declined), send to the buyer, convert to an invoice
- Invoices: create manually or from a quote, mark paid or cancelled, print/PDF
- Customers: list registered buyers with their quote and invoice counts

## Run it locally (VS Code)

1. Open the `avocado_market` folder in VS Code (`File > Open Folder`).
2. Open a terminal (`Terminal > New Terminal`) and create a virtual environment:

   **Windows**
   ```bat
   python -m venv venv
   venv\Scripts\activate
   ```
   **macOS / Linux**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the dependency:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the app:
   ```bash
   python app.py
   ```

5. Open <http://127.0.0.1:5000>

The SQLite database is created automatically on first run at `instance/avocado.db`,
with 6 sample products and one admin account.

### Default admin login

| Email | Password |
| --- | --- |
| `admin@avocadomarket.co.ke` | `Admin@1234` |

Change these before putting the site online (see below), and change the password by
creating a new admin account or by editing the database.

## Make it yours

Everything you need to change lives at the top of `app.py`:

```python
SITE_NAME = "Avocado Market Kenya"
WHATSAPP_NUMBER = "254797799104"   # international format, no + or spaces
CONTACT_EMAIL = "orders@avocadomarket.co.ke"
ADMIN_EMAIL = "admin@avocadomarket.co.ke"
ADMIN_PASSWORD = "Admin@1234"
SECRET_KEY = "dev-change-this-key-before-going-live"
```

You can also set them as environment variables instead of editing the file:

```bash
set WHATSAPP_NUMBER=254712345678
set ADMIN_PASSWORD=MyNewStrongPassword
```

Product photos live in `static/img/`. Drop your own JPG/PNG files there, then pick
them in the product form (the dropdown lists `hass.jpg`, `fuerte.jpg`, `orchard.jpg`,
`packhouse.jpg`; add more options in `templates/admin/product_form.html` if you add files).

## Everyday workflow

1. Buyer registers, or asks for a quote from a product page.
2. You open **Admin > Quotes > New quote**, pick the buyer, add lines (quantity in kg,
   price per kg), save. Status `sent` makes it visible in the buyer's account immediately.
3. When the buyer confirms, open the quote and click **Convert to invoice** - the invoice
   appears in their account with a due date.
4. Mark the invoice **paid** once money lands. Both documents print cleanly with
   **Print / Save PDF**.

## Project structure

```
avocado_market/
├── app.py                      routes, auth, admin actions
├── db.py                       schema, connection helpers, seed data
├── requirements.txt
├── instance/avocado.db         created on first run (not in git)
├── static/
│   ├── css/style.css           full design system
│   ├── js/main.js              small storefront helpers
│   ├── js/items.js            quote/invoice line-item calculator
│   └── img/                    product and farm photos
└── templates/
    ├── base.html, index.html, product.html, about.html, contact.html
    ├── login.html, signup.html, account.html
    ├── quote_view.html, invoice_view.html, error.html
    └── admin/                  dashboard, products, quotes, invoices, customers
```

## Before going live

- Change `SECRET_KEY` to a long random string.
- Change the admin email and password.
- Set `debug=False` and serve with a real WSGI server, e.g. `waitress` on Windows:
  `pip install waitress` then `waitress-serve --port=8000 app:app`.
- Put it behind HTTPS. On Truehost cPanel, use **Setup Python App** if your plan includes it,
  otherwise run it on a small VPS and point your domain at it.
- Back up `instance/avocado.db` regularly (it holds all products, quotes and invoices).
- For online card or M-Pesa payments you would add a payment gateway later; for now invoices
  record what is owed and you confirm payment manually.

## Notes

- Passwords are hashed with Werkzeug, sessions are signed with `SECRET_KEY`,
  and buyers can only open their own quotes and invoices.
- This first version has no CSRF tokens. Fine for local use; add `Flask-WTF` before
  exposing it to the public internet.
