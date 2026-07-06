"""SEO helpers for the Jiayi Shi portfolio (sitemap, robots, page metadata)."""

from __future__ import annotations

import os
from xml.sax.saxutils import escape

from portfolio_data import PORTFOLIO_LINKS, PORTFOLIO_PROJECTS

PORTFOLIO_SITE_URL = os.environ.get(
    "PORTFOLIO_SITE_URL", "https://jiayi-portfolio.onrender.com"
).rstrip("/")

PORTFOLIO_BRAND_TITLE = "Jiayi Shi | Senior Power BI Developer Portfolio"
DEFAULT_TITLE = PORTFOLIO_BRAND_TITLE
DEFAULT_DESCRIPTION = (
    "Senior Power BI Developer based in New York specializing in Power BI, SQL, Python, DAX, "
    "data visualization, dashboard development, business intelligence, and analytics. "
    "View portfolio projects, GitHub, and professional experience."
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
    json_ld: dict | list | None = None,
) -> dict:
    desc = (description or DEFAULT_DESCRIPTION).strip()
    image_path = image or DEFAULT_OG_IMAGE
    context = {
        "seo_title": title.strip(),
        "seo_site_name": PORTFOLIO_BRAND_TITLE,
        "seo_description": desc,
        "seo_path": path if path.startswith("/") else f"/{path}",
        "seo_canonical": absolute_url(path),
        "seo_image": absolute_url(f"/static/{image_path.lstrip('/')}" if not image_path.startswith("http") else image_path),
        "seo_og_type": og_type,
        "seo_noindex": noindex,
        "portfolio_site_url": PORTFOLIO_SITE_URL,
    }
    if json_ld is not None:
        context["seo_json_ld"] = json_ld
    return context


def portfolio_home_json_ld() -> dict:
    same_as = [
        url
        for url in (
            PORTFOLIO_LINKS.get("linkedin"),
            PORTFOLIO_LINKS.get("github"),
        )
        if url
    ]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": PORTFOLIO_BRAND_TITLE,
                "url": absolute_url("/portfolio"),
                "description": DEFAULT_DESCRIPTION,
            },
            {
                "@type": "Person",
                "name": "Jiayi Shi",
                "jobTitle": "Senior Power BI Developer",
                "url": absolute_url("/portfolio"),
                "sameAs": same_as,
            },
        ],
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
