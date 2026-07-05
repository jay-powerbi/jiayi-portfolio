# Price Pilot

> **Price Pilot** — compare total delivered prices across stores, track a personal watchlist, and identify products from photos — built with **Python**, **SQLite**, and **Google Gemini Vision**.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat&logo=sqlite&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?style=flat&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

---

## Highlights

| | |
|---|---|
| **Compare total delivered price** | Log the price that actually matters — item + shipping — and surface the lowest option per product |
| **Watchlist tracking** | Star products and monitor target price, lowest price, store, and alert status in one place |
| **AI product recognition** | Upload a photo; Google Gemini Vision suggests name, brand, and model for review |
| **Deal alerts** | Set a target price and get an instant **Alert** badge when the lowest price hits your goal |

---

## Screenshots

<table>
  <tr>
    <td align="center"><strong>Landing Page</strong><br><img src="docs/screenshots/landing.png" width="420" alt="Landing page"></td>
    <td align="center"><strong>Dashboard</strong><br><img src="docs/screenshots/dashboard.png" width="420" alt="Dashboard"></td>
  </tr>
  <tr>
    <td align="center"><strong>Watchlist</strong><br><img src="docs/screenshots/watchlist.png" width="420" alt="Watchlist"></td>
    <td align="center"><strong>AI Photo Upload</strong><br><img src="docs/screenshots/upload.png" width="420" alt="Upload photo"></td>
  </tr>
</table>

<details>
<summary>More screenshots</summary>

**Add Comparison** — enter product, store, URL, price, and optional target alert.

![Add Comparison](docs/screenshots/add-comparison.png)

**Edit Product** — manage all store prices and target alerts from one page.

![Edit Product](docs/screenshots/edit-product.png)

</details>

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3, Flask |
| **Database** | SQLite |
| **Frontend** | HTML5, CSS3, Jinja2 |
| **AI** | Google Gemini Vision API (`gemini-2.0-flash`) |
| **Architecture** | Server-rendered Flask app |

**Dependencies:** Flask · Google GenAI SDK · Werkzeug · Jinja2

---

## How to Run

### Prerequisites

- Python 3.10+
- pip

### 1. Clone & install

```bash
git clone https://github.com/your-username/ai-price-comparison-app.git
cd ai-price-comparison-app
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment (optional)

```bash
cp .env.example .env
```

Edit `.env` and set `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) to enable AI photo recognition. Without it, the app still works — users enter product names manually.

> **Security:** `.env` is gitignored. Never commit API keys. Use `.env.example` as the template only.

### 3. Start the app

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

### 4. Optional — seed demo data

```bash
python scripts/seed_demo.py
```

SQLite creates `prices.db` automatically on first run. No manual database setup required.

---

## Demo Workflow

**Photo-first flow (recommended):**

1. **Upload a product photo** from the dashboard or **Upload Photo** nav.
2. **Review AI detection** — confirm the name or tap a suggestion chip (e.g. Samsung Galaxy Watch).
3. **Choose model details** — series, storage, size, connectivity, and condition (when applicable).
4. **Auto Price Search** — sample prices from major retailers; enter a ZIP code to refresh delivered totals.
5. **Track the best deal** with one tap, or use **Add price manually** as a fallback.
6. **Star a product** on the dashboard to add it to your **Watchlist** with Buy Now links and deal alerts.

**Manual comparison flow:**

1. Go to **Add Comparison** and enter store prices (include shipping for true delivered cost).
2. **Add the same product from another store** with a different price.
3. **Set a target price** — the dashboard shows **Alert** when the lowest price meets your goal.
4. **Search & sort** on the dashboard to find deals quickly.

### Example

| Step | Product | Store | Price (incl. shipping) |
|------|---------|-------|------------------------|
| 1 | Wireless Mouse | Amazon | $24.99 |
| 2 | Wireless Mouse | Walmart | $19.99 |
| 3 | Wireless Mouse | Target | $22.50 |

**Result:** Lowest delivered price **$19.99** at **Walmart** · **$5.00** savings vs. highest store.

---

## Resume / LinkedIn Bullets

Copy-paste ready:

- Built an **AI-powered price comparison web app** with Python, Flask, and SQLite that groups multi-store prices and surfaces the lowest option per product.
- Integrated **Google Gemini Vision** to identify products from uploaded images and auto-suggest name, brand, and model before user confirmation.
- Implemented a **watchlist system** with target-price alerts, dashboard analytics, search/sort, and SQLite-backed contact message storage.
- Designed a **SaaS-style UI** with landing page, dashboard, photo upload flow, and responsive product management (edit, delete, multi-store entries).

**One-liner for profiles:**

> AI-Powered Price Comparison App — Built a Python + SQLite application that compares product prices, tracks watchlist items, stores user contact messages, and uses Google Gemini Vision to identify product information from uploaded images.

---

## Project Structure

```
├── app.py                  # Flask routes
├── database.py             # SQLite schema & queries
├── vision.py               # Google Gemini Vision integration
├── price_search.py         # Mock auto price search (MVP)
├── price_validation.py     # Price bands, trust scores, abnormal detection
├── pickup_locations.py     # Mock in-store pickup locations
├── shopping_intelligence.py # Dashboard deals, events & AI recommendations
├── product_variants.py     # Model/variant selection before search
├── product_suggestions.py  # Generic product name suggestions
├── images.py               # Image upload helpers
├── scripts/seed_demo.py    # Demo data seeder
├── docs/screenshots/       # README screenshots
├── static/css/             # App & landing styles
├── static/uploads/         # Product images (gitignored contents)
└── templates/              # Jinja2 HTML templates
```

---

## Future Improvements

Planned for later — not in scope for this MVP:

- [ ] **Real retailer API / search integration** — replace mock price search with live Amazon, Walmart, Best Buy, Target, eBay, and brand-store APIs
- [ ] **ZIP-code-aware delivered price** — accurate shipping and tax by location
- [ ] **Nearby pickup locations** — real store inventory, live pickup availability, estimated pickup time, and reserve-pickup via retailer APIs
- [ ] **In-store vs online price comparison** — compare local shelf prices with online delivered totals
- [ ] **Shopping intelligence** — historical event discount %, buy-now vs wait AI, watchlist items likely to drop during upcoming sales
- [ ] **Savings tracking dashboard** — historical savings, best-time-to-buy insights, and price-drop alerts
- [ ] Email / push notifications when target prices are reached
- [ ] User accounts & authentication
- [ ] Payment / subscription system
- [ ] Production deployment (Docker, cloud hosting)
- [ ] Price history charts
- [ ] REST API & CSV import/export
- [ ] Automated tests (pytest)

---

## License

MIT — see [LICENSE](LICENSE).
