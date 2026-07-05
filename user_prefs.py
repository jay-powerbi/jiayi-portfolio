from flask import session

from pickup_locations import normalize_zip

ZIP_SESSION_KEY = "user_zip"
NOTIF_PREFS_KEY = "notification_prefs"
NOTIF_PERMISSION_KEY = "notification_permission"

DEFAULT_NOTIFICATION_PREFS = {
    "price_drops": True,
    "back_in_stock": True,
    "weekly_digest": False,
    "shopping_events": True,
}


def get_saved_zip():
    return session.get(ZIP_SESSION_KEY, "")


def save_zip(zip_code):
    normalized = normalize_zip(zip_code)
    if normalized:
        session[ZIP_SESSION_KEY] = normalized
    return normalized


def resolve_zip(request_zip=""):
    explicit = normalize_zip(request_zip)
    if explicit:
        save_zip(explicit)
        return explicit
    return get_saved_zip()


def get_notification_prefs():
    stored = session.get(NOTIF_PREFS_KEY)
    if not isinstance(stored, dict):
        return dict(DEFAULT_NOTIFICATION_PREFS)
    merged = dict(DEFAULT_NOTIFICATION_PREFS)
    merged.update({k: bool(stored.get(k, merged[k])) for k in merged})
    return merged


def save_notification_prefs(form_data):
    prefs = {
        "price_drops": form_data.get("price_drops") == "on",
        "back_in_stock": form_data.get("back_in_stock") == "on",
        "weekly_digest": form_data.get("weekly_digest") == "on",
        "shopping_events": form_data.get("shopping_events") == "on",
    }
    session[NOTIF_PREFS_KEY] = prefs
    return prefs


def get_notification_permission():
    return session.get(NOTIF_PERMISSION_KEY, "default")


def set_notification_permission(status):
    session[NOTIF_PERMISSION_KEY] = status
