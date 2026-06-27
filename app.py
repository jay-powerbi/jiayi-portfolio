from flask import Flask, render_template, request, redirect, url_for, flash
from urllib.parse import quote

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
)
from images import allowed_file, save_upload, MAX_FILE_SIZE, image_url
from vision import analyze_product_image, result_from_upload_row

app = Flask(__name__)
app.secret_key = "dev-secret-change-in-production"
_db_initialized = False


@app.before_request
def setup():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True


def parse_price_fields(price_raw, target_raw, require_price=True):
    errors = []
    price = None
    target_price = None

    if require_price and not price_raw:
        errors.append("Price is required.")
    elif price_raw:
        try:
            price = float(price_raw)
            if price < 0:
                errors.append("Price must be zero or greater.")
        except ValueError:
            errors.append("Price must be a valid number.")

    if target_raw:
        try:
            target_price = float(target_raw)
            if target_price < 0:
                errors.append("Target price must be zero or greater.")
        except ValueError:
            errors.append("Target price must be a valid number.")

    return errors, price, target_price


def build_product_list(search=None, sort="price_asc", watchlist_names=None):
    products = []
    images = get_product_images_map()
    if watchlist_names is None:
        watchlist_names = get_watchlist_names()
    for row in get_dashboard_products(search=search, sort=sort):
        target = row["target_price"]
        lowest = row["lowest_price"]
        status = "Alert" if target is not None and lowest <= target else "Tracking"
        product_name = row["product_name"]
        image_filename = images.get(product_name)

        products.append(
            {
                "product_name": product_name,
                "lowest_price": lowest,
                "store_name": row["store_name"],
                "product_url": row["product_url"],
                "target_price": target,
                "last_updated": row["last_updated"],
                "savings": row["savings"],
                "status": status,
                "image_url": image_url(image_filename) if image_filename else None,
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
        status = "Alert" if target is not None and lowest <= target else "Tracking"
        product_name = row["product_name"]
        image_filename = images.get(product_name)

        items.append(
            {
                "product_name": product_name,
                "lowest_price": lowest,
                "store_name": row["store_name"],
                "product_url": row["product_url"],
                "target_price": target,
                "added_at": row["added_at"],
                "status": status,
                "image_url": image_url(image_filename) if image_filename else None,
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

    if not product_name and ai_result.get("suggested_name"):
        product_name = ai_result["suggested_name"]

    return render_template(
        "upload_confirm.html",
        upload=upload,
        preview_url=image_url(upload["filename"]),
        ai_result=ai_result,
        product_name=product_name,
    )


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not message:
        flash("Please fill in all fields.", "error")
    else:
        save_contact_message(name, email, message)
        flash("Thanks for reaching out! We'll get back to you within 24 hours.", "success")

    return redirect(url_for("landing") + "#contact")


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


@app.route("/watchlist")
def watchlist():
    items = build_watchlist()
    alert_count = sum(1 for item in items if item["status"] == "Alert")
    return render_template(
        "watchlist.html",
        items=items,
        watchlist_count=len(items),
        alert_count=alert_count,
    )


@app.route("/watchlist/add/<path:product_name>", methods=["POST"])
def add_to_watchlist_route(product_name):
    product_name = decode_product_name(product_name)
    if not product_exists(product_name):
        flash("Product not found.", "error")
        return redirect(url_for("dashboard"))

    if is_on_watchlist(product_name):
        flash(f"{product_name} is already on your watchlist.", "error")
    else:
        add_to_watchlist(product_name)
        flash(f"Added {product_name} to your watchlist.", "success")

    return redirect_back()


@app.route("/watchlist/remove/<path:product_name>", methods=["POST"])
def remove_from_watchlist_route(product_name):
    product_name = decode_product_name(product_name)
    if is_on_watchlist(product_name):
        remove_from_watchlist(product_name)
        flash(f"Removed {product_name} from your watchlist.", "success")
    else:
        flash("Product is not on your watchlist.", "error")

    return redirect_back()


@app.route("/upload", methods=["GET", "POST"])
def upload_product():
    if request.method == "POST":
        file = request.files.get("product_image")
        if not file or not file.filename:
            flash("Please select an image to upload.", "error")
            return render_template("upload.html")

        if not allowed_file(file.filename):
            flash("Invalid file type. Use PNG, JPG, GIF, or WebP.", "error")
            return render_template("upload.html")

        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            flash("Image must be 5 MB or smaller.", "error")
            return render_template("upload.html")

        upload_id, filename, original = save_upload(file)
        create_image_upload(upload_id, filename, original)
        result = analyze_product_image(filename)
        save_ai_analysis(upload_id, result)
        if result.get("identified"):
            flash("Product identified by AI. Review and confirm the name.", "success")
        elif result.get("error"):
            flash(f"AI detection unavailable: {result['error']}", "error")
        else:
            flash("Could not identify the product. Please enter the name manually.", "error")
        return redirect(url_for("confirm_upload", upload_id=upload_id))

    return render_template("upload.html")


@app.route("/upload/confirm/<upload_id>", methods=["GET", "POST"])
def confirm_upload(upload_id):
    upload = get_image_upload(upload_id)
    if not upload:
        flash("Upload not found.", "error")
        return redirect(url_for("upload_product"))

    if upload["confirmed"]:
        flash("This image was already confirmed.", "success")
        return redirect(url_for("add_product", product_name=upload["product_name"]))

    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        ai_result = ensure_ai_analysis(get_image_upload(upload_id))

        if not product_name:
            flash("Please enter a product name to continue.", "error")
            return render_confirm_upload(upload, product_name="", ai_result=ai_result)

        ai_detected_name = ai_result.get("product_name") if ai_result.get("identified") else None
        confirm_image_upload(upload_id, product_name, ai_detected_name)
        flash(f"Product photo saved for \"{product_name}\". Add store prices next.", "success")
        return redirect(url_for("add_product", product_name=product_name))

    return render_confirm_upload(upload)


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
            errors.append("Product name is required.")
        if not store_name:
            errors.append("Store name is required.")
        if not product_url:
            errors.append("Product URL is required.")

        price_errors, price, target_price = parse_price_fields(price_raw, target_raw)
        errors.extend(price_errors)

        if errors:
            for error in errors:
                flash(error, "error")
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

        add_price_entry(product_name, store_name, product_url, price, target_price)
        flash(f"Added price for {product_name} at {store_name}.", "success")
        return redirect(url_for("dashboard"))

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
        flash("Product not found.", "error")
        return redirect(url_for("dashboard"))

    entries = get_product_entries(product_name)
    target = get_product_target(product_name)
    product_image = get_product_image(product_name)
    image_preview = image_url(product_image["filename"]) if product_image else None

    if request.method == "POST":
        action = request.form.get("action", "save")

        if action == "delete_product":
            delete_product(product_name)
            flash(f"Deleted {product_name} and all store prices.", "success")
            return redirect(url_for("dashboard"))

        if action == "delete_entry":
            entry_id = request.form.get("entry_id")
            if entry_id:
                delete_entry(int(entry_id))
                remaining = get_product_entries(product_name)
                if not remaining:
                    flash(f"Deleted {product_name} — no store prices remaining.", "success")
                    return redirect(url_for("dashboard"))
                flash("Store entry removed.", "success")
            return redirect(url_for("edit_product", product_name=quote(product_name)))

        new_name = request.form.get("product_name", "").strip()
        target_raw = request.form.get("target_price", "").strip()

        errors = []
        if not new_name:
            errors.append("Product name is required.")

        _, _, target_price = parse_price_fields("", target_raw, require_price=False)

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            if new_name != product_name:
                if product_exists(new_name):
                    flash(f"A product named \"{new_name}\" already exists.", "error")
                    return redirect(url_for("edit_product", product_name=quote(product_name)))
                rename_product(product_name, new_name)
                product_name = new_name

            set_product_target(product_name, target_price)

            for entry in get_product_entries(product_name):
                entry_id = str(entry["id"])
                store_name = request.form.get(f"store_name_{entry_id}", "").strip()
                product_url = request.form.get(f"product_url_{entry_id}", "").strip()
                price_raw = request.form.get(f"price_{entry_id}", "").strip()

                if not store_name or not product_url or not price_raw:
                    continue

                entry_errors, price, _ = parse_price_fields(price_raw, "", require_price=True)
                if entry_errors:
                    for error in entry_errors:
                        flash(error, "error")
                    return redirect(url_for("edit_product", product_name=quote(product_name)))

                update_entry(entry["id"], store_name, product_url, price, target_price)

            new_store = request.form.get("new_store_name", "").strip()
            new_url = request.form.get("new_product_url", "").strip()
            new_price_raw = request.form.get("new_price", "").strip()
            if new_store and new_url and new_price_raw:
                entry_errors, new_price, _ = parse_price_fields(new_price_raw, "", require_price=True)
                if entry_errors:
                    for error in entry_errors:
                        flash(error, "error")
                else:
                    add_entry_to_product(product_name, new_store, new_url, new_price, target_price)

            flash(f"Updated {product_name}.", "success")
            return redirect(url_for("dashboard"))

        entries = get_product_entries(product_name)
        target = get_product_target(product_name)

    return render_template(
        "edit.html",
        product_name=product_name,
        entries=entries,
        target_price=target,
        image_preview=image_preview,
        on_watchlist=is_on_watchlist(product_name),
    )


@app.route("/product/<path:product_name>/delete", methods=["POST"])
def delete_product_route(product_name):
    product_name = decode_product_name(product_name)
    if not product_exists(product_name):
        flash("Product not found.", "error")
        return redirect(url_for("dashboard"))

    delete_product(product_name)
    flash(f"Deleted {product_name} and all store prices.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
