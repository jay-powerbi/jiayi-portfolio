from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify, Response
from urllib.parse import quote
import os

from dotenv import load_dotenv

load_dotenv()

from i18n import init_locale, flash_t, translate as t, get_locale

from database import (
    init_db,
    add_price_entry,
    get_dashboard_products,
    get_dashboard_summary,
    product_exists,
    get_product_entries,
    get_product_target,
    get_product_image,
    delete_product,
    delete_product_by_id,
    get_product_by_id,
    get_product_id_by_name,
    ensure_product,
    rename_product,
    set_product_target,
    update_entry,
    add_entry_to_product,
    delete_entry,
    decode_product_name,
    create_image_upload,
    get_image_upload,
    confirm_image_upload,
    save_ai_analysis,
    get_product_images_map,
    add_to_watchlist,
    remove_from_watchlist,
    is_on_watchlist,
    get_watchlist_names,
    get_watchlist_products,
    get_watchlist_count,
    save_contact_message,
    save_portfolio_feedback,
    get_portfolio_feedback,
)
from product_urls import is_usable_product_url, normalize_product_url, stored_product_url
from images import allowed_file, save_upload, MAX_FILE_SIZE, image_url, resolve_product_image_url
from vision import analyze_product_image, result_from_upload_row
from product_suggestions import get_product_suggestions
from price_search import mock_search_prices
from pickup_locations import (
    mock_pickup_locations,
    normalize_zip,
    pickup_retailer_name,
    supports_pickup,
)
from product_variants import (
    build_search_query,
    detect_variant_profile,
    get_variant_schema,
    has_variant_profile,
    validate_selections,
)
from retailer_filter import get_filter_retailers, store_name_to_retailer_id, get_store_branding
from user_prefs import (
    get_notification_permission,
    get_notification_prefs,
    get_saved_zip,
    resolve_zip,
    save_notification_prefs,
    save_zip,
    set_notification_permission,
)
from portfolio_data import PORTFOLIO_EXPERIENCE, PORTFOLIO_LINKS, PORTFOLIO_PROJECT_MAP, PORTFOLIO_PROJECTS
from portfolio_seo import PORTFOLIO_BRAND_TITLE, PORTFOLIO_SITE_URL, portfolio_home_json_ld, render_robots, render_sitemap, seo_context

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-production")
init_locale(app)


@app.after_request
def apply_static_cache(response):
    if (
        response.status_code == 200
        and request.path.startswith("/static/")
        and os.environ.get("SITE_ROOT", "").strip().lower() == "portfolio"
    ):
        response.cache_control.public = True
        response.cache_control.max_age = 86400
    return response


@app.template_global()
def tp(key, params=None):
    """Translate with a params dict (supports nested event_key → event)."""
    params = dict(params or {})
    if "event_key" in params:
        params["event"] = t(params.pop("event_key"))
    return t(key, **params)


@app.template_global()
def static_v(filename):
    """Versioned static asset URL to bust browser cache after deploys."""
    path = os.path.join(app.static_folder, filename)
    version = int(os.path.getmtime(path)) if os.path.isfile(path) else 0
    return url_for("static", filename=filename, v=version)


@app.context_processor
def inject_user_prefs():
    return {
        "saved_zip": get_saved_zip(),
        "notification_prefs": get_notification_prefs(),
        "notification_permission": get_notification_permission(),
        "filter_retailers": get_filter_retailers(),
        "portfolio_ga4_id": os.environ.get("GA4_MEASUREMENT_ID", "").strip(),
        "portfolio_links": PORTFOLIO_LINKS,
        "portfolio_site_url": PORTFOLIO_SITE_URL,
    }


_db_initialized = False


@app.before_request
def setup():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True


AUTO_CONFIRM_IMAGE_CONFIDENCE = 0.72


def get_product_image_preview(product_name, upload_id=None):
    if product_name:
        product_image = get_product_image(product_name)
        if product_image:
            return image_url(product_image["filename"])
    if upload_id:
        upload = get_image_upload(upload_id)
        if upload and upload.get("filename"):
            return image_url(upload["filename"])
    if product_name:
        return resolve_product_image_url(product_name)
    return None


def attach_upload_to_product(product_name, upload_id):
    if not product_name or not upload_id:
        return False
    upload = get_image_upload(upload_id)
    if not upload or not upload.get("filename"):
        return False
    if upload["confirmed"]:
        return upload["product_name"] == product_name
    ai_detected_name = None
    if upload["ai_analyzed"]:
        ai_result = result_from_upload_row(upload)
        if ai_result.get("identified"):
            ai_detected_name = ai_result.get("product_name")
    confirm_image_upload(upload_id, product_name, ai_detected_name)
    return True


def redirect_after_scan_product(product_name, upload_id):
    if has_variant_profile(product_name):
        return redirect(url_for("select_variants", product_name=product_name, upload_id=upload_id))
    return redirect(url_for("price_search", product_name=product_name, upload_id=upload_id))


    errors = []
    price = None
    target_price = None

    if require_price and not price_raw:
        errors.append("errors.price_required")
    elif price_raw:
        try:
            price = float(price_raw)
            if price < 0:
                errors.append("errors.price_min")
        except ValueError:
            errors.append("errors.price_invalid")

    if target_raw:
        try:
            target_price = float(target_raw)
            if target_price < 0:
                errors.append("errors.target_min")
        except ValueError:
            errors.append("errors.target_invalid")

    return errors, price, target_price


def build_product_list(search=None, sort="price_asc", watchlist_names=None):
    products = []
    images = get_product_images_map()
    if watchlist_names is None:
        watchlist_names = get_watchlist_names()
    for row in get_dashboard_products(search=search, sort=sort):
        target = row["target_price"]
        lowest = row["lowest_price"]
        status = "alert" if target is not None and lowest <= target else "tracking"
        product_name = row["product_name"]
        image_filename = images.get(product_name)
        product_record = get_product_by_id(get_product_id_by_name(product_name)) if product_name else None
        if not product_record and product_name:
            product_record = ensure_product(product_name)
        store_brand = get_store_branding(row["store_name"])
        product_url = stored_product_url(row["product_url"])
        link_available = product_url is not None

        products.append(
            {
                "id": product_record["id"] if product_record else None,
                "product_name": product_name,
                "lowest_price": lowest,
                "store_name": store_brand["store_name"],
                "store_logo_text": store_brand["logo_text"],
                "store_logo_class": store_brand["logo_class"],
                "store_retailer_id": store_brand["retailer_id"] or store_name_to_retailer_id(row["store_name"]),
                "product_url": product_url,
                "product_link_available": link_available,
                "target_price": target,
                "last_updated": row["last_updated"],
                "savings": row["savings"],
                "status": status,
                "image_url": resolve_product_image_url(product_name, image_filename),
                "on_watchlist": product_name in watchlist_names,
            }
        )
    return products


def build_watchlist():
    items = []
    images = get_product_images_map()
    for row in get_watchlist_products():
        target = row["target_price"]
        lowest = row["lowest_price"]
        product_name = row["product_name"]
        if lowest is None or target is None:
            status = "tracking"
        else:
            status = "alert" if lowest <= target else "tracking"
        image_filename = images.get(product_name)
        store_brand = get_store_branding(row["store_name"] or "")
        product_url = stored_product_url(row["product_url"])
        link_available = product_url is not None

        items.append(
            {
                "id": row["product_id"],
                "product_name": product_name,
                "lowest_price": lowest,
                "store_name": store_brand["store_name"],
                "store_logo_text": store_brand["logo_text"],
                "store_logo_class": store_brand["logo_class"],
                "store_retailer_id": store_brand["retailer_id"],
                "product_url": product_url,
                "product_link_available": link_available,
                "target_price": target,
                "added_at": row["added_at"],
                "status": status,
                "image_url": resolve_product_image_url(product_name, image_filename),
            }
        )
    return items


def redirect_back(default="dashboard"):
    target = request.referrer
    if target and target.startswith(request.host_url):
        return redirect(target)
    return redirect(url_for(default))


def ensure_ai_analysis(upload):
    if upload["ai_analyzed"]:
        return result_from_upload_row(upload)

    result = analyze_product_image(upload["filename"])
    save_ai_analysis(upload["id"], result)
    return result


def render_confirm_upload(upload, product_name="", ai_result=None):
    if ai_result is None:
        ai_result = ensure_ai_analysis(upload)

    if not product_name:
        if ai_result.get("suggested_name"):
            product_name = ai_result["suggested_name"]
        elif ai_result.get("identified") and ai_result.get("product_name"):
            product_name = ai_result["product_name"]

    detect_name = ai_result.get("product_name") or product_name
    product_suggestions = get_product_suggestions(detect_name, get_locale())

    return render_template(
        "upload_confirm.html",
        upload=upload,
        preview_url=image_url(upload["filename"]),
        ai_result=ai_result,
        product_name=product_name,
        product_suggestions=product_suggestions,
    )


@app.route("/lang/<locale>")
def set_language(locale):
    from i18n import SUPPORTED_LOCALES

    if locale in SUPPORTED_LOCALES:
        session["locale"] = locale
    return redirect(request.referrer or url_for("landing"))


@app.route("/")
def landing():
    if os.environ.get("SITE_ROOT", "").strip().lower() == "portfolio":
        return redirect(url_for("portfolio_home"))
    return render_template("landing.html")


@app.route("/portfolio")
def portfolio_home():
    return render_template(
        "portfolio.html",
        projects=PORTFOLIO_PROJECTS,
        experience=PORTFOLIO_EXPERIENCE,
        seo=seo_context(
            title=PORTFOLIO_BRAND_TITLE,
            path="/portfolio",
            json_ld=portfolio_home_json_ld(),
        ),
    )


@app.route("/sitemap.xml")
def sitemap():
    return Response(render_sitemap(), mimetype="application/xml; charset=utf-8")


@app.route("/robots.txt")
def robots():
    return Response(render_robots(), mimetype="text/plain")


@app.route("/portfolio/resume")
def portfolio_resume():
    return send_from_directory(
        os.path.join(app.root_path, "static", "files"),
        "Jiayi_Shi_Resume.docx",
        as_attachment=True,
        download_name="Jiayi_Shi_Resume.docx",
    )


@app.route("/portfolio/feedback", methods=["POST"])
def portfolio_feedback():
    payload = request.get_json(silent=True) or {}
    liked = str(payload.get("liked", "")).strip()[:20]
    message = str(payload.get("message", "")).strip()[:2000]
    page = str(payload.get("page", "")).strip()[:500]
    try:
        time_on_page_seconds = int(payload.get("time_on_page_seconds", 0))
    except (TypeError, ValueError):
        time_on_page_seconds = 0

    if not liked and not message:
        return jsonify({"ok": False, "error": "Feedback is empty."}), 400

    save_portfolio_feedback(
        liked=liked,
        message=message,
        page=page,
        user_agent=request.headers.get("User-Agent", "")[:500],
        ip_address=(request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip())[:80],
        time_on_page_seconds=max(0, time_on_page_seconds),
    )
    return jsonify({"ok": True})


@app.route("/portfolio/feedback-admin")
def portfolio_feedback_admin():
    admin_token = os.environ.get("PORTFOLIO_ADMIN_TOKEN") or app.secret_key
    if request.args.get("token") != admin_token:
        return "Not found", 404
    return render_template(
        "portfolio_feedback_admin.html",
        feedback=get_portfolio_feedback(),
        seo=seo_context(
            title="Portfolio Feedback - Admin",
            description="Private portfolio feedback admin view.",
            path="/portfolio/feedback-admin",
            noindex=True,
        ),
    )


@app.route("/portfolio/projects/<slug>")
def portfolio_project(slug):
    project = PORTFOLIO_PROJECT_MAP.get(slug)
    if project is None:
        return redirect(url_for("portfolio_home"))
    template = "portfolio_project_case_study.html" if project.get("case_study") else "portfolio_project.html"
    return render_template(
        template,
        project=project,
        seo=seo_context(
            title=f"{project['title']} - Jiayi Shi Portfolio",
            description=project.get("summary"),
            path=f"/portfolio/projects/{slug}",
            image=project.get("preview_image"),
            og_type="article",
        ),
    )


@app.route("/portfolio/about")
def portfolio_about():
    return render_template(
        "portfolio_about.html",
        seo=seo_context(
            title="About - Jiayi Shi",
            description=(
                "Learn about Jiayi Shi, Senior BI Developer with 8+ years of experience in "
                "Power BI, SQL, ETL, and enterprise dashboard delivery."
            ),
            path="/portfolio/about",
        ),
    )


@app.route("/portfolio/contact")
def portfolio_contact():
    return render_template(
        "portfolio_contact.html",
        seo=seo_context(
            title="Contact - Jiayi Shi",
            description="Contact Jiayi Shi for BI developer opportunities, portfolio inquiries, and collaboration.",
            path="/portfolio/contact",
        ),
    )


@app.route("/portfolio/opportunities")
def portfolio_opportunities():
    return render_template(
        "portfolio_opportunities.html",
        seo=seo_context(
            title="Open to Opportunities - Jiayi Shi",
            description=(
                "Jiayi Shi is open to Senior BI Developer and Power BI Developer roles across the U.S., "
                "including remote and relocation-friendly opportunities."
            ),
            path="/portfolio/opportunities",
        ),
    )


@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not message:
        flash_t("errors.contact_required", "error")
    else:
        save_contact_message(name, email, message)
        flash_t("flash.contact_success", "success")

    return redirect(url_for("landing"))


@app.route("/dashboard")
def dashboard():
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "price_asc")
    products = build_product_list(search=search or None, sort=sort)
    summary = get_dashboard_summary()

    return render_template(
        "index.html",
        products=products,
        summary=summary,
        search=search,
        sort=sort,
    )


@app.route("/alerts")
def alerts():
    products = [p for p in build_product_list(sort="price_asc") if p["status"] == "alert"]
    return render_template("alerts.html", products=products)


@app.route("/scan")
def scan():
    return render_template("scan.html")


def build_compare_summary(product_name, listings):
    if not listings:
        return None
    valid = [l for l in listings if not l.get("price_abnormal")]
    prices = [l["total_delivered"] for l in valid] or [l["total_delivered"] for l in listings]
    rating, review_count = _demo_product_rating(product_name)
    return {
        "lowest_price": min(prices) if prices else None,
        "store_count": len(listings),
        "rating": rating,
        "review_count": review_count,
    }


def _demo_product_rating(product_name):
    import hashlib

    digest = hashlib.md5((product_name or "").encode("utf-8")).hexdigest()
    rating = round(4.0 + (int(digest[:2], 16) % 10) / 10, 1)
    review_count = 150 + int(digest[2:6], 16) % 4850
    return rating, review_count


@app.route("/compare")
def compare():
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "price_asc")
    product_param = request.args.get("product", "").strip()
    products = build_product_list(search=search or None, sort=sort)
    all_products = build_product_list(sort="name")
    product_options = [p["product_name"] for p in all_products]

    compare_product = product_param or search or (products[0]["product_name"] if products else "")
    compare_listings = []
    compare_image_url = None
    compare_summary = None
    if compare_product:
        zip_code = get_saved_zip()
        compare_listings = mock_search_prices(compare_product, zip_code)
        compare_image_url = get_product_image_preview(compare_product)
        compare_summary = build_compare_summary(compare_product, compare_listings)

    return render_template(
        "compare.html",
        products=products,
        product_options=product_options,
        search=search,
        sort=sort,
        compare_product=compare_product,
        compare_listings=compare_listings,
        compare_image_url=compare_image_url,
        compare_summary=compare_summary,
    )


@app.route("/design-system")
def design_system():
    return render_template("design_system.html")


@app.route("/profile")
def profile():
    return render_template("profile.html")


@app.route("/settings/notifications", methods=["GET"])
def notification_settings():
    return render_template(
        "settings_notifications.html",
        permission=get_notification_permission(),
    )


@app.route("/settings/zip", methods=["POST"])
def update_zip():
    zip_code = save_zip(request.form.get("zip", ""))
    if not zip_code:
        flash_t("flash.invalid_zip", "error")
    else:
        flash_t("flash.zip_saved", "success", zip=zip_code)

    next_url = request.form.get("next") or request.referrer or url_for("dashboard")
    return redirect(next_url)


@app.route("/settings/notifications/permission", methods=["POST"])
def update_notification_permission():
    status = request.form.get("status", "default")
    if status in ("granted", "denied", "default"):
        set_notification_permission(status)
    return ("", 204)


@app.route("/watchlist")
def watchlist():
    items = build_watchlist()
    alert_count = sum(1 for item in items if item["status"] == "alert")
    return render_template(
        "watchlist.html",
        items=items,
        watchlist_count=get_watchlist_count(),
        alert_count=alert_count,
    )


@app.route("/watchlist/add/<path:product_name>", methods=["POST"])
def add_to_watchlist_route(product_name):
    product_name = decode_product_name(product_name)
    if not product_exists(product_name):
        flash_t("flash.product_not_found", "error")
        return redirect(url_for("dashboard"))

    if is_on_watchlist(product_name):
        flash_t("flash.already_on_watchlist", "error", name=product_name)
    else:
        add_to_watchlist(product_name)
        flash_t("flash.added_watchlist", "success", name=product_name)

    return redirect_back()


@app.route("/watchlist/remove/<path:product_name>", methods=["POST"])
def remove_from_watchlist_route(product_name):
    product_name = decode_product_name(product_name)
    if is_on_watchlist(product_name):
        remove_from_watchlist(product_name)
        flash_t("flash.removed_watchlist", "success", name=product_name)
    else:
        flash_t("flash.not_on_watchlist", "error")

    return redirect_back()


@app.route("/upload", methods=["GET", "POST"])
def upload_product():
    if request.method == "POST":
        file = request.files.get("product_image")
        if not file or not file.filename:
            flash_t("flash.select_image", "error")
            return render_template("upload.html")

        if not allowed_file(file.filename):
            flash_t("flash.invalid_file_type", "error")
            return render_template("upload.html")

        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            flash_t("flash.image_too_large", "error")
            return render_template("upload.html")

        upload_id, filename, original = save_upload(file)
        create_image_upload(upload_id, filename, original)
        result = analyze_product_image(filename)
        save_ai_analysis(upload_id, result)

        product_name = (result.get("suggested_name") or result.get("product_name") or "").strip()
        confidence = result.get("confidence") or 0
        auto_confirm = (
            result.get("identified")
            and product_name
            and confidence >= AUTO_CONFIRM_IMAGE_CONFIDENCE
        )

        if auto_confirm:
            confirm_image_upload(upload_id, product_name, result.get("product_name"))
            flash_t("flash.ai_auto_confirmed", "success", name=product_name)
            return redirect_after_scan_product(product_name, upload_id)

        if result.get("identified"):
            flash_t("flash.ai_identified", "success")
        elif result.get("error"):
            flash_t("flash.ai_unavailable", "error", error=result["error"])
        else:
            flash_t("flash.ai_not_identified", "error")
        return redirect(url_for("confirm_upload", upload_id=upload_id))

    return render_template("upload.html")


@app.route("/upload/confirm/<upload_id>", methods=["GET", "POST"])
def confirm_upload(upload_id):
    upload = get_image_upload(upload_id)
    if not upload:
        flash_t("flash.upload_not_found", "error")
        return redirect(url_for("upload_product"))

    if upload["confirmed"]:
        flash_t("flash.already_confirmed", "success")
        product_name = upload["product_name"]
        return redirect_after_scan_product(product_name, upload_id)

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        ai_result = ensure_ai_analysis(get_image_upload(upload_id))

        if not product_name:
            flash_t("flash.enter_product_name", "error")
            return render_confirm_upload(upload, product_name="", ai_result=ai_result)

        ai_detected_name = ai_result.get("product_name") if ai_result.get("identified") else None
        confirm_image_upload(upload_id, product_name, ai_detected_name)
        flash_t("flash.photo_saved", "success", name=product_name)
        return redirect_after_scan_product(product_name, upload_id)

    return render_confirm_upload(upload)


@app.route("/search/variants", methods=["GET", "POST"])
def select_variants():
    product_name = request.args.get("product_name", "").strip() or request.form.get("product_name", "").strip()
    upload_id = request.args.get("upload_id", "").strip() or request.form.get("upload_id", "").strip()
    profile_id = detect_variant_profile(product_name)

    if not product_name:
        flash_t("flash.enter_product_name", "error")
        return redirect(url_for("upload_product"))

    if not profile_id:
        return redirect(url_for("price_search", product_name=product_name, upload_id=upload_id))

    schema = get_variant_schema(profile_id)
    product_image = get_product_image(product_name)
    image_preview = image_url(product_image["filename"]) if product_image else None
    if not image_preview:
        image_preview = get_product_image_preview(product_name, upload_id or None)

    selections = {}

    if request.method == "POST":
        selections, errors = validate_selections(profile_id, request.form)
        if errors:
            for error in set(errors):
                flash_t(error, "error")
        else:
            search_query = build_search_query(profile_id, selections)
            flash_t("flash.variants_saved", "success")
            return redirect(
                url_for(
                    "price_search",
                    product_name=search_query,
                    base_name=product_name,
                    upload_id=upload_id,
                )
            )
        # Preserve submitted values after validation errors
        if not selections:
            selections = {
                group["id"]: (request.form.get(group["id"]) or "").strip()
                for group in schema["groups"]
            }

    return render_template(
        "product_variants.html",
        product_name=product_name,
        upload_id=upload_id,
        schema=schema,
        selections=selections,
        image_preview=image_preview,
    )


@app.route("/search/prices", methods=["GET"])
def price_search():
    product_name = request.args.get("product_name", "").strip()
    base_name = request.args.get("base_name", "").strip() or product_name
    upload_id = request.args.get("upload_id", "").strip()
    change_zip = request.args.get("change_zip") == "1"
    explicit_zip = normalize_zip(request.args.get("zip", ""))

    if explicit_zip:
        zip_code = save_zip(explicit_zip) or explicit_zip
    elif change_zip:
        zip_code = ""
    else:
        zip_code = get_saved_zip()

    if not product_name:
        flash_t("flash.enter_product_name", "error")
        return redirect(url_for("upload_product"))

    image_preview = get_product_image_preview(base_name or product_name, upload_id or None)

    if not zip_code:
        return render_template(
            "price_search.html",
            product_name=product_name,
            base_name=base_name,
            zip_code=get_saved_zip() if change_zip else "",
            upload_id=upload_id,
            listings=[],
            image_preview=image_preview,
            change_zip=True,
            saved_zip=get_saved_zip(),
            needs_zip=True,
        )

    listings = mock_search_prices(product_name, zip_code)

    return render_template(
        "price_search.html",
        product_name=product_name,
        base_name=base_name,
        zip_code=zip_code,
        upload_id=upload_id,
        listings=listings,
        image_preview=image_preview,
        change_zip=change_zip,
        saved_zip=get_saved_zip(),
        needs_zip=False,
    )


@app.route("/search/pickup", methods=["GET"])
def pickup_details():
    retailer_id = request.args.get("retailer", "").strip().lower()
    product_name = request.args.get("product_name", "").strip()
    base_name = request.args.get("base_name", "").strip() or product_name
    zip_code = resolve_zip(request.args.get("zip", ""))
    upload_id = request.args.get("upload_id", "").strip()
    pickup_key = request.args.get("pickup_key", "").strip()
    product_url = request.args.get("product_url", "").strip()

    if not product_name or not retailer_id:
        flash_t("pickup.errors.missing_info", "error")
        return redirect(url_for("upload_product"))

    if not supports_pickup(retailer_id):
        flash_t("pickup.errors.no_pickup", "error")
        return redirect(
            url_for(
                "price_search",
                product_name=product_name,
                base_name=base_name,
                zip=zip_code,
                upload_id=upload_id,
            )
        )

    retailer_name = pickup_retailer_name(retailer_id)
    normalized_zip = normalize_zip(zip_code)
    locations = []

    if normalized_zip:
        locations = mock_pickup_locations(
            retailer_id,
            normalized_zip,
            product_name,
            pickup_key=pickup_key or None,
        )

    image_preview = get_product_image_preview(base_name or product_name, upload_id or None)

    back_url = url_for(
        "price_search",
        product_name=product_name,
        base_name=base_name,
        zip=normalized_zip,
        upload_id=upload_id,
    )

    return render_template(
        "pickup_details.html",
        retailer_id=retailer_id,
        retailer_name=retailer_name,
        product_name=product_name,
        base_name=base_name,
        zip_code=normalized_zip,
        upload_id=upload_id,
        pickup_key=pickup_key,
        product_url=product_url,
        locations=locations,
        needs_zip=not normalized_zip,
        image_preview=image_preview,
        back_url=back_url,
    )


@app.route("/search/prices/track", methods=["POST"])
def track_search_price():
    product_name = request.form.get("product_name", "").strip()
    store_name = request.form.get("store_name", "").strip()
    product_url = request.form.get("product_url", "").strip()
    price_raw = request.form.get("price", "").strip()
    upload_id = request.form.get("upload_id", "").strip()

    if not product_name or not store_name or not price_raw:
        flash_t("errors.search_track_required", "error")
        return redirect(url_for("price_search", product_name=product_name, upload_id=upload_id))

    product_url = normalize_product_url(product_url)
    if not is_usable_product_url(product_url):
        flash_t("errors.invalid_product_url", "error")
        return redirect(url_for("price_search", product_name=product_name, upload_id=upload_id))

    try:
        price = float(price_raw)
        if price < 0:
            raise ValueError
    except ValueError:
        flash_t("errors.price_invalid", "error")
        return redirect(url_for("price_search", product_name=product_name, upload_id=upload_id))

    add_price_entry(product_name, store_name, product_url, price, None)
    if attach_upload_to_product(product_name, upload_id):
        flash_t("flash.tracked_with_photo", "success", product=product_name, store=store_name)
    else:
        flash_t("flash.tracked_search_price", "success", product=product_name, store=store_name)
    return redirect(url_for("compare", q=product_name))


@app.route("/add", methods=["GET", "POST"])
def add_product():
    prefilled_name = request.args.get("product_name", "").strip()

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        store_name = request.form.get("store_name", "").strip()
        product_url = request.form.get("product_url", "").strip()
        price_raw = request.form.get("price", "").strip()
        target_raw = request.form.get("target_price", "").strip()

        errors = []
        if not product_name:
            errors.append("errors.product_name_required")
        if not store_name:
            errors.append("errors.store_name_required")

        price_errors, price, target_price = parse_price_fields(price_raw, target_raw)
        errors.extend(price_errors)

        cleaned_url = normalize_product_url(product_url)
        if product_url.strip() and not is_usable_product_url(cleaned_url):
            errors.append("errors.invalid_product_url")
        elif not product_url.strip():
            errors.append("errors.product_url_required")

        if errors:
            for error in errors:
                flash(t(error), "error")
            product_image = get_product_image(product_name)
            return render_template(
                "add.html",
                form={
                    "product_name": product_name,
                    "store_name": store_name,
                    "product_url": product_url,
                    "price": price_raw,
                    "target_price": target_raw,
                },
                image_preview=image_url(product_image["filename"]) if product_image else None,
            )

        add_price_entry(product_name, store_name, cleaned_url, price, target_price)
        flash_t("flash.added_price", "success", product=product_name, store=store_name)
        return redirect(url_for("compare", q=product_name))

    product_image = get_product_image(prefilled_name) if prefilled_name else None
    form = {"product_name": prefilled_name} if prefilled_name else {}
    image_preview = image_url(product_image["filename"]) if product_image else None

    return render_template(
        "add.html",
        form=form,
        image_preview=image_preview,
    )


@app.route("/product/<path:product_name>/edit", methods=["GET", "POST"])
def edit_product(product_name):
    product_name = decode_product_name(product_name)
    if not product_exists(product_name):
        flash_t("flash.product_not_found", "error")
        return redirect(url_for("dashboard"))

    entries = get_product_entries(product_name)
    target = get_product_target(product_name)
    product_image = get_product_image(product_name)
    image_preview = image_url(product_image["filename"]) if product_image else None

    if request.method == "POST":
        action = request.form.get("action", "save")

        if action == "delete_product":
            product_id = get_product_id_by_name(product_name)
            if product_id:
                delete_product_by_id(product_id)
            else:
                delete_product(product_name)
            flash_t("flash.deleted_product", "success", name=product_name)
            return redirect(url_for("dashboard"))

        if action == "delete_entry":
            entry_id = request.form.get("entry_id")
            if entry_id:
                delete_entry(int(entry_id))
                remaining = get_product_entries(product_name)
                if not remaining:
                    flash_t("flash.deleted_no_entries", "success", name=product_name)
                    return redirect(url_for("dashboard"))
                flash_t("flash.entry_removed", "success")
            return redirect(url_for("edit_product", product_name=quote(product_name)))

        new_name = request.form.get("product_name", "").strip()
        target_raw = request.form.get("target_price", "").strip()

        errors = []
        if not new_name:
            errors.append("errors.product_name_required")

        _, _, target_price = parse_price_fields("", target_raw, require_price=False)

        if errors:
            for error in errors:
                flash(t(error), "error")
        else:
            if new_name != product_name:
                if product_exists(new_name):
                    flash_t("flash.product_exists", "error", name=new_name)
                    return redirect(url_for("edit_product", product_name=quote(product_name)))
                rename_product(product_name, new_name)
                product_name = new_name

            set_product_target(product_name, target_price)

            for entry in get_product_entries(product_name):
                entry_id = str(entry["id"])
                store_name = request.form.get(f"store_name_{entry_id}", "").strip()
                product_url = request.form.get(f"product_url_{entry_id}", "").strip()
                price_raw = request.form.get(f"price_{entry_id}", "").strip()

                if not store_name or not price_raw:
                    continue

                entry_errors, price, _ = parse_price_fields(price_raw, "", require_price=True)
                if entry_errors:
                    for error in entry_errors:
                        flash(t(error), "error")
                    return redirect(url_for("edit_product", product_name=quote(product_name)))

                cleaned_url = normalize_product_url(product_url)
                if not is_usable_product_url(cleaned_url):
                    flash_t("errors.invalid_product_url", "error")
                    return redirect(url_for("edit_product", product_name=quote(product_name)))

                update_entry(entry["id"], store_name, cleaned_url, price, target_price)

            new_store = request.form.get("new_store_name", "").strip()
            new_url = request.form.get("new_product_url", "").strip()
            new_price_raw = request.form.get("new_price", "").strip()
            if new_store and new_url and new_price_raw:
                entry_errors, new_price, _ = parse_price_fields(new_price_raw, "", require_price=True)
                if entry_errors:
                    for error in entry_errors:
                        flash(t(error), "error")
                elif not is_usable_product_url(normalize_product_url(new_url)):
                    flash_t("errors.invalid_product_url", "error")
                else:
                    add_entry_to_product(product_name, new_store, new_url, new_price, target_price)

            flash_t("flash.updated_product", "success", name=product_name)
            return redirect(url_for("dashboard"))

        entries = get_product_entries(product_name)
        target = get_product_target(product_name)

    return render_template(
        "edit.html",
        product_name=product_name,
        product_id=get_product_id_by_name(product_name),
        entries=entries,
        target_price=target,
        image_preview=image_preview,
        on_watchlist=is_on_watchlist(product_name),
    )


@app.route("/products/<int:product_id>/delete", methods=["POST"])
def delete_product_by_id_route(product_id):
    posted_id = request.form.get("product_id", type=int)
    if posted_id is not None and posted_id != product_id:
        flash_t("flash.delete_failed", "error")
        return redirect(url_for("dashboard"))

    product = get_product_by_id(product_id)
    if not product:
        flash_t("flash.product_not_found", "error")
        return redirect(url_for("dashboard"))

    delete_product_by_id(product_id)
    flash_t("flash.deleted_product", "success", name=product["name"])
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/product/<path:product_name>/delete", methods=["POST"])
def delete_product_route(product_name):
    product_name = decode_product_name(product_name)
    product_id = get_product_id_by_name(product_name)
    if product_id:
        product = get_product_by_id(product_id)
        delete_product_by_id(product_id)
        flash_t("flash.deleted_product", "success", name=product["name"])
        return redirect(request.referrer or url_for("dashboard"))

    if not product_exists(product_name):
        flash_t("flash.product_not_found", "error")
        return redirect(url_for("dashboard"))

    delete_product(product_name)
    flash_t("flash.deleted_product", "success", name=product_name)
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    import socket

    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")

    lan_ip = None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            lan_ip = sock.getsockname()[0]
    except OSError:
        pass

    print(f"Local:   http://127.0.0.1:{port}/")
    if lan_ip:
        print(f"Mobile:  http://{lan_ip}:{port}/  (same Wi‑Fi required)")
    app.run(debug=True, host=host, port=port)
