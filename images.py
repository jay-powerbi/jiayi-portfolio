import hashlib
import uuid
from pathlib import Path
from urllib.parse import quote

from werkzeug.utils import secure_filename

UPLOAD_DIR = Path(__file__).parent / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_storage):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    original = secure_filename(file_storage.filename or "upload.jpg")
    ext = original.rsplit(".", 1)[1].lower()
    upload_id = str(uuid.uuid4())
    filename = f"{upload_id}.{ext}"
    path = UPLOAD_DIR / filename

    file_storage.save(path)
    return upload_id, filename, original


def _placeholder_svg(product_name):
    digest = hashlib.md5(product_name.encode("utf-8")).hexdigest()
    hue = int(digest[:6], 16) % 360
    accent = (hue + 28) % 360
    label = (product_name.strip()[:2] or "?").upper()
    safe_name = product_name.replace('"', "'")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160" role="img" aria-label="{safe_name}">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="hsl({hue}, 62%, 52%)"/>
      <stop offset="100%" stop-color="hsl({accent}, 68%, 38%)"/>
    </linearGradient>
  </defs>
  <rect width="160" height="160" rx="18" fill="url(#g)"/>
  <rect x="18" y="18" width="124" height="124" rx="14" fill="rgba(255,255,255,0.12)"/>
  <text x="80" y="92" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-size="42" font-weight="700" fill="rgba(255,255,255,0.95)">{label}</text>
</svg>"""


def placeholder_image_data_uri(product_name):
    return f"data:image/svg+xml,{quote(_placeholder_svg(product_name))}"


def resolve_product_image_url(product_name, filename=None):
    if filename:
        return image_url(filename)
    if product_name:
        return placeholder_image_data_uri(product_name)
    return None


def save_placeholder_image(product_name):
    """Create a deterministic product thumbnail for demos and empty states."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_id = str(uuid.uuid4())
    filename = f"{upload_id}.svg"
    path = UPLOAD_DIR / filename
    path.write_text(_placeholder_svg(product_name), encoding="utf-8")
    return upload_id, filename


def image_url(filename):
    return f"/static/uploads/{filename}"


def delete_image_file(filename):
    if not filename:
        return
    path = UPLOAD_DIR / filename
    if path.exists():
        path.unlink()

