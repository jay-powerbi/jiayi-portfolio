import base64
import json
import os
import re
from pathlib import Path

UPLOAD_DIR = Path(__file__).parent / "static" / "uploads"

MIME_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
}

VISION_PROMPT = """Analyze this product image and identify the consumer product shown.

Return a JSON object with exactly these fields:
- "product_name": string or null — the specific product name (e.g. "Wireless Bluetooth Headphones")
- "brand": string or null — the brand name if visible or identifiable
- "model_number": string or null — model number or SKU if visible on the product or packaging
- "confidence": number from 0.0 to 1.0 — how confident you are in the identification
- "identified": boolean — true if you can reasonably identify the product, false if the image is unclear, not a product, or too ambiguous

Be concise. Use null for fields you cannot determine. Set identified to false and confidence below 0.4 if you cannot identify the product."""


def _empty_result(error=None):
    return {
        "identified": False,
        "product_name": None,
        "brand": None,
        "model_number": None,
        "confidence": None,
        "suggested_name": "",
        "error": error,
    }


def build_suggested_name(product_name, brand=None, model_number=None):
    if not product_name:
        return ""

    name = product_name.strip()
    parts = []

    if brand and brand.strip().lower() not in name.lower():
        parts.append(brand.strip())

    parts.append(name)

    if model_number and model_number.strip().lower() not in name.lower():
        parts.append(model_number.strip())

    return " ".join(parts)


def _parse_response_content(content):
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    data = json.loads(content)
    product_name = data.get("product_name") or None
    brand = data.get("brand") or None
    model_number = data.get("model_number") or None
    confidence = data.get("confidence")
    identified = bool(data.get("identified", False))

    if product_name:
        product_name = str(product_name).strip() or None
    if brand:
        brand = str(brand).strip() or None
    if model_number:
        model_number = str(model_number).strip() or None

    if confidence is not None:
        confidence = max(0.0, min(1.0, float(confidence)))

    if not identified or not product_name:
        identified = False
        suggested = ""
    else:
        suggested = build_suggested_name(product_name, brand, model_number)

    return {
        "identified": identified,
        "product_name": product_name,
        "brand": brand,
        "model_number": model_number,
        "confidence": confidence,
        "suggested_name": suggested,
        "error": None,
    }


def analyze_product_image(filename):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _empty_result("OpenAI API key not configured. Set OPENAI_API_KEY to enable AI detection.")

    path = UPLOAD_DIR / filename
    if not path.exists():
        return _empty_result("Image file not found.")

    ext = filename.rsplit(".", 1)[-1].lower()
    mime = MIME_TYPES.get(ext)
    if not mime:
        return _empty_result("Unsupported image format for analysis.")

    try:
        image_b64 = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    except OSError:
        return _empty_result("Could not read the uploaded image.")

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{image_b64}"},
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=300,
        )
        content = response.choices[0].message.content
        if not content:
            return _empty_result("AI returned an empty response.")
        return _parse_response_content(content)
    except json.JSONDecodeError:
        return _empty_result("Could not parse the AI response.")
    except Exception as exc:
        return _empty_result(f"AI analysis failed: {exc}")


def result_from_upload_row(upload):
    if not upload["ai_analyzed"]:
        return None

    product_name = upload["ai_detected_name"]
    brand = upload["ai_brand"]
    model_number = upload["ai_model_number"]
    confidence = upload["ai_confidence"]
    identified = bool(product_name and confidence is not None and confidence >= 0.4)

    return {
        "identified": identified,
        "product_name": product_name,
        "brand": brand,
        "model_number": model_number,
        "confidence": confidence,
        "suggested_name": build_suggested_name(product_name, brand, model_number) if product_name else "",
        "error": upload["ai_error"],
    }
