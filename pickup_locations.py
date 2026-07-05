import hashlib
import re
from urllib.parse import quote_plus

# Retailers that offer in-store / curbside pickup in this demo.
PICKUP_RETAILERS = {
    "walmart": "Walmart",
    "target": "Target",
    "bestbuy": "Best Buy",
    "apple": "Apple Store",
    "costco": "Costco",
    "samsung": "Samsung Experience Store",
}

RETAILER_STORE_PREFIX = {
    "walmart": "Walmart Supercenter",
    "target": "Target",
    "bestbuy": "Best Buy",
    "apple": "Apple Store",
    "costco": "Costco Wholesale",
    "samsung": "Samsung Experience Store",
}

# Demo street/area names — combined with ZIP for plausible addresses.
STREET_NAMES = [
    "Main St",
    "Market St",
    "Broadway",
    "Oak Ave",
    "Cedar Ln",
    "Park Blvd",
    "Commerce Dr",
    "Union Sq",
]

CITY_NAMES = [
    "Springfield",
    "Fairview",
    "Riverside",
    "Greenville",
    "Madison",
    "Georgetown",
    "Arlington",
    "Milltown",
]

STATE_CODES = [
    "CA",
    "TX",
    "NY",
    "FL",
    "IL",
    "PA",
    "OH",
    "GA",
    "NC",
    "WA",
]


def normalize_zip(zip_code):
    digits = re.sub(r"\D", "", zip_code or "")
    return digits[:5] if len(digits) >= 5 else ""


def supports_pickup(retailer_id):
    return retailer_id in PICKUP_RETAILERS


def pickup_retailer_name(retailer_id):
    return PICKUP_RETAILERS.get(retailer_id, "")


def _seed(*parts):
    payload = "|".join(str(p).lower() for p in parts)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _pickup_availability(seed, index):
    roll = int(seed[index : index + 2], 16) % 10
    return "pickup_today" if roll < 6 else "pickup_tomorrow"


def mock_pickup_locations(retailer_id, zip_code, product_name="", pickup_key=None):
    zip_code = normalize_zip(zip_code)
    if not zip_code or retailer_id not in PICKUP_RETAILERS:
        return []

    base_seed = _seed(retailer_id, zip_code, product_name)
    location_count = 2 + int(base_seed[0], 16) % 3
    locations = []

    for index in range(location_count):
        seed = _seed(base_seed, index)
        street_num = 100 + int(seed[2:5], 16) % 8900
        street = STREET_NAMES[int(seed[5:7], 16) % len(STREET_NAMES)]
        city = CITY_NAMES[int(seed[7:9], 16) % len(CITY_NAMES)]
        state = STATE_CODES[int(seed[9:11], 16) % len(STATE_CODES)]
        address = f"{street_num} {street}, {city}, {state} {zip_code}"
        distance = round(0.8 + (int(seed[11:14], 16) % 120) / 10, 1)
        availability = pickup_key or _pickup_availability(seed, 14)
        hours_roll = int(seed[15:17], 16) % 3
        if hours_roll == 0:
            hours = "Mon–Sat 8AM–10PM, Sun 8AM–8PM"
        elif hours_roll == 1:
            hours = "Mon–Fri 10AM–9PM, Sat–Sun 9AM–9PM"
        else:
            hours = "Daily 9AM–9PM"

        store_label = RETAILER_STORE_PREFIX.get(retailer_id, PICKUP_RETAILERS[retailer_id])
        suffix = f" #{1 + int(seed[1:3], 16) % 400}"
        maps_query = quote_plus(address)

        locations.append(
            {
                "store_name": f"{store_label}{suffix}",
                "address": address,
                "distance_miles": distance,
                "pickup_key": availability,
                "hours": hours,
                "maps_url": f"https://maps.google.com/?q={maps_query}",
            }
        )

    locations.sort(key=lambda item: item["distance_miles"])
    return locations
