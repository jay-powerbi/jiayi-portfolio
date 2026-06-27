"""Seed demo products for screenshots and local testing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import init_db, add_price_entry, add_to_watchlist

DEMO_PRODUCTS = [
    ("Wireless Mouse", "Amazon", "https://amazon.com/example/mouse", 24.99, 20.00),
    ("Wireless Mouse", "Walmart", "https://walmart.com/example/mouse", 19.99, 20.00),
    ("Wireless Mouse", "Target", "https://target.com/example/mouse", 22.50, 20.00),
    ("Bluetooth Headphones", "Best Buy", "https://bestbuy.com/example/headphones", 79.99, 65.00),
    ("Bluetooth Headphones", "Amazon", "https://amazon.com/example/headphones", 69.99, 65.00),
    ("USB-C Hub", "Amazon", "https://amazon.com/example/hub", 34.99, None),
    ("USB-C Hub", "Newegg", "https://newegg.com/example/hub", 29.99, None),
]


def seed():
    init_db()
    for product_name, store, url, price, target in DEMO_PRODUCTS:
        add_price_entry(product_name, store, url, price, target)
    add_to_watchlist("Wireless Mouse")
    add_to_watchlist("Bluetooth Headphones")
    print("Demo data seeded.")


if __name__ == "__main__":
    seed()
