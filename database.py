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
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL UNIQUE,
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
    _migrate_product_images(conn)
    conn.commit()
    conn.close()


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


def add_price_entry(product_name, store_name, product_url, price, target_price=None):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO price_entries (product_name, store_name, product_url, price, target_price)
        VALUES (?, ?, ?, ?, ?)
        """,
        (product_name, store_name, product_url, price, target_price),
    )
    conn.commit()
    conn.close()


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

    for row in products:
        target = row["target_price"]
        lowest = row["lowest_price"]
        if target is not None and lowest <= target:
            total_alerts += 1
        if row["savings"] and row["savings"] > 0:
            savings_values.append(row["savings"])

    avg_savings = sum(savings_values) / len(savings_values) if savings_values else 0.0

    return {
        "total_products": total_products,
        "total_alerts": total_alerts,
        "average_savings": avg_savings,
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


def delete_product(product_name):
    from images import delete_image_file

    filename = delete_product_image(product_name)
    if filename:
        delete_image_file(filename)

    remove_from_watchlist(product_name)

    conn = get_db()
    conn.execute("DELETE FROM price_entries WHERE product_name = ?", (product_name,))
    conn.commit()
    conn.close()


def rename_product(old_name, new_name):
    rename_product_image(old_name, new_name)
    rename_watchlist_product(old_name, new_name)
    conn = get_db()
    conn.execute(
        "UPDATE price_entries SET product_name = ? WHERE product_name = ?",
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
    conn = get_db()
    conn.execute(
        """
        UPDATE price_entries
        SET store_name = ?, product_url = ?, price = ?, target_price = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (store_name, product_url, price, target_price, entry_id),
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
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO watchlist (product_name) VALUES (?)",
        (product_name,),
    )
    conn.commit()
    conn.close()


def remove_from_watchlist(product_name):
    conn = get_db()
    conn.execute("DELETE FROM watchlist WHERE product_name = ?", (product_name,))
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
            w.product_name,
            w.added_at,
            l.lowest_price,
            l.store_name,
            l.product_url,
            t.target_price
        FROM watchlist w
        JOIN lowest l ON w.product_name = l.product_name AND l.rn = 1
        LEFT JOIN targets t ON w.product_name = t.product_name
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
