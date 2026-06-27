import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

UPLOAD_DIR = Path(__file__).parent / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
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


def image_url(filename):
    return f"/static/uploads/{filename}"


def delete_image_file(filename):
    if not filename:
        return
    path = UPLOAD_DIR / filename
    if path.exists():
        path.unlink()
