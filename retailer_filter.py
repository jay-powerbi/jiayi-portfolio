"""Retailer filter config for Phase 1.5 — client-side filtering only."""

# Ordered list shown in the Retailer Filter UI.
FILTER_RETAILER_IDS = (
    "amazon",
    "walmart",
    "costco",
    "bestbuy",
    "target",
    "homedepot",
    "lowes",
    "ebay",
)

# Maps store display names (from DB / listings) to filter retailer ids.
STORE_NAME_TO_ID = {
    "amazon": "amazon",
    "walmart": "walmart",
    "costco": "costco",
    "costco wholesale": "costco",
    "best buy": "bestbuy",
    "target": "target",
    "home depot": "homedepot",
    "the home depot": "homedepot",
    "lowe's": "lowes",
    "lowes": "lowes",
    "ebay": "ebay",
    "apple": "apple",
    "apple store": "apple",
    "samsung": "samsung",
    "samsung experience store": "samsung",
}


def store_name_to_retailer_id(store_name):
    key = (store_name or "").strip().lower()
    return STORE_NAME_TO_ID.get(key, "")


def get_store_branding(store_name):
    """Logo and display name for a store label from price entries."""
    from price_search import ALL_RETAILERS, RETAILER_META

    retailer_id = store_name_to_retailer_id(store_name)
    raw_name = (store_name or "").strip()
    if retailer_id and retailer_id in ALL_RETAILERS:
        display_name = ALL_RETAILERS[retailer_id]["name"]
        logo = RETAILER_META.get(retailer_id, {})
        return {
            "retailer_id": retailer_id,
            "store_name": display_name,
            "logo_text": logo.get("logo_text", display_name[:1]),
            "logo_class": logo.get("logo_class", "retailer-logo--default"),
        }
    return {
        "retailer_id": retailer_id or "",
        "store_name": raw_name or "—",
        "logo_text": raw_name[:1] if raw_name else "?",
        "logo_class": "retailer-logo--default",
    }


def get_filter_retailers(retailer_meta=None):
    """Return filter UI rows using names/logos from price_search when available."""
    from price_search import ALL_RETAILERS, RETAILER_META

    meta = retailer_meta or RETAILER_META
    rows = []
    for retailer_id in FILTER_RETAILER_IDS:
        retailer = ALL_RETAILERS.get(retailer_id)
        if not retailer:
            continue
        logo = meta.get(retailer_id, {})
        rows.append(
            {
                "id": retailer_id,
                "name": retailer["name"],
                "logo_text": logo.get("logo_text", retailer["name"][:1]),
                "logo_class": logo.get("logo_class", "retailer-logo--default"),
            }
        )
    return rows
