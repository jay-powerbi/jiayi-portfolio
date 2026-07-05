import json
from pathlib import Path

from flask import g, request, session

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = {
    "en": "English",
    "zh": "中文",
}

_TRANSLATIONS = {}


def _load_translations():
    if _TRANSLATIONS:
        return
    base = Path(__file__).parent / "translations"
    for locale in SUPPORTED_LOCALES:
        path = base / f"{locale}.json"
        with path.open(encoding="utf-8") as handle:
            _TRANSLATIONS[locale] = json.load(handle)


def get_locale():
    return getattr(g, "locale", DEFAULT_LOCALE)


def init_locale(app):
    @app.before_request
    def _set_locale():
        locale = session.get("locale")
        if locale not in SUPPORTED_LOCALES:
            locale = request.accept_languages.best_match(SUPPORTED_LOCALES) or DEFAULT_LOCALE
            session["locale"] = locale
        g.locale = locale

    @app.context_processor
    def _inject_i18n():
        _load_translations()
        return {
            "_": translate,
            "current_locale": get_locale(),
            "supported_locales": SUPPORTED_LOCALES,
        }


def translate(key, **kwargs):
    _load_translations()
    locale = get_locale()
    text = _TRANSLATIONS.get(locale, {}).get(key)
    if text is None:
        text = _TRANSLATIONS.get(DEFAULT_LOCALE, {}).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def flash_t(key, category="message", **kwargs):
    from flask import flash

    flash(translate(key, **kwargs), category)
