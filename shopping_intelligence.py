from datetime import date

# Annual US shopping events (demo dates for the current cycle).
SHOPPING_EVENTS = [
    {
        "id": "independence_day",
        "name_key": "events.independence_day",
        "event_date": (7, 4),
        "categories_keys": [
            "events.cat.outdoor",
            "events.cat.appliances",
            "events.cat.electronics",
        ],
        "recommendation_key": "events.rec.independence_day",
        "match_keywords": ("grill", "outdoor", "tv", "appliance", "furniture"),
    },
    {
        "id": "prime_day",
        "name_key": "events.prime_day",
        "event_date": (7, 15),
        "categories_keys": [
            "events.cat.electronics",
            "events.cat.headphones",
            "events.cat.ssd",
        ],
        "recommendation_key": "events.rec.prime_day",
        "match_keywords": (
            "iphone",
            "macbook",
            "headphone",
            "airpod",
            "watch",
            "ssd",
            "electronics",
            "tablet",
            "laptop",
        ),
    },
    {
        "id": "back_to_school",
        "name_key": "events.back_to_school",
        "event_date": (8, 10),
        "categories_keys": [
            "events.cat.laptops",
            "events.cat.tablets",
            "events.cat.accessories",
        ],
        "recommendation_key": "events.rec.back_to_school",
        "match_keywords": ("laptop", "macbook", "ipad", "tablet", "backpack", "monitor"),
    },
    {
        "id": "labor_day",
        "name_key": "events.labor_day",
        "event_date": (9, 7),
        "categories_keys": [
            "events.cat.appliances",
            "events.cat.mattresses",
            "events.cat.outdoor",
        ],
        "recommendation_key": "events.rec.labor_day",
        "match_keywords": ("mattress", "appliance", "grill", "outdoor", "furniture"),
    },
    {
        "id": "black_friday",
        "name_key": "events.black_friday",
        "event_date": (11, 27),
        "categories_keys": [
            "events.cat.electronics",
            "events.cat.tvs",
            "events.cat.wearables",
        ],
        "recommendation_key": "events.rec.black_friday",
        "match_keywords": (
            "iphone",
            "watch",
            "tv",
            "headphone",
            "laptop",
            "tablet",
            "game",
        ),
    },
    {
        "id": "cyber_monday",
        "name_key": "events.cyber_monday",
        "event_date": (11, 30),
        "categories_keys": [
            "events.cat.electronics",
            "events.cat.software",
            "events.cat.accessories",
        ],
        "recommendation_key": "events.rec.cyber_monday",
        "match_keywords": (
            "laptop",
            "monitor",
            "headphone",
            "keyboard",
            "software",
            "ssd",
        ),
    },
]


def _event_date_for_year(month, day, reference=None):
    reference = reference or date.today()
    candidate = date(reference.year, month, day)
    if candidate < reference:
        candidate = date(reference.year + 1, month, day)
    return candidate


def _days_remaining(event_date, reference=None):
    reference = reference or date.today()
    return max(0, (event_date - reference).days)


def _product_matches_keywords(product_name, keywords):
    name = (product_name or "").lower()
    return any(keyword in name for keyword in keywords)


def get_upcoming_shopping_events(limit=4, reference=None):
    reference = reference or date.today()
    events = []

    for event in SHOPPING_EVENTS:
        month, day = event["event_date"]
        event_date = _event_date_for_year(month, day, reference)
        days_left = _days_remaining(event_date, reference)
        events.append(
            {
                "id": event["id"],
                "name_key": event["name_key"],
                "event_date": event_date,
                "days_remaining": days_left,
                "categories_keys": event["categories_keys"],
                "recommendation_key": event["recommendation_key"],
                "match_keywords": event["match_keywords"],
            }
        )

    events.sort(key=lambda item: item["event_date"])
    return events[:limit]


def _personalized_event_recommendation(event, products):
    matched = [
        p["product_name"]
        for p in products
        if _product_matches_keywords(p["product_name"], event["match_keywords"])
    ]
    if matched:
        return {
            "key": "events.rec.personalized",
            "params": {
                "event_key": event["name_key"],
                "product": matched[0],
                "count": len(matched),
            },
        }
    return {"key": event["recommendation_key"], "params": {}}


def enrich_events_with_recommendations(events, products):
    enriched = []
    for event in events:
        item = dict(event)
        item["recommendation"] = _personalized_event_recommendation(event, products)
        item["watchlist_matches"] = [
            p["product_name"]
            for p in products
            if p.get("on_watchlist")
            and _product_matches_keywords(p["product_name"], event["match_keywords"])
        ]
        enriched.append(item)
    return enriched


def get_best_deals(products, limit=3):
    from price_validation import validate_price

    deals = []
    for product in products:
        if (product.get("savings") or 0) <= 0:
            continue
        validation = validate_price(product["product_name"], product["lowest_price"])
        if validation["is_abnormal"]:
            continue
        deals.append(product)

    deals.sort(key=lambda p: p["savings"], reverse=True)
    return deals[:limit]


def get_price_trend(products, summary):
    if not products:
        return {
            "has_data": False,
            "sparkline": [],
            "headline_key": "intel.trend.empty_headline",
            "body_key": "intel.trend.empty_body",
            "params": {},
            "direction": "neutral",
        }

    prices = [p["lowest_price"] for p in products]
    savings = [p.get("savings") or 0 for p in products]
    avg_price = sum(prices) / len(prices)
    total_savings = sum(savings)
    alert_count = sum(1 for p in products if p.get("status") == "alert")

    sparkline = []
    chunk_size = max(1, len(prices) // 7)
    for index in range(0, min(len(prices), 7)):
        start = index * chunk_size
        chunk = prices[start : start + chunk_size] or prices[-1:]
        sparkline.append(round(sum(chunk) / len(chunk), 2))

    direction = "down" if total_savings > 0 else "neutral"
    if alert_count:
        direction = "down"

    return {
        "has_data": True,
        "sparkline": sparkline,
        "headline_key": "intel.trend.headline",
        "body_key": "intel.trend.body",
        "params": {
            "avg_price": f"{avg_price:.2f}",
            "total_savings": f"{total_savings:.2f}",
            "product_count": len(products),
            "alert_count": alert_count,
        },
        "direction": direction,
    }


def get_ai_recommendation(products, events):
    if not products:
        next_event = events[0] if events else None
        if next_event:
            return {
                "headline_key": "intel.ai.empty_headline",
                "body_key": "intel.ai.empty_body_event",
                "params": {
                    "event_key": next_event["name_key"],
                    "days": next_event["days_remaining"],
                },
            }
        return {
            "headline_key": "intel.ai.empty_headline",
            "body_key": "intel.ai.empty_body",
            "params": {},
        }

    alerts = [p for p in products if p.get("status") == "alert"]
    if alerts:
        product = alerts[0]
        return {
            "headline_key": "intel.ai.alert_headline",
            "body_key": "intel.ai.alert_body",
            "params": {
                "product": product["product_name"],
                "price": f"{product['lowest_price']:.2f}",
                "store": product["store_name"],
            },
        }

    upcoming = events[0] if events else None
    electronics_matches = []
    if upcoming:
        electronics_matches = [
            p["product_name"]
            for p in products
            if _product_matches_keywords(p["product_name"], upcoming["match_keywords"])
        ]

    if upcoming and electronics_matches and upcoming["days_remaining"] <= 45:
        return {
            "headline_key": "intel.ai.wait_headline",
            "body_key": "intel.ai.wait_body",
            "params": {
                "event_key": upcoming["name_key"],
                "days": upcoming["days_remaining"],
                "product": electronics_matches[0],
            },
        }

    best = get_best_deals(products, limit=1)
    if best:
        deal = best[0]
        return {
            "headline_key": "intel.ai.deal_headline",
            "body_key": "intel.ai.deal_body",
            "params": {
                "product": deal["product_name"],
                "savings": f"{deal['savings']:.2f}",
                "store": deal["store_name"],
            },
        }

    return {
        "headline_key": "intel.ai.track_headline",
        "body_key": "intel.ai.track_body",
        "params": {"count": len(products)},
    }


def build_dashboard_intelligence(products, summary):
    events = get_upcoming_shopping_events(limit=4)
    events = enrich_events_with_recommendations(events, products)
    return {
        "price_trend": get_price_trend(products, summary),
        "best_deals": get_best_deals(products, limit=3),
        "ai_recommendation": get_ai_recommendation(products, events),
        "shopping_events": events,
    }
