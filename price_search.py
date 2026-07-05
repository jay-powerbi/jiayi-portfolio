import hashlib
import re

from pickup_locations import supports_pickup
from product_urls import is_usable_product_url, normalize_product_url, stored_product_url
from price_validation import (
    apply_trust_and_validation,
    assign_seller_profile,
    delivery_label_key,
    enrich_listing_display,
    mark_statistical_outliers,
    mark_expensive_listings,
    marketplace_price_multiplier,
    select_best_deal,
)

ALL_RETAILERS = {
    "amazon": {"id": "amazon", "name": "Amazon"},
    "walmart": {"id": "walmart", "name": "Walmart"},
    "costco": {"id": "costco", "name": "Costco"},
    "bestbuy": {"id": "bestbuy", "name": "Best Buy"},
    "target": {"id": "target", "name": "Target"},
    "homedepot": {"id": "homedepot", "name": "Home Depot"},
    "lowes": {"id": "lowes", "name": "Lowe's"},
    "ebay": {"id": "ebay", "name": "eBay"},
    "samsung": {"id": "samsung", "name": "Samsung"},
    "apple": {"id": "apple", "name": "Apple"},
}

RETAILER_META = {
    "amazon": {"logo_text": "a", "logo_class": "retailer-logo--amazon"},
    "walmart": {"logo_text": "W", "logo_class": "retailer-logo--walmart"},
    "costco": {"logo_text": "C", "logo_class": "retailer-logo--costco"},
    "bestbuy": {"logo_text": "BB", "logo_class": "retailer-logo--bestbuy"},
    "target": {"logo_text": "◎", "logo_class": "retailer-logo--target"},
    "homedepot": {"logo_text": "HD", "logo_class": "retailer-logo--homedepot"},
    "lowes": {"logo_text": "L", "logo_class": "retailer-logo--lowes"},
    "ebay": {"logo_text": "e", "logo_class": "retailer-logo--ebay"},
    "samsung": {"logo_text": "S", "logo_class": "retailer-logo--samsung"},
    "apple": {"logo_text": "", "logo_class": "retailer-logo--apple"},
}

DELIVERY_OPTIONS = [
    {"key": "same_day", "days": 0},
    {"key": "delivery_tomorrow", "days": 1},
    {"key": "delivery_fast", "days": 2},
    {"key": "delivery_standard", "days": 5},
    {"key": "delivery_slow", "days": 8},
]

PICKUP_OPTIONS = [
    {"key": "pickup_today", "days": 0},
    {"key": "pickup_tomorrow", "days": 1},
]

SEARCH_URLS = {
    "amazon": "https://www.amazon.com/s?k={query}",
    "walmart": "https://www.walmart.com/search?q={query}",
    "costco": "https://www.costco.com/CatalogSearch?dept=All&keyword={query}",
    "bestbuy": "https://www.bestbuy.com/site/searchpage.jsp?st={query}",
    "target": "https://www.target.com/s?searchTerm={query}",
    "homedepot": "https://www.homedepot.com/s/{query}",
    "lowes": "https://www.lowes.com/search?searchTerm={query}",
    "ebay": "https://www.ebay.com/sch/i.html?_nkw={query}",
    "samsung": "https://www.samsung.com/us/search/?searchterm={query}",
    "apple": "https://www.apple.com/us/search/{query}?src=globalnav",
}

# Realistic demo price bands and retailer sets by product family.
FAMILY_CONFIG = {
    "macbook": {
        "price_min": 899,
        "price_max": 2499,
        "retailers": ["apple", "bestbuy", "amazon", "walmart", "target"],
    },
    "apple_watch": {
        "price_min": 179,
        "price_max": 499,
        "retailers": ["apple", "bestbuy", "amazon", "walmart", "target"],
    },
    "samsung_watch": {
        "price_min": 179,
        "price_max": 499,
        "retailers": ["samsung", "bestbuy", "amazon", "walmart", "target", "ebay"],
    },
    "iphone": {
        "price_min": 599,
        "price_max": 1299,
        "retailers": ["apple", "bestbuy", "amazon", "walmart", "target"],
    },
    "samsung_phone": {
        "price_min": 599,
        "price_max": 1299,
        "retailers": ["samsung", "bestbuy", "amazon", "walmart", "target", "ebay"],
    },
    "phone": {
        "price_min": 599,
        "price_max": 1299,
        "retailers": ["bestbuy", "amazon", "walmart", "target", "ebay"],
    },
    "earbuds": {
        "price_min": 79,
        "price_max": 249,
        "retailers": ["amazon", "walmart", "bestbuy", "target", "ebay"],
    },
    "airpods": {
        "price_min": 79,
        "price_max": 249,
        "retailers": ["apple", "bestbuy", "amazon", "walmart", "target"],
    },
    "galaxy_buds": {
        "price_min": 79,
        "price_max": 249,
        "retailers": ["samsung", "bestbuy", "amazon", "walmart", "target", "ebay"],
    },
    "headphones": {
        "price_min": 99,
        "price_max": 399,
        "retailers": ["amazon", "walmart", "bestbuy", "target", "ebay"],
    },
    "laptop": {
        "price_min": 499,
        "price_max": 1999,
        "retailers": ["bestbuy", "amazon", "walmart", "target", "ebay"],
    },
    "general": {
        "price_min": 9.99,
        "price_max": 199.99,
        "retailers": ["amazon", "walmart", "costco", "bestbuy", "target", "homedepot", "lowes", "ebay"],
    },
    "personal_care": {
        "price_min": 2.99,
        "price_max": 24.99,
        "retailers": ["amazon", "walmart", "costco", "target", "ebay"],
    },
    "household": {
        "price_min": 3.99,
        "price_max": 49.99,
        "retailers": ["amazon", "walmart", "costco", "target", "homedepot", "lowes", "ebay"],
    },
}


def _normalize_zip(zip_code):
    digits = re.sub(r"\D", "", zip_code or "")
    return digits[:5] if len(digits) >= 5 else ""


def _product_seed(product_name, retailer_id, zip_code=""):
    payload = f"{product_name.strip().lower()}|{retailer_id}|{_normalize_zip(zip_code)}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def detect_product_family(product_name):
    name = (product_name or "").lower()

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

    if any(
        token in name
        for token in ("headphones", "headphone", "wh-1000", "quietcomfort", "beats")
    ):
        return "headphones"

    if any(token in name for token in ("laptop", "thinkpad", "xps", "spectre", "surface")):
        return "laptop"

    if any(token in name for token in ("phone", "pixel", "oneplus")):
        return "phone"

    if any(
        keyword in name
        for keyword in (
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
    ):
        return "personal_care"

    if any(keyword in name for keyword in ("detergent", "cleaner", "paper towel", "trash bag")):
        return "household"

    return "general"


def retailers_for_product(product_name):
    family = detect_product_family(product_name)
    config = FAMILY_CONFIG[family]
    return [ALL_RETAILERS[retailer_id] for retailer_id in config["retailers"]]


def _money(amount):
    return round(float(amount), 2)


def _clamp(amount, low, high):
    return _money(max(low, min(high, amount)))


def _condition_multiplier(name):
    if "refurbished" in name:
        return 0.85
    if "used" in name:
        return 0.72
    return 1.0


def _config_premium_ratio(name, family):
    """Map product configuration keywords to a 0.0–1.0 position inside the price band."""
    ratio = 0.45

    if family == "macbook":
        if "m4" in name:
            ratio += 0.35
        elif "m3" in name:
            ratio += 0.28
        elif "m2" in name:
            ratio += 0.18
        elif "m1" in name:
            ratio += 0.08
        if "macbook pro" in name:
            ratio += 0.12
        if "16-inch" in name:
            ratio += 0.18
        elif "15-inch" in name:
            ratio += 0.12
        elif "14-inch" in name:
            ratio += 0.08
        if "1tb" in name:
            ratio += 0.12
        elif "512gb" in name:
            ratio += 0.07
        if "32gb" in name:
            ratio += 0.1
        elif "24gb" in name:
            ratio += 0.07
        elif "16gb" in name:
            ratio += 0.04

    elif family in ("apple_watch", "samsung_watch"):
        if "ultra 2" in name or "watch ultra" in name:
            ratio += 0.35
        elif "ultra" in name:
            ratio += 0.28
        elif any(token in name for token in ("series 10", "watch 7", "watch 6")):
            ratio += 0.18
        elif any(token in name for token in ("series 9", "watch 5")):
            ratio += 0.1
        if any(token in name for token in ("49mm", "47mm", "45mm", "44mm")):
            ratio += 0.05
        if "cellular" in name or " lte" in name or name.endswith(" lte"):
            ratio += 0.08

    elif family in ("iphone", "samsung_phone", "phone"):
        if "iphone 16" in name or "galaxy s24" in name:
            ratio += 0.28
        elif "iphone 15" in name or "galaxy s23" in name:
            ratio += 0.2
        elif "iphone 14" in name:
            ratio += 0.12
        elif "iphone 13" in name:
            ratio += 0.05
        if "1tb" in name:
            ratio += 0.22
        elif "512gb" in name:
            ratio += 0.14
        elif "256gb" in name:
            ratio += 0.08

    elif family in ("airpods", "galaxy_buds", "earbuds"):
        if "pro" in name or "max" in name or "ultra" in name:
            ratio += 0.25
        elif "3" in name or "xm5" in name:
            ratio += 0.12

    elif family == "headphones":
        if any(token in name for token in ("xm5", "xm4", "quietcomfort ultra")):
            ratio += 0.28
        elif "pro" in name or "max" in name:
            ratio += 0.18

    elif family == "laptop":
        if any(token in name for token in ("m3", "m4", "i7", "i9")):
            ratio += 0.2
        if "32gb" in name:
            ratio += 0.12
        elif "16gb" in name:
            ratio += 0.06
        if "1tb" in name:
            ratio += 0.1
        elif "512gb" in name:
            ratio += 0.05

    return min(1.0, max(0.0, ratio))


def _retailer_offset(retailer_id, seed):
    roll = int(seed[3:5], 16) % 100
    if retailer_id == "ebay":
        return -0.08 + (roll / 100) * 0.1
    if retailer_id in ("walmart", "target", "costco"):
        return -0.04 + (roll / 100) * 0.07
    if retailer_id in ("amazon", "bestbuy", "homedepot", "lowes"):
        return -0.02 + (roll / 100) * 0.06
    if retailer_id in ("apple", "samsung"):
        return 0.0 + (roll / 100) * 0.04
    return -0.03 + (roll / 100) * 0.08


def _estimate_item_price(product_name, family, retailer_id, seed):
    config = FAMILY_CONFIG[family]
    low, high = config["price_min"], config["price_max"]
    name = product_name.lower()

    ratio = _config_premium_ratio(name, family)
    jitter = (int(seed[:4], 16) % 100) / 100 * 0.08 - 0.04
    ratio = min(1.0, max(0.0, ratio + jitter))

    base = low + (high - low) * ratio
    base *= _condition_multiplier(name)
    base *= 1 + _retailer_offset(retailer_id, seed)

    return _clamp(base, low, high)


def _listing_title(product_name, retailer_name):
    return product_name


def _delivery_for_listing(retailer_id, seed):
    if supports_pickup(retailer_id):
        pickup_roll = int(seed[9:10], 16) % 10
        if pickup_roll < 5:
            pickup = PICKUP_OPTIONS[int(seed[10:11], 16) % len(PICKUP_OPTIONS)]
            return pickup, True
    delivery = DELIVERY_OPTIONS[int(seed[9:10], 16) % len(DELIVERY_OPTIONS)]
    return delivery, False


def mock_search_prices(product_name, zip_code=""):
    if not product_name or not product_name.strip():
        return []

    family = detect_product_family(product_name)
    listings = []

    for retailer in retailers_for_product(product_name):
        seed = _product_seed(product_name, retailer["id"], zip_code)
        seller = assign_seller_profile(retailer["id"], seed)

        from database import get_product_store_entry

        tracked = get_product_store_entry(product_name, retailer["name"])
        if tracked:
            base_price = _money(float(tracked["price"]))
            product_url = stored_product_url(tracked["product_url"])
            shipping = 0.0
            shipping_label_key = "search.shipping_free"
            shipping_free = True
        else:
            base_price = _estimate_item_price(product_name, family, retailer["id"], seed)
            base_price = _money(base_price * marketplace_price_multiplier(seller["seller_type"], seed))
            product_url = None
            shipping_roll = int(seed[5:7], 16) % 100
            if base_price >= 99 and shipping_roll < 50:
                shipping = 0.0
                shipping_label_key = "search.shipping_free"
            elif shipping_roll < 78:
                shipping = _money(4.99 + (int(seed[7:9], 16) % 500) / 100)
                shipping_label_key = "search.shipping_paid"
            else:
                shipping = _money(9.99 + (int(seed[7:9], 16) % 700) / 100)
                shipping_label_key = "search.shipping_paid"
            shipping_free = shipping == 0.0

        delivery, pickup_available = _delivery_for_listing(retailer["id"], seed)
        total = _money(base_price + shipping)
        delivery_days = delivery["days"]
        delivery_days_plus = delivery_days + 2 if delivery["key"] == "delivery_standard" else delivery_days

        meta = RETAILER_META.get(retailer["id"], {"logo_text": retailer["name"][:1], "logo_class": "retailer-logo--default"})
        listing = {
            "retailer_id": retailer["id"],
            "retailer_name": retailer["name"],
            "logo_text": meta["logo_text"],
            "logo_class": meta["logo_class"],
            "product_title": _listing_title(product_name, retailer["name"]),
            "price": base_price,
            "shipping": shipping,
            "shipping_label_key": shipping_label_key,
            "shipping_free": shipping_free,
            "delivery_key": delivery["key"],
            "delivery_label_key": delivery_label_key(
                delivery["key"],
                shipping_free=shipping_free and not pickup_available,
                pickup_available=pickup_available,
            ),
            "delivery_days": delivery_days,
            "delivery_days_plus": delivery_days_plus,
            "pickup_available": pickup_available,
            "total_delivered": total,
            "product_url": product_url,
            "product_link_available": product_url is not None,
            "seller_type": seller["seller_type"],
            "trust_stars": seller["trust_stars"],
            "trust_label_key": seller["trust_label_key"],
            "listing_note_key": (
                "search.listing_marketplace_note"
                if seller["seller_type"] == "marketplace"
                else None
            ),
        }
        listings.append(enrich_listing_display(apply_trust_and_validation(listing, product_name)))

    listings = mark_statistical_outliers(listings)
    listings = mark_expensive_listings(listings)
    listings.sort(
        key=lambda item: (
            item.get("price_abnormal", False),
            item.get("seller_type") != "direct",
            item["total_delivered"],
            -item.get("trust_stars", 0),
        )
    )
    return select_best_deal(listings)
