"""Seed demo products for screenshots and local testing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import (
    init_db,
    add_price_entry,
    add_to_watchlist,
    create_image_upload,
    confirm_image_upload,
    get_product_image,
)
from images import save_placeholder_image

# Prices only — add a real product_url per row via Edit or Add when you have the exact listing URL.
DEMO_PRODUCTS = [
    ("Wireless Mouse", "Amazon", "", 24.99, 20.00),
    ("Wireless Mouse", "Walmart", "", 19.99, 20.00),
    ("Wireless Mouse", "Target", "", 22.50, 20.00),
    ("Bluetooth Headphones", "Best Buy", "", 79.99, 65.00),
    ("Bluetooth Headphones", "Amazon", "", 69.99, 65.00),
    ("USB-C Hub", "Amazon", "", 34.99, None),
    ("USB-C Hub", "Best Buy", "", 29.99, None),
]


def seed_product_image(product_name):
    if get_product_image(product_name):
        return
    upload_id, filename = save_placeholder_image(product_name)
    create_image_upload(upload_id, filename, f"{product_name}.svg")
    confirm_image_upload(upload_id, product_name, ai_detected_name=product_name)


def seed():
    init_db()
    for product_name, store, url, price, target in DEMO_PRODUCTS:
        add_price_entry(product_name, store, url, price, target)
    for product_name in {name for name, *_ in DEMO_PRODUCTS}:
        seed_product_image(product_name)
    add_to_watchlist("Wireless Mouse")
    add_to_watchlist("Bluetooth Headphones")
    print("Demo data seeded.")


if __name__ == "__main__":
    seed()
