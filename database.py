import sqlite3
from pathlib import Path
from urllib.parse import unquote

DB_PATH = Path(__file__).parent / "prices.db"

DASHBOARD_QUERY = """
WITH lowest AS (
    SELECT
        product_name,
        store_name,
        product_url,
        price AS lowest_price,
        updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY product_name
            ORDER BY price ASC, updated_at DESC
        ) AS rn
    FROM price_entries
),
last_updated AS (
    SELECT product_name, MAX(updated_at) AS last_updated
    FROM price_entries
    GROUP BY product_name
),
targets AS (
    SELECT product_name, MIN(target_price) AS target_price
    FROM price_entries
    WHERE target_price IS NOT NULL
    GROUP BY product_name
),
savings AS (
    SELECT
        product_name,
        MAX(price) - MIN(price) AS savings
    FROM price_entries
    GROUP BY product_name
    HAVING COUNT(*) > 1
)
SELECT
    l.product_name,
    l.lowest_price,
    l.store_name,
    l.product_url,
    t.target_price,
    u.last_updated,
    COALESCE(s.savings, 0) AS savings
FROM lowest l
JOIN last_updated u ON l.product_name = u.product_name
LEFT JOIN targets t ON l.product_name = t.product_name
LEFT JOIN savings s ON l.product_name = s.product_name
WHERE l.rn = 1
{search_clause}
{order_clause}
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS price_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            store_name TEXT NOT NULL,
            product_url TEXT NOT NULL,
            price REAL NOT NULL,
            target_price REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS product_images (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            original_filename TEXT,
            product_name TEXT,
            ai_detected_name TEXT,
            confirmed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL UNIQUE,
            product_id INTEGER REFERENCES products(id),
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            liked TEXT,
            message TEXT,
            page TEXT,
            user_agent TEXT,
            ip_address TEXT,
            time_on_page_seconds INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    _migrate_product_images(conn)
    _migrate_products(conn)
    _migrate_sanitize_product_urls(conn)
    conn.commit()
    conn.close()


def _migrate_sanitize_product_urls(conn):
    from product_urls import is_placeholder_product_url, normalize_product_url, stored_product_url

    # Legacy demo ASINs from an earlier seed — they caused price/URL mismatches.
    legacy_demo_markers = (
        "amazon.com/dp/b004yavf8i",
        "amazon.com/dp/b0863txgm3",
        "amazon.com/dp/b07vhs4dcx",
        "walmart.com/ip/logitech-wireless-mouse-m185",
        "target.com/p/logitech-m185-wireless-mouse",
        "bestbuy.com/site/sony-wh-1000xm4",
        "bestbuy.com/site/anker-7-in-1-usb-c-hub",
    )

    rows = conn.execute("SELECT id, product_url FROM price_entries").fetchall()
    for row in rows:
        url = row["product_url"] or ""
        url_lower = url.lower()
        if not url or is_placeholder_product_url(url):
            conn.execute("UPDATE price_entries SET product_url = ? WHERE id = ?", ("", row["id"]))
            continue
        if any(marker in url_lower for marker in legacy_demo_markers):
            conn.execute("UPDATE price_entries SET product_url = ? WHERE id = ?", ("", row["id"]))
            continue
        cleaned = stored_product_url(url)
        if cleaned and cleaned != url:
            conn.execute("UPDATE price_entries SET product_url = ? WHERE id = ?", (cleaned, row["id"]))
        elif not cleaned:
            conn.execute("UPDATE price_entries SET product_url = ? WHERE id = ?", ("", row["id"]))


def _migrate_products(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(watchlist)")}
    if "product_id" not in columns:
        conn.execute("ALTER TABLE watchlist ADD COLUMN product_id INTEGER REFERENCES products(id)")

    names = set()
    for row in conn.execute("SELECT DISTINCT product_name FROM price_entries"):
        if row[0]:
            names.add(row[0])
    for row in conn.execute("SELECT product_name FROM watchlist"):
        if row[0]:
            names.add(row[0])

    for name in names:
        conn.execute("INSERT OR IGNORE INTO products (name) VALUES (?)", (name,))

    for row in conn.execute("SELECT product_name FROM watchlist WHERE product_id IS NULL"):
        product_row = conn.execute(
            "SELECT id FROM products WHERE name = ? COLLATE NOCASE",
            (row[0],),
        ).fetchone()
        if product_row:
            conn.execute(
                "UPDATE watchlist SET product_id = ? WHERE product_name = ?",
                (product_row[0], row[0]),
            )


def _migrate_product_images(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(product_images)")}
    migrations = {
        "ai_brand": "ALTER TABLE product_images ADD COLUMN ai_brand TEXT",
        "ai_model_number": "ALTER TABLE product_images ADD COLUMN ai_model_number TEXT",
        "ai_confidence": "ALTER TABLE product_images ADD COLUMN ai_confidence REAL",
        "ai_analyzed": "ALTER TABLE product_images ADD COLUMN ai_analyzed INTEGER DEFAULT 0",
        "ai_error": "ALTER TABLE product_images ADD COLUMN ai_error TEXT",
    }
    for column, sql in migrations.items():
        if column not in columns:
            conn.execute(sql)


def ensure_product(product_name):
    name = (product_name or "").strip()
    if not name:
        return None
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO products (name) VALUES (?)", (name,))
    row = conn.execute("SELECT id, name FROM products WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
    conn.commit()
    conn.close()
    return dict(row) if row else None


def get_product_by_id(product_id):
    conn = get_db()
    row = conn.execute("SELECT id, name FROM products WHERE id = ?", (int(product_id),)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_product_id_by_name(product_name):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM products WHERE name = ? COLLATE NOCASE",
        (product_name,),
    ).fetchone()
    conn.close()
    return row["id"] if row else None


def add_price_entry(product_name, store_name, product_url, price, target_price=None):
    from product_urls import is_usable_product_url, normalize_product_url

    stored_url = normalize_product_url(product_url) if is_usable_product_url(product_url) else ""
    ensure_product(product_name)
    conn = get_db()
    conn.execute(
        """
        INSERT INTO price_entries (product_name, store_name, product_url, price, target_price)
        VALUES (?, ?, ?, ?, ?)
        """,
        (product_name, store_name, stored_url, price, target_price),
    )
    conn.commit()
    conn.close()


def get_product_store_entry(product_name, store_name):
    conn = get_db()
    row = conn.execute(
        """
        SELECT id, product_name, store_name, product_url, price, target_price, updated_at
        FROM price_entries
        WHERE product_name = ? COLLATE NOCASE AND store_name = ? COLLATE NOCASE
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (product_name, store_name),
    ).fetchone()
    conn.close()
    return row


def get_product_store_url(product_name, store_name):
    row = get_product_store_entry(product_name, store_name)
    return row["product_url"] if row else None


def get_dashboard_products(search=None, sort="price_asc"):
    search_clause = ""
    params = []

    if search:
        search_clause = "AND l.product_name LIKE ? COLLATE NOCASE"
        params.append(f"%{search}%")

    sort_map = {
        "price_asc": "l.lowest_price ASC, l.product_name COLLATE NOCASE",
        "price_desc": "l.lowest_price DESC, l.product_name COLLATE NOCASE",
        "name": "l.product_name COLLATE NOCASE",
        "updated": "u.last_updated DESC",
    }
    order_clause = f"ORDER BY {sort_map.get(sort, sort_map['price_asc'])}"

    query = DASHBOARD_QUERY.format(search_clause=search_clause, order_clause=order_clause)
    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_dashboard_summary():
    products = get_dashboard_products()
    total_products = len(products)
    total_alerts = 0
    savings_values = []
    todays_savings = 0.0
    best_deals = 0

    for row in products:
        target = row["target_price"]
        lowest = row["lowest_price"]
        savings = row["savings"] or 0.0
        if target is not None and lowest <= target:
            total_alerts += 1
            if savings > 0:
                todays_savings += savings
        if savings > 0:
            best_deals += 1
            savings_values.append(savings)

    avg_savings = sum(savings_values) / len(savings_values) if savings_values else 0.0

    return {
        "total_products": total_products,
        "total_alerts": total_alerts,
        "average_savings": avg_savings,
        "watching_products": get_watchlist_count(),
        "active_alerts": total_alerts,
        "todays_savings": todays_savings,
        "best_deals": best_deals,
    }


def product_exists(product_name):
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM price_entries WHERE product_name = ? LIMIT 1",
        (product_name,),
    ).fetchone()
    conn.close()
    return row is not None


def get_product_entries(product_name):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, product_name, store_name, product_url, price, target_price, updated_at
        FROM price_entries
        WHERE product_name = ?
        ORDER BY price ASC, store_name COLLATE NOCASE
        """,
        (product_name,),
    ).fetchall()
    conn.close()
    return rows


def get_product_target(product_name):
    conn = get_db()
    row = conn.execute(
        """
        SELECT MIN(target_price) AS target_price
        FROM price_entries
        WHERE product_name = ? AND target_price IS NOT NULL
        """,
        (product_name,),
    ).fetchone()
    conn.close()
    return row["target_price"] if row else None


def delete_product_by_id(product_id):
    from images import delete_image_file

    product = get_product_by_id(product_id)
    if not product:
        return False

    product_name = product["name"]
    filename = delete_product_image(product_name)
    if filename:
        delete_image_file(filename)

    conn = get_db()
    conn.execute("DELETE FROM watchlist WHERE product_id = ?", (product_id,))
    conn.execute(
        "DELETE FROM watchlist WHERE product_id IS NULL AND product_name = ? COLLATE NOCASE",
        (product_name,),
    )
    conn.execute(
        "DELETE FROM price_entries WHERE product_name = ? COLLATE NOCASE",
        (product_name,),
    )
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return True


def delete_product(product_name):
    product_name = (product_name or "").strip()
    if not product_name:
        return False
    product_id = get_product_id_by_name(product_name)
    if product_id:
        return delete_product_by_id(product_id)

    from images import delete_image_file

    filename = delete_product_image(product_name)
    if filename:
        delete_image_file(filename)

    conn = get_db()
    conn.execute(
        "DELETE FROM watchlist WHERE product_name = ? COLLATE NOCASE",
        (product_name,),
    )
    conn.execute(
        "DELETE FROM price_entries WHERE product_name = ? COLLATE NOCASE",
        (product_name,),
    )
    conn.commit()
    conn.close()
    return True


def rename_product(old_name, new_name):
    rename_product_image(old_name, new_name)
    rename_watchlist_product(old_name, new_name)
    conn = get_db()
    conn.execute(
        "UPDATE price_entries SET product_name = ? WHERE product_name = ? COLLATE NOCASE",
        (new_name, old_name),
    )
    conn.execute(
        "UPDATE products SET name = ? WHERE name = ? COLLATE NOCASE",
        (new_name, old_name),
    )
    conn.commit()
    conn.close()


def set_product_target(product_name, target_price):
    conn = get_db()
    conn.execute(
        "UPDATE price_entries SET target_price = ? WHERE product_name = ?",
        (target_price, product_name),
    )
    conn.commit()
    conn.close()


def update_entry(entry_id, store_name, product_url, price, target_price=None):
    from product_urls import is_usable_product_url, normalize_product_url

    stored_url = normalize_product_url(product_url) if is_usable_product_url(product_url) else ""
    conn = get_db()
    conn.execute(
        """
        UPDATE price_entries
        SET store_name = ?, product_url = ?, price = ?, target_price = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (store_name, stored_url, price, target_price, entry_id),
    )
    conn.commit()
    conn.close()


def add_entry_to_product(product_name, store_name, product_url, price, target_price=None):
    add_price_entry(product_name, store_name, product_url, price, target_price)


def delete_entry(entry_id):
    conn = get_db()
    conn.execute("DELETE FROM price_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def decode_product_name(name):
    return unquote(name)


def create_image_upload(upload_id, filename, original_filename):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO product_images (id, filename, original_filename, confirmed)
        VALUES (?, ?, ?, 0)
        """,
        (upload_id, filename, original_filename),
    )
    conn.commit()
    conn.close()


def get_image_upload(upload_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM product_images WHERE id = ?",
        (upload_id,),
    ).fetchone()
    conn.close()
    return row


def confirm_image_upload(upload_id, product_name, ai_detected_name=None):
    conn = get_db()
    conn.execute(
        """
        UPDATE product_images
        SET product_name = ?, ai_detected_name = COALESCE(ai_detected_name, ?), confirmed = 1
        WHERE id = ?
        """,
        (product_name, ai_detected_name, upload_id),
    )
    conn.commit()
    conn.close()


def save_ai_analysis(upload_id, result):
    conn = get_db()
    conn.execute(
        """
        UPDATE product_images
        SET ai_detected_name = ?,
            ai_brand = ?,
            ai_model_number = ?,
            ai_confidence = ?,
            ai_analyzed = 1,
            ai_error = ?
        WHERE id = ?
        """,
        (
            result.get("product_name"),
            result.get("brand"),
            result.get("model_number"),
            result.get("confidence"),
            result.get("error"),
            upload_id,
        ),
    )
    conn.commit()
    conn.close()


def get_product_image(product_name):
    conn = get_db()
    row = conn.execute(
        """
        SELECT filename, ai_detected_name
        FROM product_images
        WHERE product_name = ? AND confirmed = 1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (product_name,),
    ).fetchone()
    conn.close()
    return row


def get_product_images_map():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT product_name, filename
        FROM product_images
        WHERE confirmed = 1 AND product_name IS NOT NULL
        """
    ).fetchall()
    conn.close()
    return {row["product_name"]: row["filename"] for row in rows}


def rename_product_image(old_name, new_name):
    conn = get_db()
    conn.execute(
        "UPDATE product_images SET product_name = ? WHERE product_name = ?",
        (new_name, old_name),
    )
    conn.commit()
    conn.close()


def delete_product_image(product_name):
    conn = get_db()
    row = conn.execute(
        """
        SELECT id, filename FROM product_images
        WHERE product_name = ? AND confirmed = 1
        """,
        (product_name,),
    ).fetchone()
    if row:
        conn.execute("DELETE FROM product_images WHERE id = ?", (row["id"],))
        conn.commit()
    conn.close()
    return row["filename"] if row else None


def delete_unconfirmed_upload(upload_id):
    conn = get_db()
    row = conn.execute(
        "SELECT filename FROM product_images WHERE id = ? AND confirmed = 0",
        (upload_id,),
    ).fetchone()
    if row:
        conn.execute("DELETE FROM product_images WHERE id = ?", (upload_id,))
        conn.commit()
    conn.close()
    return row["filename"] if row else None


def add_to_watchlist(product_name):
    product = ensure_product(product_name)
    if not product:
        return
    conn = get_db()
    conn.execute(
        """
        INSERT OR IGNORE INTO watchlist (product_name, product_id)
        VALUES (?, ?)
        """,
        (product["name"], product["id"]),
    )
    conn.execute(
        """
        UPDATE watchlist
        SET product_id = ?
        WHERE product_name = ? COLLATE NOCASE AND product_id IS NULL
        """,
        (product["id"], product["name"]),
    )
    conn.commit()
    conn.close()


def remove_from_watchlist(product_name):
    product_name = (product_name or "").strip()
    if not product_name:
        return
    product_id = get_product_id_by_name(product_name)
    conn = get_db()
    if product_id:
        conn.execute("DELETE FROM watchlist WHERE product_id = ?", (product_id,))
    conn.execute(
        "DELETE FROM watchlist WHERE product_name = ? COLLATE NOCASE",
        (product_name,),
    )
    conn.commit()
    conn.close()


def remove_from_watchlist_by_id(product_id):
    conn = get_db()
    conn.execute("DELETE FROM watchlist WHERE product_id = ?", (int(product_id),))
    conn.commit()
    conn.close()


def is_on_watchlist(product_name):
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM watchlist WHERE product_name = ? LIMIT 1",
        (product_name,),
    ).fetchone()
    conn.close()
    return row is not None


def get_watchlist_names():
    conn = get_db()
    rows = conn.execute("SELECT product_name FROM watchlist").fetchall()
    conn.close()
    return {row["product_name"] for row in rows}


def rename_watchlist_product(old_name, new_name):
    conn = get_db()
    conn.execute(
        "UPDATE watchlist SET product_name = ? WHERE product_name = ?",
        (new_name, old_name),
    )
    conn.commit()
    conn.close()


def get_watchlist_products():
    conn = get_db()
    rows = conn.execute(
        """
        WITH lowest AS (
            SELECT
                product_name,
                store_name,
                product_url,
                price AS lowest_price,
                ROW_NUMBER() OVER (
                    PARTITION BY product_name
                    ORDER BY price ASC, updated_at DESC
                ) AS rn
            FROM price_entries
        ),
        targets AS (
            SELECT product_name, MIN(target_price) AS target_price
            FROM price_entries
            WHERE target_price IS NOT NULL
            GROUP BY product_name
        )
        SELECT
            w.product_id,
            COALESCE(p.name, w.product_name) AS product_name,
            w.added_at,
            l.lowest_price,
            l.store_name,
            l.product_url,
            t.target_price
        FROM watchlist w
        LEFT JOIN products p ON p.id = w.product_id
        LEFT JOIN lowest l ON l.product_name = COALESCE(p.name, w.product_name) AND l.rn = 1
        LEFT JOIN targets t ON t.product_name = COALESCE(p.name, w.product_name)
        ORDER BY w.added_at DESC
        """
    ).fetchall()
    conn.close()
    return rows


def get_watchlist_count():
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) AS count FROM watchlist").fetchone()
    conn.close()
    return row["count"]


def save_contact_message(name, email, message):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO contact_messages (name, email, message)
        VALUES (?, ?, ?)
        """,
        (name, email, message),
    )
    conn.commit()
    conn.close()


def save_portfolio_feedback(liked, message, page, user_agent, ip_address, time_on_page_seconds):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO portfolio_feedback (
            liked,
            message,
            page,
            user_agent,
            ip_address,
            time_on_page_seconds
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (liked, message, page, user_agent, ip_address, time_on_page_seconds),
    )
    conn.commit()
    conn.close()


def get_portfolio_feedback(limit=100):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, liked, message, page, user_agent, ip_address, time_on_page_seconds, created_at
        FROM portfolio_feedback
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    conn.close()
    return rows
