import re

VARIANT_PROFILES = {
    "iphone": {
        "label_key": "variants.profile_iphone",
        "groups": [
            {
                "id": "series",
                "label_key": "variants.series",
                "options": [
                    {"value": "iPhone 13", "label": "iPhone 13"},
                    {"value": "iPhone 14", "label": "iPhone 14"},
                    {"value": "iPhone 15", "label": "iPhone 15"},
                    {"value": "iPhone 16", "label": "iPhone 16"},
                ],
            },
            {
                "id": "storage",
                "label_key": "variants.storage",
                "options": [
                    {"value": "128GB", "label": "128GB"},
                    {"value": "256GB", "label": "256GB"},
                    {"value": "512GB", "label": "512GB"},
                    {"value": "1TB", "label": "1TB"},
                ],
            },
            {
                "id": "condition",
                "label_key": "variants.condition",
                "options": [
                    {"value": "new", "label_key": "variants.condition_new"},
                    {"value": "used", "label_key": "variants.condition_used"},
                    {"value": "refurbished", "label_key": "variants.condition_refurbished"},
                ],
            },
            {
                "id": "carrier",
                "label_key": "variants.carrier",
                "options": [
                    {"value": "unlocked", "label_key": "variants.carrier_unlocked"},
                    {"value": "verizon", "label_key": "variants.carrier_verizon"},
                    {"value": "att", "label_key": "variants.carrier_att"},
                    {"value": "tmobile", "label_key": "variants.carrier_tmobile"},
                ],
            },
        ],
    },
    "apple_watch": {
        "label_key": "variants.profile_apple_watch",
        "groups": [
            {
                "id": "series",
                "label_key": "variants.series",
                "options": [
                    {"value": "Series 8", "label": "Series 8"},
                    {"value": "Series 9", "label": "Series 9"},
                    {"value": "Series 10", "label": "Series 10"},
                    {"value": "Ultra", "label": "Ultra"},
                    {"value": "Ultra 2", "label": "Ultra 2"},
                ],
            },
            {
                "id": "size",
                "label_key": "variants.size",
                "options": [
                    {"value": "41mm", "label": "41mm"},
                    {"value": "45mm", "label": "45mm"},
                    {"value": "49mm", "label": "49mm"},
                ],
            },
            {
                "id": "connectivity",
                "label_key": "variants.connectivity",
                "options": [
                    {"value": "GPS", "label": "GPS"},
                    {"value": "GPS + Cellular", "label": "GPS + Cellular"},
                ],
            },
            {
                "id": "condition",
                "label_key": "variants.condition",
                "options": [
                    {"value": "new", "label_key": "variants.condition_new"},
                    {"value": "used", "label_key": "variants.condition_used"},
                    {"value": "refurbished", "label_key": "variants.condition_refurbished"},
                ],
            },
        ],
    },
    "samsung_galaxy_watch": {
        "label_key": "variants.profile_samsung_watch",
        "groups": [
            {
                "id": "series",
                "label_key": "variants.series",
                "options": [
                    {"value": "Galaxy Watch 5", "label": "Galaxy Watch 5"},
                    {"value": "Galaxy Watch 6", "label": "Galaxy Watch 6"},
                    {"value": "Galaxy Watch 7", "label": "Galaxy Watch 7"},
                    {"value": "Galaxy Watch Ultra", "label": "Galaxy Watch Ultra"},
                ],
            },
            {
                "id": "size",
                "label_key": "variants.size",
                "options": [
                    {"value": "40mm", "label": "40mm"},
                    {"value": "44mm", "label": "44mm"},
                    {"value": "47mm", "label": "47mm"},
                ],
            },
            {
                "id": "connectivity",
                "label_key": "variants.connectivity",
                "options": [
                    {"value": "Bluetooth", "label": "Bluetooth"},
                    {"value": "LTE", "label": "LTE"},
                ],
            },
            {
                "id": "condition",
                "label_key": "variants.condition",
                "options": [
                    {"value": "new", "label_key": "variants.condition_new"},
                    {"value": "used", "label_key": "variants.condition_used"},
                    {"value": "refurbished", "label_key": "variants.condition_refurbished"},
                ],
            },
        ],
    },
    "macbook": {
        "label_key": "variants.profile_macbook",
        "groups": [
            {
                "id": "model",
                "label_key": "variants.model",
                "options": [
                    {"value": "MacBook Air", "label": "MacBook Air"},
                    {"value": "MacBook Pro", "label": "MacBook Pro"},
                ],
            },
            {
                "id": "chip",
                "label_key": "variants.chip",
                "options": [
                    {"value": "M1", "label": "M1"},
                    {"value": "M2", "label": "M2"},
                    {"value": "M3", "label": "M3"},
                    {"value": "M4", "label": "M4"},
                ],
            },
            {
                "id": "screen",
                "label_key": "variants.screen_size",
                "options": [
                    {"value": '13-inch', "label": '13-inch'},
                    {"value": '14-inch', "label": '14-inch'},
                    {"value": '15-inch', "label": '15-inch'},
                    {"value": '16-inch', "label": '16-inch'},
                ],
            },
            {
                "id": "storage",
                "label_key": "variants.storage",
                "options": [
                    {"value": "256GB", "label": "256GB"},
                    {"value": "512GB", "label": "512GB"},
                    {"value": "1TB", "label": "1TB"},
                ],
            },
            {
                "id": "memory",
                "label_key": "variants.memory",
                "options": [
                    {"value": "8GB", "label": "8GB"},
                    {"value": "16GB", "label": "16GB"},
                    {"value": "24GB", "label": "24GB"},
                    {"value": "32GB", "label": "32GB"},
                ],
            },
        ],
    },
}

CARRIER_QUERY_LABELS = {
    "unlocked": "unlocked",
    "verizon": "Verizon",
    "att": "AT&T",
    "tmobile": "T-Mobile",
}

CONDITION_QUERY_LABELS = {
    "new": "new",
    "used": "used",
    "refurbished": "refurbished",
}


def _normalize(name):
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def detect_variant_profile(product_name):
    name = _normalize(product_name)
    if not name:
        return None

    if "iphone" in name or name == "iphone":
        return "iphone"

    if "macbook" in name or name == "macbook":
        return "macbook"

    if "galaxy watch" in name or ("samsung" in name and "watch" in name):
        return "samsung_galaxy_watch"

    if "apple watch" in name or (name == "watch" and "samsung" not in name and "galaxy" not in name):
        return "apple_watch"

    if name in ("watch", "smartwatch", "smart watch") and "galaxy" not in name:
        return None

    return None


def get_variant_schema(profile_id):
    profile = VARIANT_PROFILES.get(profile_id)
    if not profile:
        return None
    return {
        "profile_id": profile_id,
        "label_key": profile["label_key"],
        "groups": profile["groups"],
    }


def _option_values(group):
    return {opt["value"] for opt in group["options"]}


def validate_selections(profile_id, form_data):
    profile = VARIANT_PROFILES.get(profile_id)
    if not profile:
        return None, ["variants.errors.invalid_profile"]

    selections = {}
    errors = []
    for group in profile["groups"]:
        value = (form_data.get(group["id"]) or "").strip()
        if not value:
            errors.append("variants.errors.required")
            continue
        if value not in _option_values(group):
            errors.append("variants.errors.invalid_option")
            continue
        selections[group["id"]] = value

    if errors:
        return selections, errors
    return selections, []


def build_search_query(profile_id, selections):
    condition = CONDITION_QUERY_LABELS.get(selections.get("condition", "new"), "new")

    if profile_id == "iphone":
        carrier = CARRIER_QUERY_LABELS.get(selections["carrier"], selections["carrier"])
        return f"{selections['series']} {selections['storage']} {carrier} {condition}"

    if profile_id == "apple_watch":
        return (
            f"Apple Watch {selections['series']} {selections['size']} "
            f"{selections['connectivity']} {condition}"
        )

    if profile_id == "samsung_galaxy_watch":
        return (
            f"Samsung {selections['series']} {selections['size']} "
            f"{selections['connectivity']} {condition}"
        )

    if profile_id == "macbook":
        return (
            f"{selections['model']} {selections['chip']} {selections['screen']} "
            f"{selections['storage']} {selections['memory']}"
        )

    return ""


def has_variant_profile(product_name):
    return detect_variant_profile(product_name) is not None
