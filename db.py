"""Database helpers and seed data for Avocado Market Kenya."""
import os
import sqlite3
from datetime import datetime, timedelta
from flask import g
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "avocado.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT,
    phone         TEXT,
    company       TEXT,
    is_admin      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    variety      TEXT,
    grade        TEXT,
    description  TEXT,
    price_per_kg REAL NOT NULL,
    moq_kg       INTEGER NOT NULL DEFAULT 20,
    origin       TEXT,
    packaging    TEXT,
    stock_kg     INTEGER NOT NULL DEFAULT 0,
    image        TEXT,
    active       INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quotes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_no    TEXT UNIQUE NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    status      TEXT NOT NULL DEFAULT 'requested',
    notes       TEXT,
    total       REAL NOT NULL DEFAULT 0,
    valid_until TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quote_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_id     INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
    product_id   INTEGER REFERENCES products(id),
    description  TEXT,
    quantity_kg  REAL NOT NULL,
    price_per_kg REAL NOT NULL,
    line_total   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT UNIQUE NOT NULL,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    quote_id   INTEGER REFERENCES quotes(id),
    status     TEXT NOT NULL DEFAULT 'unpaid',
    due_date   TEXT,
    notes      TEXT,
    total      REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id   INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    product_id   INTEGER REFERENCES products(id),
    description  TEXT,
    quantity_kg  REAL NOT NULL,
    price_per_kg REAL NOT NULL,
    line_total   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT,
    email      TEXT,
    phone      TEXT,
    body       TEXT,
    created_at TEXT NOT NULL
);
"""

SEED_PRODUCTS = [
    dict(
        name="Hass Avocado - Grade A (Export)",
        variety="Hass",
        grade="Grade A / Export",
        description=(
            "Premium Hass avocado from Murang'a and Kiambu highlands. Deep green, "
            "pebbled skin, oil content 10-12% at harvest, uniform size 140-220g per fruit. "
            "Hand-picked, field-sorted and packed the same day. Ideal for exporters, "
            "supermarkets and hotels."
        ),
        price_per_kg=220.0,
        moq_kg=50,
        origin="Murang'a, Kiambu",
        packaging="10kg / 20kg vented cartons",
        stock_kg=4200,
        image="hass.jpg",
    ),
    dict(
        name="Hass Avocado - Grade B (Local Trade)",
        variety="Hass",
        grade="Grade B",
        description=(
            "Same farm-fresh Hass, sorted for the local market. Slightly varied sizing, "
            "excellent taste and shelf life of 7-10 days. Best value for groceries, "
            "fruit traders and restaurants in Nairobi."
        ),
        price_per_kg=150.0,
        moq_kg=20,
        origin="Kiambu",
        packaging="10kg cartons or 90kg sacks",
        stock_kg=6800,
        image="hass.jpg",
    ),
    dict(
        name="Fuerte Avocado",
        variety="Fuerte",
        grade="Grade A",
        description=(
            "Smooth, thin-skinned Fuerte with creamy, low-fibre flesh. Popular with juice "
            "processors and household buyers. Delivered firm and ripens in 3-5 days at "
            "room temperature."
        ),
        price_per_kg=180.0,
        moq_kg=30,
        origin="Nyeri, Meru",
        packaging="10kg / 18kg cartons",
        stock_kg=3500,
        image="fuerte.jpg",
    ),
    dict(
        name="Jumbo Avocado",
        variety="Jumbo",
        grade="Grade A",
        description=(
            "Large fruit, 250-400g each, thick flesh and small seed. Sold mainly to "
            "caterers, salad processors and events. Consistent supply from Trans Nzoia "
            "and Kisii farms."
        ),
        price_per_kg=160.0,
        moq_kg=20,
        origin="Trans Nzoia, Kisii",
        packaging="18kg cartons",
        stock_kg=2400,
        image="fuerte.jpg",
    ),
    dict(
        name="Pinkerton Avocado",
        variety="Pinkerton",
        grade="Grade A",
        description=(
            "Long, pear-shaped fruit with a small seed and high flesh-to-skin ratio. "
            "Excellent for retail packs and restaurant platters. Available in season "
            "from late October."
        ),
        price_per_kg=190.0,
        moq_kg=30,
        origin="Meru",
        packaging="10kg / 18kg cartons",
        stock_kg=1800,
        image="fuerte.jpg",
    ),
    dict(
        name="Organic Hass Avocado (Certified)",
        variety="Hass",
        grade="Organic / Grade A",
        description=(
            "Certified organic Hass grown without synthetic pesticides. Traceable batch "
            "codes, residue-free, suitable for buyers needing organic documentation. "
            "Limited weekly volumes."
        ),
        price_per_kg=260.0,
        moq_kg=100,
        origin="Kisii",
        packaging="10kg cartons, batch-coded",
        stock_kg=900,
        image="hass.jpg",
    ),
]


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        os.makedirs(INSTANCE_DIR, exist_ok=True)
        g.db = _connect(DB_PATH)
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(admin_email, admin_password):
    """Create tables and seed the first admin plus sample products."""
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    conn = _connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        cur = conn.execute("SELECT COUNT(*) AS c FROM users")
        if cur.fetchone()["c"] == 0:
            conn.execute(
                "INSERT INTO users (email, password_hash, full_name, phone, company, is_admin, created_at)"
                " VALUES (?,?,?,?,?,1,?)",
                (
                    admin_email,
                    generate_password_hash(admin_password),
                    "Brian Muia",
                    "+254797799104",
                    "Avocado Market Kenya",
                    _now(),
                ),
            )
        cur = conn.execute("SELECT COUNT(*) AS c FROM products")
        if cur.fetchone()["c"] == 0:
            for p in SEED_PRODUCTS:
                conn.execute(
                    "INSERT INTO products (name, variety, grade, description, price_per_kg, moq_kg,"
                    " origin, packaging, stock_kg, image, active, created_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,1,?)",
                    (
                        p["name"], p["variety"], p["grade"], p["description"], p["price_per_kg"],
                        p["moq_kg"], p["origin"], p["packaging"], p["stock_kg"], p["image"], _now(),
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def next_number(conn, table, prefix, column):
    """Generate a sequential document number such as Q-2026-0007."""
    year = datetime.now().year
    like = f"{prefix}-{year}-%"
    row = conn.execute(
        f"SELECT {column} AS n FROM {table} WHERE {column} LIKE ? ORDER BY id DESC LIMIT 1", (like,)
    ).fetchone()
    seq = 1
    if row and row["n"]:
        try:
            seq = int(str(row["n"]).split("-")[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}-{year}-{seq:04d}"


def default_valid_until(days=14):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
