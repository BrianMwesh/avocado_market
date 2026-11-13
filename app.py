"""
Avocado Market Kenya
A small B2B/B2C avocado trading site built with Flask + SQLite.

Run locally:
    python -m venv venv
    venv\\Scripts\\activate      (Windows)   |   source venv/bin/activate  (macOS/Linux)
    pip install -r requirements.txt
    python app.py
    open http://127.0.0.1:5000
"""
import os
from datetime import datetime
from functools import wraps
from urllib.parse import quote as urlquote

from flask import (
    Flask, abort, flash, g, redirect, render_template, request,
    session, url_for, jsonify,
)
from werkzeug.security import check_password_hash, generate_password_hash

import db as database

# --------------------------------------------------------------------------
# Configuration (change these three lines or set env vars)
# --------------------------------------------------------------------------
SITE_NAME = os.environ.get("SITE_NAME", "Avocado Market Kenya")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "254797799104")  # 0797 799 104
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "orders@avocadomarket.co.ke")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@avocadomarket.co.ke")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@1234")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-this-key-before-going-live")

app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY, JSON_SORT_KEYS=False)
app.teardown_appcontext(database.close_db)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def money(value):
    try:
        return "KES {:,.2f}".format(float(value or 0))
    except (TypeError, ValueError):
        return "KES 0.00"


def nice_date(value, fmt="%d %b %Y"):
    if not value:
        return ""
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value)[:19], pattern).strftime(fmt)
        except ValueError:
            continue
    return str(value)


app.jinja_env.filters["money"] = money
app.jinja_env.filters["nice_date"] = nice_date


def wa_link(message):
    return "https://wa.me/{}?text={}".format(WHATSAPP_NUMBER, urlquote(message))


@app.context_processor
def inject_globals():
    return dict(
        site_name=SITE_NAME,
        whatsapp_number=WHATSAPP_NUMBER,
        whatsapp_display="+{} {}".format(WHATSAPP_NUMBER[:3], WHATSAPP_NUMBER[3:]),
        contact_email=CONTACT_EMAIL,
        wa_link=wa_link,
        current_user=g.get("user"),
        now=datetime.now(),
    )


def load_user():
    uid = session.get("user_id")
    g.user = None
    if uid:
        g.user = database.get_db().execute(
            "SELECT * FROM users WHERE id = ?", (uid,)
        ).fetchone()
        if g.user is None:
            session.clear()
    return g.user


@app.before_request
def before_request():
    load_user()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.get("user"):
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = g.get("user")
        if not user:
            flash("Please sign in as an administrator.", "info")
            return redirect(url_for("login", next=request.path))
        if not user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def parse_items(conn):
    """Read quote/invoice line items posted from the form."""
    product_ids = request.form.getlist("product_id")
    descriptions = request.form.getlist("description")
    quantities = request.form.getlist("quantity_kg")
    prices = request.form.getlist("price_per_kg")
    items = []
    for i, raw_qty in enumerate(quantities):
        try:
            qty = float(raw_qty or 0)
            price = float(prices[i] if i < len(prices) else 0)
        except ValueError:
            continue
        if qty <= 0:
            continue
        pid = None
        if i < len(product_ids) and product_ids[i]:
            try:
                pid = int(product_ids[i])
            except ValueError:
                pid = None
        desc = (descriptions[i] if i < len(descriptions) else "") or ""
        if not desc.strip() and pid:
            row = conn.execute("SELECT name FROM products WHERE id = ?", (pid,)).fetchone()
            desc = row["name"] if row else "Avocado supply"
        items.append(
            dict(product_id=pid, description=desc.strip(), quantity_kg=qty,
                 price_per_kg=price, line_total=round(qty * price, 2))
        )
    return items


def fetch_document(conn, table, items_table, fk, doc_id):
    doc = conn.execute(
        "SELECT d.*, u.full_name, u.email, u.phone, u.company FROM {} d"
        " JOIN users u ON u.id = d.user_id WHERE d.id = ?".format(table),
        (doc_id,),
    ).fetchone()
    if not doc:
        return None, []
    items = conn.execute(
        "SELECT * FROM {} WHERE {} = ? ORDER BY id".format(items_table, fk), (doc_id,)
    ).fetchall()
    return doc, items


# --------------------------------------------------------------------------
# Public storefront
# --------------------------------------------------------------------------
@app.route("/")
def index():
    conn = database.get_db()
    q = (request.args.get("q") or "").strip()
    variety = (request.args.get("variety") or "").strip()

    sql = "SELECT * FROM products WHERE active = 1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR description LIKE ? OR origin LIKE ? OR variety LIKE ?)"
        like = "%{}%".format(q)
        params += [like, like, like, like]
    if variety:
        sql += " AND variety = ?"
        params.append(variety)
    sql += " ORDER BY price_per_kg DESC"
    products = conn.execute(sql, params).fetchall()

    varieties = [r["variety"] for r in conn.execute(
        "SELECT DISTINCT variety FROM products WHERE active = 1 AND variety IS NOT NULL ORDER BY variety"
    ).fetchall()]
    return render_template("index.html", products=products, varieties=varieties, q=q, active_variety=variety)


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = database.get_db()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ? AND active = 1", (product_id,)
    ).fetchone()
    if not product:
        abort(404)
    related = conn.execute(
        "SELECT * FROM products WHERE active = 1 AND id != ? ORDER BY RANDOM() LIMIT 3", (product_id,)
    ).fetchall()
    return render_template("product.html", product=product, related=related)


@app.route("/products")
def products():
    return redirect(url_for("index"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        conn = database.get_db()
        conn.execute(
            "INSERT INTO messages (name, email, phone, body, created_at) VALUES (?,?,?,?,?)",
            (
                (request.form.get("name") or "").strip(),
                (request.form.get("email") or "").strip(),
                (request.form.get("phone") or "").strip(),
                (request.form.get("body") or "").strip(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        flash("Thank you. Our sales team will get back to you shortly.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        full_name = (request.form.get("full_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        company = (request.form.get("company") or "").strip()

        errors = []
        if "@" not in email or "." not in email:
            errors.append("Enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if not full_name:
            errors.append("Enter your name or the buyer's name.")

        conn = database.get_db()
        if not errors:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                errors.append("That email is already registered. Try signing in instead.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("signup.html", form=request.form)

        conn.execute(
            "INSERT INTO users (email, password_hash, full_name, phone, company, is_admin, created_at)"
            " VALUES (?,?,?,?,?,0,?)",
            (email, generate_password_hash(password), full_name, phone, company,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        session["user_id"] = row["id"]
        flash("Welcome to {}.".format(SITE_NAME), "success")
        return redirect(request.args.get("next") or url_for("account"))

    return render_template("signup.html", form={})


@app.route("/admin/login")
def admin_login():
    """Direct door for the shop owner: same form, admin framing."""
    return redirect(url_for("login", admin=1))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        conn = database.get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("Signed in as {}.".format(user["email"]), "success")
            target = request.args.get("next")
            if target:
                return redirect(target)
            return redirect(url_for("admin_dashboard") if user["is_admin"] else url_for("account"))
        flash("Wrong email or password.", "error")
    return render_template("login.html", form={},
                           admin_mode=bool(request.args.get("admin")))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# Customer account: quotes and invoices
# --------------------------------------------------------------------------
@app.route("/account")
@login_required
def account():
    conn = database.get_db()
    quotes = conn.execute(
        "SELECT q.*, (SELECT COUNT(*) FROM quote_items qi WHERE qi.quote_id = q.id) AS items"
        " FROM quotes q WHERE q.user_id = ? ORDER BY q.id DESC", (g.user["id"],)
    ).fetchall()
    invoices = conn.execute(
        "SELECT i.*, (SELECT COUNT(*) FROM invoice_items ii WHERE ii.invoice_id = i.id) AS items"
        " FROM invoices i WHERE i.user_id = ? ORDER BY i.id DESC", (g.user["id"],)
    ).fetchall()
    return render_template("account.html", quotes=quotes, invoices=invoices)


@app.route("/account/quote/<int:quote_id>")
@login_required
def view_quote(quote_id):
    conn = database.get_db()
    quote, items = fetch_document(conn, "quotes", "quote_items", "quote_id", quote_id)
    if not quote:
        abort(404)
    if quote["user_id"] != g.user["id"] and not g.user["is_admin"]:
        abort(403)
    return render_template("quote_view.html", quote=quote, items=items, is_admin=bool(g.user["is_admin"]))


@app.route("/account/invoice/<int:invoice_id>")
@login_required
def view_invoice(invoice_id):
    conn = database.get_db()
    invoice, items = fetch_document(conn, "invoices", "invoice_items", "invoice_id", invoice_id)
    if not invoice:
        abort(404)
    if invoice["user_id"] != g.user["id"] and not g.user["is_admin"]:
        abort(403)
    return render_template("invoice_view.html", invoice=invoice, items=items, is_admin=bool(g.user["is_admin"]))


@app.route("/account/request-quote", methods=["POST"])
@login_required
def request_quote():
    """A signed-in buyer asks for a quote from a product page."""
    conn = database.get_db()
    product_id = request.form.get("product_id")
    product = conn.execute("SELECT * FROM products WHERE id = ?", (int(product_id),)).fetchone() \
        if product_id and product_id.isdigit() else None
    if not product:
        abort(400)
    try:
        qty = float(request.form.get("quantity_kg") or product["moq_kg"])
    except ValueError:
        qty = float(product["moq_kg"])

    quote_no = database.next_number(conn, "quotes", "Q", "quote_no")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    note = (request.form.get("notes") or "").strip()
    cur = conn.execute(
        "INSERT INTO quotes (quote_no, user_id, status, notes, total, valid_until, created_at, updated_at)"
        " VALUES (?,?,'requested',?,?,?,?,?)",
        (quote_no, g.user["id"], note, round(qty * product["price_per_kg"], 2),
         database.default_valid_until(), now, now),
    )
    conn.execute(
        "INSERT INTO quote_items (quote_id, product_id, description, quantity_kg, price_per_kg, line_total)"
        " VALUES (?,?,?,?,?,?)",
        (cur.lastrowid, product["id"], product["name"], qty, product["price_per_kg"],
         round(qty * product["price_per_kg"], 2)),
    )
    conn.commit()
    flash(
        "Quote request {} received. Our sales team will send you a formal quote and it will "
        "appear under My Quotes.".format(quote_no),
        "success",
    )
    return redirect(url_for("account"))


# --------------------------------------------------------------------------
# Admin: dashboard and products
# --------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = database.get_db()
    stats = dict(
        products=conn.execute("SELECT COUNT(*) c FROM products").fetchone()["c"],
        customers=conn.execute("SELECT COUNT(*) c FROM users WHERE is_admin = 0").fetchone()["c"],
        quotes=conn.execute("SELECT COUNT(*) c FROM quotes").fetchone()["c"],
        open_quotes=conn.execute(
            "SELECT COUNT(*) c FROM quotes WHERE status IN ('requested','sent')").fetchone()["c"],
        invoices=conn.execute("SELECT COUNT(*) c FROM invoices").fetchone()["c"],
        unpaid=conn.execute(
            "SELECT COUNT(*) c FROM invoices WHERE status = 'unpaid'").fetchone()["c"],
        unpaid_value=conn.execute(
            "SELECT COALESCE(SUM(total),0) v FROM invoices WHERE status = 'unpaid'").fetchone()["v"],
        revenue=conn.execute(
            "SELECT COALESCE(SUM(total),0) v FROM invoices WHERE status = 'paid'").fetchone()["v"],
    )
    recent_quotes = conn.execute(
        "SELECT q.*, u.full_name, u.company FROM quotes q JOIN users u ON u.id = q.user_id"
        " ORDER BY q.id DESC LIMIT 6").fetchall()
    recent_invoices = conn.execute(
        "SELECT i.*, u.full_name, u.company FROM invoices i JOIN users u ON u.id = i.user_id"
        " ORDER BY i.id DESC LIMIT 6").fetchall()
    return render_template("admin/dashboard.html", stats=stats,
                           recent_quotes=recent_quotes, recent_invoices=recent_invoices)


@app.route("/admin/products")
@admin_required
def admin_products():
    conn = database.get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY active DESC, id DESC").fetchall()
    return render_template("admin/products.html", products=rows)


@app.route("/admin/products/new", methods=["GET", "POST"])
@admin_required
def admin_product_new():
    if request.method == "POST":
        return _save_product(None)
    return render_template("admin/product_form.html", product=None)


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_product_edit(product_id):
    conn = database.get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        abort(404)
    if request.method == "POST":
        return _save_product(product_id)
    return render_template("admin/product_form.html", product=product)


def _save_product(product_id):
    conn = database.get_db()
    f = request.form
    try:
        price = float(f.get("price_per_kg") or 0)
        moq = int(float(f.get("moq_kg") or 0))
        stock = int(float(f.get("stock_kg") or 0))
    except ValueError:
        flash("Price, MOQ and stock must be numbers.", "error")
        return redirect(request.path)
    image = (f.get("image") or "").strip() or "hass.jpg"
    values = (
        (f.get("name") or "").strip(),
        (f.get("variety") or "").strip(),
        (f.get("grade") or "").strip(),
        (f.get("description") or "").strip(),
        price, moq,
        (f.get("origin") or "").strip(),
        (f.get("packaging") or "").strip(),
        stock, image, 1 if f.get("active") else 0,
    )
    if not values[0]:
        flash("Product name is required.", "error")
        return redirect(request.path)

    if product_id:
        conn.execute(
            "UPDATE products SET name=?, variety=?, grade=?, description=?, price_per_kg=?, moq_kg=?,"
            " origin=?, packaging=?, stock_kg=?, image=?, active=? WHERE id=?", values + (product_id,))
        flash("Product updated.", "success")
    else:
        conn.execute(
            "INSERT INTO products (name, variety, grade, description, price_per_kg, moq_kg, origin,"
            " packaging, stock_kg, image, active, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            values + (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        flash("Product created.", "success")
    conn.commit()
    return redirect(url_for("admin_products"))


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def admin_product_delete(product_id):
    conn = database.get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("admin_products"))


# --------------------------------------------------------------------------
# Admin: quotes
# --------------------------------------------------------------------------
@app.route("/admin/quotes")
@admin_required
def admin_quotes():
    conn = database.get_db()
    rows = conn.execute(
        "SELECT q.*, u.full_name, u.company, u.email FROM quotes q JOIN users u ON u.id = q.user_id"
        " ORDER BY q.id DESC").fetchall()
    return render_template("admin/quotes.html", quotes=rows)


@app.route("/admin/quotes/new", methods=["GET", "POST"])
@admin_required
def admin_quote_new():
    conn = database.get_db()
    if request.method == "POST":
        user_id = request.form.get("user_id")
        items = parse_items(conn)
        if not user_id or not items:
            flash("Choose a customer and add at least one line item.", "error")
            return redirect(url_for("admin_quote_new"))
        quote_no = database.next_number(conn, "quotes", "Q", "quote_no")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = round(sum(i["line_total"] for i in items), 2)
        cur = conn.execute(
            "INSERT INTO quotes (quote_no, user_id, status, notes, total, valid_until, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (quote_no, int(user_id), request.form.get("status") or "sent",
             (request.form.get("notes") or "").strip(), total,
             request.form.get("valid_until") or database.default_valid_until(), now, now),
        )
        for i in items:
            conn.execute(
                "INSERT INTO quote_items (quote_id, product_id, description, quantity_kg, price_per_kg,"
                " line_total) VALUES (?,?,?,?,?,?)",
                (cur.lastrowid, i["product_id"], i["description"], i["quantity_kg"],
                 i["price_per_kg"], i["line_total"]),
            )
        conn.commit()
        flash("Quote {} created.".format(quote_no), "success")
        return redirect(url_for("admin_quote_view", quote_id=cur.lastrowid))

    customers = conn.execute(
        "SELECT id, full_name, email, company FROM users WHERE is_admin = 0 ORDER BY full_name").fetchall()
    products = conn.execute("SELECT * FROM products WHERE active = 1 ORDER BY name").fetchall()
    return render_template("admin/quote_form.html", customers=customers, products=products,
                           default_valid_until=database.default_valid_until())


@app.route("/admin/quotes/<int:quote_id>")
@admin_required
def admin_quote_view(quote_id):
    conn = database.get_db()
    quote, items = fetch_document(conn, "quotes", "quote_items", "quote_id", quote_id)
    if not quote:
        abort(404)
    return render_template("quote_view.html", quote=quote, items=items, is_admin=True)


@app.route("/admin/quotes/<int:quote_id>/status", methods=["POST"])
@admin_required
def admin_quote_status(quote_id):
    status = request.form.get("status")
    if status not in ("requested", "sent", "accepted", "declined"):
        abort(400)
    conn = database.get_db()
    conn.execute("UPDATE quotes SET status = ?, updated_at = ? WHERE id = ?",
                 (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), quote_id))
    conn.commit()
    flash("Quote marked as {}.".format(status), "success")
    return redirect(url_for("admin_quote_view", quote_id=quote_id))


@app.route("/admin/quotes/<int:quote_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_quote_edit(quote_id):
    conn = database.get_db()
    quote, items = fetch_document(conn, "quotes", "quote_items", "quote_id", quote_id)
    if not quote:
        abort(404)
    if request.method == "POST":
        new_items = parse_items(conn)
        if not new_items:
            flash("A quote needs at least one line item.", "error")
            return redirect(url_for("admin_quote_edit", quote_id=quote_id))
        total = round(sum(i["line_total"] for i in new_items), 2)
        conn.execute(
            "UPDATE quotes SET notes=?, total=?, valid_until=?, updated_at=? WHERE id=?",
            ((request.form.get("notes") or "").strip(), total,
             request.form.get("valid_until") or quote["valid_until"],
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), quote_id))
        conn.execute("DELETE FROM quote_items WHERE quote_id = ?", (quote_id,))
        for i in new_items:
            conn.execute(
                "INSERT INTO quote_items (quote_id, product_id, description, quantity_kg, price_per_kg,"
                " line_total) VALUES (?,?,?,?,?,?)",
                (quote_id, i["product_id"], i["description"], i["quantity_kg"],
                 i["price_per_kg"], i["line_total"]))
        conn.commit()
        flash("Quote updated.", "success")
        return redirect(url_for("admin_quote_view", quote_id=quote_id))

    customers = conn.execute(
        "SELECT id, full_name, email, company FROM users WHERE is_admin = 0 ORDER BY full_name").fetchall()
    products = conn.execute("SELECT * FROM products WHERE active = 1 ORDER BY name").fetchall()
    return render_template("admin/quote_form.html", customers=customers, products=products,
                           quote=quote, items=items,
                           default_valid_until=database.default_valid_until())


@app.route("/admin/quotes/<int:quote_id>/delete", methods=["POST"])
@admin_required
def admin_quote_delete(quote_id):
    conn = database.get_db()
    conn.execute("DELETE FROM quote_items WHERE quote_id = ?", (quote_id,))
    conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    conn.commit()
    flash("Quote deleted.", "success")
    return redirect(url_for("admin_quotes"))


@app.route("/admin/quotes/<int:quote_id>/invoice", methods=["POST"])
@admin_required
def admin_quote_to_invoice(quote_id):
    conn = database.get_db()
    quote, items = fetch_document(conn, "quotes", "quote_items", "quote_id", quote_id)
    if not quote:
        abort(404)
    invoice_no = database.next_number(conn, "invoices", "INV", "invoice_no")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        "INSERT INTO invoices (invoice_no, user_id, quote_id, status, due_date, notes, total, created_at)"
        " VALUES (?,?,?,'unpaid',?,?,?,?)",
        (invoice_no, quote["user_id"], quote_id,
         request.form.get("due_date") or database.default_valid_until(7),
         quote["notes"], quote["total"], now),
    )
    for i in items:
        conn.execute(
            "INSERT INTO invoice_items (invoice_id, product_id, description, quantity_kg, price_per_kg,"
            " line_total) VALUES (?,?,?,?,?,?)",
            (cur.lastrowid, i["product_id"], i["description"], i["quantity_kg"],
             i["price_per_kg"], i["line_total"]))
    conn.execute("UPDATE quotes SET status = 'accepted', updated_at = ? WHERE id = ?", (now, quote_id))
    conn.commit()
    flash("Invoice {} created from {}.".format(invoice_no, quote["quote_no"]), "success")
    return redirect(url_for("admin_invoice_view", invoice_id=cur.lastrowid))


# --------------------------------------------------------------------------
# Admin: invoices
# --------------------------------------------------------------------------
@app.route("/admin/invoices")
@admin_required
def admin_invoices():
    conn = database.get_db()
    rows = conn.execute(
        "SELECT i.*, u.full_name, u.company, u.email FROM invoices i JOIN users u ON u.id = i.user_id"
        " ORDER BY i.id DESC").fetchall()
    return render_template("admin/invoices.html", invoices=rows)


@app.route("/admin/invoices/new", methods=["GET", "POST"])
@admin_required
def admin_invoice_new():
    conn = database.get_db()
    if request.method == "POST":
        user_id = request.form.get("user_id")
        items = parse_items(conn)
        if not user_id or not items:
            flash("Choose a customer and add at least one line item.", "error")
            return redirect(url_for("admin_invoice_new"))
        invoice_no = database.next_number(conn, "invoices", "INV", "invoice_no")
        total = round(sum(i["line_total"] for i in items), 2)
        cur = conn.execute(
            "INSERT INTO invoices (invoice_no, user_id, quote_id, status, due_date, notes, total, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (invoice_no, int(user_id), None, "unpaid",
             request.form.get("due_date") or database.default_valid_until(7),
             (request.form.get("notes") or "").strip(), total,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        for i in items:
            conn.execute(
                "INSERT INTO invoice_items (invoice_id, product_id, description, quantity_kg, price_per_kg,"
                " line_total) VALUES (?,?,?,?,?,?)",
                (cur.lastrowid, i["product_id"], i["description"], i["quantity_kg"],
                 i["price_per_kg"], i["line_total"]))
        conn.commit()
        flash("Invoice {} created.".format(invoice_no), "success")
        return redirect(url_for("admin_invoice_view", invoice_id=cur.lastrowid))

    customers = conn.execute(
        "SELECT id, full_name, email, company FROM users WHERE is_admin = 0 ORDER BY full_name").fetchall()
    products = conn.execute("SELECT * FROM products WHERE active = 1 ORDER BY name").fetchall()
    return render_template("admin/invoice_form.html", customers=customers, products=products,
                           default_due_date=database.default_valid_until(7))


@app.route("/admin/invoices/<int:invoice_id>")
@admin_required
def admin_invoice_view(invoice_id):
    conn = database.get_db()
    invoice, items = fetch_document(conn, "invoices", "invoice_items", "invoice_id", invoice_id)
    if not invoice:
        abort(404)
    return render_template("invoice_view.html", invoice=invoice, items=items, is_admin=True)


@app.route("/admin/invoices/<int:invoice_id>/status", methods=["POST"])
@admin_required
def admin_invoice_status(invoice_id):
    status = request.form.get("status")
    if status not in ("unpaid", "paid", "cancelled"):
        abort(400)
    conn = database.get_db()
    conn.execute("UPDATE invoices SET status = ? WHERE id = ?", (status, invoice_id))
    conn.commit()
    flash("Invoice marked as {}.".format(status), "success")
    return redirect(url_for("admin_invoice_view", invoice_id=invoice_id))


@app.route("/admin/invoices/<int:invoice_id>/delete", methods=["POST"])
@admin_required
def admin_invoice_delete(invoice_id):
    conn = database.get_db()
    conn.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    conn.commit()
    flash("Invoice deleted.", "success")
    return redirect(url_for("admin_invoices"))


@app.route("/admin/customers")
@admin_required
def admin_customers():
    conn = database.get_db()
    rows = conn.execute(
        "SELECT u.*, (SELECT COUNT(*) FROM quotes q WHERE q.user_id = u.id) AS quote_count,"
        " (SELECT COUNT(*) FROM invoices i WHERE i.user_id = u.id) AS invoice_count"
        " FROM users u WHERE u.is_admin = 0 ORDER BY u.id DESC").fetchall()
    return render_template("admin/customers.html", customers=rows)


# --------------------------------------------------------------------------
# Small JSON endpoint used by the item editor
# --------------------------------------------------------------------------
@app.route("/api/products/<int:product_id>")
def api_product(product_id):
    conn = database.get_db()
    row = conn.execute(
        "SELECT id, name, price_per_kg, moq_kg FROM products WHERE id = ? AND active = 1",
        (product_id,)).fetchone()
    if not row:
        abort(404)
    return jsonify(dict(row))


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403,
                           message="You do not have access to this page."), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404,
                           message="We could not find that page."), 404


def create_app():
    database.init_db(ADMIN_EMAIL, ADMIN_PASSWORD)
    return app


if __name__ == "__main__":
    create_app()
    print("\n  {} running at http://127.0.0.1:5000".format(SITE_NAME))
    print("  Admin login: {} / {}".format(ADMIN_EMAIL, ADMIN_PASSWORD))
    print("  WhatsApp orders: +{}\n".format(WHATSAPP_NUMBER))
    app.run(debug=True, port=5000)
