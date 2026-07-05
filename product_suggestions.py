import re

GENERIC_MODIFIERS = {
    "wireless",
    "bluetooth",
    "smart",
    "portable",
    "digital",
    "electronic",
    "generic",
    "unknown",
}

CATEGORY_ALIASES = {
    "watch": {
        "en": ["watch", "watches", "smartwatch", "smart watch"],
        "zh": ["手表", "智能手表", "腕表", "运动手表"],
    },
    "headphones": {
        "en": ["headphones", "headphone", "earphones", "earbuds", "headset"],
        "zh": ["耳机", "头戴式耳机", "无线耳机", "蓝牙耳机"],
    },
    "phone": {
        "en": ["phone", "phones", "smartphone", "smart phone", "mobile phone", "cell phone"],
        "zh": ["手机", "智能手机", "移动电话"],
    },
    "laptop": {
        "en": ["laptop", "laptops", "notebook", "notebook computer", "ultrabook"],
        "zh": ["笔记本", "笔记本电脑", "便携电脑"],
    },
    "tablet": {
        "en": ["tablet", "tablets", "pad"],
        "zh": ["平板", "平板电脑", "平板设备"],
    },
}

SUGGESTIONS = {
    "watch": {
        "en": [
            "Apple Watch",
            "Samsung Galaxy Watch",
            "Garmin Watch",
            "Fitbit",
            "Google Pixel Watch",
        ],
        "zh": [
            "Apple Watch",
            "Samsung Galaxy Watch",
            "Garmin 手表",
            "Fitbit",
            "Google Pixel Watch",
        ],
    },
    "headphones": {
        "en": [
            "AirPods",
            "Sony WH-1000XM",
            "Bose QuietComfort",
            "Beats",
            "Samsung Galaxy Buds",
        ],
        "zh": [
            "AirPods",
            "Sony WH-1000XM",
            "Bose QuietComfort",
            "Beats",
            "Samsung Galaxy Buds",
        ],
    },
    "phone": {
        "en": ["iPhone", "Samsung Galaxy", "Google Pixel", "OnePlus"],
        "zh": ["iPhone", "Samsung Galaxy", "Google Pixel", "OnePlus"],
    },
    "laptop": {
        "en": [
            "MacBook",
            "Dell XPS",
            "Lenovo ThinkPad",
            "HP Spectre",
            "Microsoft Surface",
        ],
        "zh": [
            "MacBook",
            "Dell XPS",
            "Lenovo ThinkPad",
            "HP Spectre",
            "Microsoft Surface",
        ],
    },
    "tablet": {
        "en": [
            "iPad",
            "Samsung Galaxy Tab",
            "Microsoft Surface",
            "Lenovo Tab",
        ],
        "zh": [
            "iPad",
            "Samsung Galaxy Tab",
            "Microsoft Surface",
            "Lenovo Tab",
        ],
    },
}


def _normalize(name):
    text = (name or "").strip().lower()
    text = re.sub(r"[^\w\s\u4e00-\u9fff-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for article in ("a ", "an ", "the "):
        if text.startswith(article):
            text = text[len(article) :].strip()
    return text


def _alias_lookup():
    lookup = {}
    for category, locales in CATEGORY_ALIASES.items():
        aliases = set()
        for alias_list in locales.values():
            for alias in alias_list:
                aliases.add(_normalize(alias))
        lookup[category] = aliases
    return lookup


_ALIAS_LOOKUP = _alias_lookup()


def detect_generic_category(product_name):
    normalized = _normalize(product_name)
    if not normalized:
        return None

    words = normalized.split()

    for category, aliases in _ALIAS_LOOKUP.items():
        if normalized in aliases:
            return category

        if len(words) == 1 and words[0] in aliases:
            return category

        if words and words[-1] in aliases:
            if len(words) == 1:
                return category
            if all(word in GENERIC_MODIFIERS for word in words[:-1]):
                return category

    return None


def get_product_suggestions(product_name, locale="en"):
    category = detect_generic_category(product_name)
    if not category:
        return []

    locale_key = locale if locale in SUGGESTIONS[category] else "en"
    return list(SUGGESTIONS[category][locale_key])
