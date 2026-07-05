import re

# Expected retail price bands by product family (single-unit, US retail).
FAMILY_PRICE_RANGES = {
    "macbook": (899, 2499),
    "apple_watch": (179, 499),
    "samsung_watch": (179, 499),
    "iphone": (599, 1299),
    "samsung_phone": (599, 1299),
    "phone": (599, 1299),
    "earbuds": (79, 249),
    "airpods": (79, 249),
    "galaxy_buds": (79, 249),
    "headphones": (99, 399),
    "laptop": (499, 1999),
    "personal_care": (2.99, 24.99),
    "household": (3.99, 49.99),
    "general": (9.99, 199.99),
}

BULK_KEYWORDS = (
    "pack of",
    "count",
    "-pack",
    " pack",
    "bulk",
    "gallon",
    "case of",
    "multi",
)

PERSONAL_CARE_KEYWORDS = (
    "sanitizer",
    "hand sanitizer",
    "soap",
    "lotion",
    "shampoo",
    "conditioner",
    "toothpaste",
    "deodorant",
    "tissue",
    "wipes",
)

TRUST_DIRECT_RETAILERS = {"walmart", "target", "bestbuy", "apple", "samsung", "costco"}


def _detect_family(product_name):
    name = (product_name or "").lower()

    if any(keyword in name for keyword in PERSONAL_CARE_KEYWORDS):
        return "personal_care"
    if any(keyword in name for keyword in ("detergent", "cleaner", "paper towel", "trash bag")):
        return "household"
    if "macbook" in name:
        return "macbook"
    if "galaxy watch" in name or ("samsung" in name and "watch" in name):
        return "samsung_watch"
    if "apple watch" in name:
        return "apple_watch"
    if "iphone" in name:
        return "iphone"
    if ("samsung" in name or "galaxy" in name) and "watch" not in name and "buds" not in name:
        return "samsung_phone"
    if "airpods" in name:
        return "airpods"
    if "galaxy buds" in name:
        return "galaxy_buds"
    if any(token in name for token in ("earbuds", "earbud", "buds")):
        return "earbuds"
    if any(token in name for token in ("headphones", "headphone", "wh-1000", "quietcomfort", "beats")):
        return "headphones"
    if any(token in name for token in ("laptop", "thinkpad", "xps", "spectre", "surface")):
        return "laptop"
    if any(token in name for token in ("phone", "pixel", "oneplus")):
        return "phone"
    return "general"


def _is_bulk_listing(product_name, listing_title=""):
    text = f"{product_name} {listing_title}".lower()
    if re.search(r"\b(\d+)\s*(ct|count|pk|pack)\b", text):
        return True
    return any(keyword in text for keyword in BULK_KEYWORDS)


def get_price_range(product_name, listing_title=""):
    family = _detect_family(product_name)
    low, high = FAMILY_PRICE_RANGES.get(family, FAMILY_PRICE_RANGES["general"])

    if _is_bulk_listing(product_name, listing_title):
        low = low * 2
        high = high * 8

    return family, low, high


def validate_price(product_name, total_price, listing_title=""):
    """Return validation metadata for a delivered price."""
    family, low, high = get_price_range(product_name, listing_title)
    price = float(total_price)

    if price > high * 1.35:
        return {
            "is_abnormal": True,
            "reason_key": "validation.abnormal_high",
            "family": family,
            "expected_min": low,
            "expected_max": high,
        }
    if price < low * 0.45:
        return {
            "is_abnormal": True,
            "reason_key": "validation.abnormal_low",
            "family": family,
            "expected_min": low,
            "expected_max": high,
        }

    return {
        "is_abnormal": False,
        "reason_key": None,
        "family": family,
        "expected_min": low,
        "expected_max": high,
    }


def assign_seller_profile(retailer_id, seed_hex):
    roll = int(seed_hex[8:10], 16) % 100

    if retailer_id == "ebay":
        return {
            "seller_type": "marketplace",
            "trust_stars": 2,
            "trust_label_key": "trust.marketplace_seller",
        }

    if retailer_id == "amazon":
        if roll < 35:
            return {
                "seller_type": "marketplace",
                "trust_stars": 3,
                "trust_label_key": "trust.amazon_third_party",
            }
        return {
            "seller_type": "direct",
            "trust_stars": 4,
            "trust_label_key": "trust.amazon_retail",
        }

    if retailer_id == "walmart":
        if roll < 18:
            return {
                "seller_type": "marketplace",
                "trust_stars": 2,
                "trust_label_key": "trust.walmart_marketplace",
            }
        return {
            "seller_type": "direct",
            "trust_stars": 5,
            "trust_label_key": "trust.walmart_direct",
        }

    if retailer_id == "target":
        return {
            "seller_type": "direct",
            "trust_stars": 5,
            "trust_label_key": "trust.target_direct",
        }

    if retailer_id == "bestbuy":
        return {
            "seller_type": "direct",
            "trust_stars": 5,
            "trust_label_key": "trust.bestbuy_direct",
        }

    if retailer_id == "costco":
        return {
            "seller_type": "direct",
            "trust_stars": 5,
            "trust_label_key": "trust.costco_direct",
        }

    if retailer_id == "homedepot":
        return {
            "seller_type": "direct",
            "trust_stars": 5,
            "trust_label_key": "trust.homedepot_direct",
        }

    if retailer_id == "lowes":
        return {
            "seller_type": "direct",
            "trust_stars": 5,
            "trust_label_key": "trust.lowes_direct",
        }

    if retailer_id == "apple":
        return {
            "seller_type": "direct",
            "trust_stars": 5,
            "trust_label_key": "trust.apple_direct",
        }

    if retailer_id == "samsung":
        return {
            "seller_type": "direct",
            "trust_stars": 5,
            "trust_label_key": "trust.samsung_direct",
        }

    return {
        "seller_type": "marketplace",
        "trust_stars": 3,
        "trust_label_key": "trust.marketplace_seller",
    }


def marketplace_price_multiplier(seller_type, seed_hex):
    """Simulate inflated third-party / wrong-SKU listings."""
    if seller_type != "marketplace":
        return 1.0
    roll = int(seed_hex[10:12], 16) % 100
    if roll < 25:
        return 3.5 + (roll / 100) * 2.0
    if roll < 55:
        return 1.8 + (roll / 100) * 0.8
    return 1.0


def apply_trust_and_validation(listing, product_name):
    validation = validate_price(
        product_name,
        listing["total_delivered"],
        listing.get("product_title", ""),
    )
    listing["price_validation"] = validation
    listing["price_abnormal"] = validation["is_abnormal"]

    if validation["is_abnormal"]:
        listing["trust_stars"] = 1
        listing["trust_label_key"] = "trust.price_abnormal"
    else:
        listing["trust_stars"] = listing.get("trust_stars", 3)
        if listing.get("seller_type") == "marketplace" and listing["trust_stars"] > 3:
            listing["trust_stars"] = 3

    return listing


def delivery_label_key(delivery_key, shipping_free=False, pickup_available=False):
    normalized = (delivery_key or "").strip().lower().replace("-", "_")

    if pickup_available:
        if normalized in ("pickup_today",):
            return "search.delivery_pickup_today"
        if normalized in ("pickup_tomorrow",):
            return "search.delivery_pickup_tomorrow"
        return "search.delivery_pickup_today"

    if shipping_free or normalized in ("free_shipping",):
        return "search.delivery_free_shipping"

    mapping = {
        "delivery_fast": "search.delivery_two_day",
        "two_day": "search.delivery_two_day",
        "delivery_tomorrow": "search.delivery_tomorrow",
        "delivery_standard": "search.delivery_standard_label",
        "delivery_slow": "search.delivery_standard_label",
        "same_day": "search.delivery_same_day",
        "pickup_today": "search.delivery_pickup_today",
        "pickup_tomorrow": "search.delivery_pickup_tomorrow",
        "free_shipping": "search.delivery_free_shipping",
    }
    return mapping.get(normalized, "search.delivery_standard_label")


def enrich_listing_display(listing):
    shipping_free = listing.get("shipping_free")
    pickup_available = listing.get("pickup_available")

    if shipping_free:
        listing["shipping_display_key"] = "search.delivery_free_shipping"
    else:
        listing["shipping_display_key"] = listing.get("shipping_label_key", "search.shipping_paid")

    if pickup_available:
        listing["pickup_display_key"] = delivery_label_key(
            listing.get("delivery_key"),
            pickup_available=True,
        )
    else:
        listing["pickup_display_key"] = None

    listing["delivery_display_key"] = delivery_label_key(
        listing.get("delivery_key"),
        shipping_free=False,
        pickup_available=False,
    )
    return listing


def mark_statistical_outliers(listings):
    """Flag prices far above the peer median (wrong SKU / marketplace glitch)."""
    valid = [item for item in listings if not item.get("price_abnormal")]
    if len(valid) < 2:
        return listings

    prices = sorted(item["total_delivered"] for item in valid)
    median = prices[len(prices) // 2]
    if median <= 0:
        return listings

    threshold = max(median * 2.2, median + 35)

    for item in listings:
        if item.get("price_abnormal"):
            continue
        if item["total_delivered"] > threshold:
            item["price_abnormal"] = True
            item["trust_stars"] = 1
            item["trust_label_key"] = "trust.price_abnormal"
            item["listing_note_key"] = "search.listing_outlier_note"

    return listings


def mark_expensive_listings(listings, threshold_ratio=1.20):
    """Visually de-emphasize listings priced well above the best deal."""
    eligible = [item for item in listings if not item.get("price_abnormal")]
    if not eligible:
        for item in listings:
            item["is_expensive"] = False
        return listings

    best_price = min(item["total_delivered"] for item in eligible)
    limit = best_price * threshold_ratio

    for item in listings:
        if item.get("is_best_deal") or item.get("price_abnormal"):
            item["is_expensive"] = False
        else:
            item["is_expensive"] = item["total_delivered"] > limit

    return listings


def select_best_deal(listings):
    for item in listings:
        item["is_best_deal"] = False

    normal = [item for item in listings if not item.get("price_abnormal")]
    direct = [item for item in normal if item.get("seller_type") == "direct"]
    pool = direct if direct else normal
    if not pool:
        pool = listings

    pool.sort(
        key=lambda item: (
            item["total_delivered"],
            -item.get("trust_stars", 0),
            item.get("seller_type") != "direct",
        )
    )

    if pool and not pool[0].get("price_abnormal"):
        pool[0]["is_best_deal"] = True

    return listings
