"""SEO helpers for the Jiayi Shi portfolio (sitemap, robots, page metadata)."""

from __future__ import annotations

import os
from xml.sax.saxutils import escape

from portfolio_data import PORTFOLIO_PROJECTS

PORTFOLIO_SITE_URL = os.environ.get(
    "PORTFOLIO_SITE_URL", "https://jiayi-portfolio.onrender.com"
).rstrip("/")

DEFAULT_TITLE = "Jiayi Shi - Senior BI Developer Portfolio"
DEFAULT_DESCRIPTION = (
    "Portfolio of Jiayi Shi, Senior Business Intelligence Developer specializing in "
    "Power BI, DAX, SQL, and executive dashboards across finance, retail, insurance, "
    "real estate, and transportation."
)
DEFAULT_OG_IMAGE = "images/projects/profile-photo.png"

STATIC_PAGES = [
    ("/portfolio", "weekly", "1.0"),
    ("/portfolio/about", "monthly", "0.8"),
    ("/portfolio/contact", "monthly", "0.8"),
    ("/portfolio/opportunities", "weekly", "0.9"),
]

ROBOTS_DISALLOW = [
    "/portfolio/feedback-admin",
    "/dashboard",
    "/alerts",
    "/scan",
    "/compare",
    "/watchlist",
    "/upload",
    "/search",
    "/add",
    "/product",
    "/products",
    "/profile",
    "/settings",
    "/design-system",
    "/contact",
    "/lang",
]


def absolute_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{PORTFOLIO_SITE_URL}{path}"


def seo_context(
    *,
    title: str,
    description: str | None = None,
    path: str,
    image: str | None = None,
    og_type: str = "website",
    noindex: bool = False,
) -> dict:
    desc = (description or DEFAULT_DESCRIPTION).strip()
    image_path = image or DEFAULT_OG_IMAGE
    return {
        "seo_title": title.strip(),
        "seo_description": desc,
        "seo_path": path if path.startswith("/") else f"/{path}",
        "seo_canonical": absolute_url(path),
        "seo_image": absolute_url(f"/static/{image_path.lstrip('/')}" if not image_path.startswith("http") else image_path),
        "seo_og_type": og_type,
        "seo_noindex": noindex,
        "portfolio_site_url": PORTFOLIO_SITE_URL,
    }


def sitemap_urls() -> list[dict[str, str]]:
    urls: list[dict[str, str]] = []
    for path, changefreq, priority in STATIC_PAGES:
        urls.append(
            {
                "loc": absolute_url(path),
                "changefreq": changefreq,
                "priority": priority,
            }
        )
    for project in PORTFOLIO_PROJECTS:
        urls.append(
            {
                "loc": absolute_url(f"/portfolio/projects/{project['slug']}"),
                "changefreq": "monthly",
                "priority": "0.85",
            }
        )
    return urls


def render_sitemap() -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for entry in sitemap_urls():
        lines.extend(
            [
                "  <url>",
                f"    <loc>{escape(entry['loc'])}</loc>",
                f"    <changefreq>{entry['changefreq']}</changefreq>",
                f"    <priority>{entry['priority']}</priority>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def render_robots() -> str:
    lines = ["User-agent: *"]
    for path in ROBOTS_DISALLOW:
        lines.append(f"Disallow: {path}")
    lines.append("")
    lines.append(f"Sitemap: {absolute_url('/sitemap.xml')}")
    return "\n".join(lines) + "\n"
