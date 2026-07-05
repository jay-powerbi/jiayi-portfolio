(function (global) {
    var STORAGE_KEY = 'pricepilot_recent_searches';
    var LEGACY_STORAGE_KEY = 'pricefinder_recent_searches';

    function migrateLegacyStorage() {
        if (localStorage.getItem(STORAGE_KEY)) return;
        var legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
        if (legacy) {
            localStorage.setItem(STORAGE_KEY, legacy);
        }
    }

    migrateLegacyStorage();
    var MAX_ITEMS = 8;

    function load() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            var list = raw ? JSON.parse(raw) : [];
            return Array.isArray(list) ? list : [];
        } catch (err) {
            return [];
        }
    }

    function save(list) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, MAX_ITEMS)));
    }

    function add(productName, extra) {
        if (!productName) return;
        var list = load().filter(function (item) {
            return item.productName !== productName;
        });
        list.unshift({
            productName: productName,
            ts: Date.now(),
            extra: extra || {},
        });
        save(list);
    }

    function render(container) {
        if (!container) return;
        var list = load();
        if (!list.length) {
            container.hidden = true;
            return;
        }
        container.hidden = false;
        var html = list.slice(0, 5).map(function (item) {
            var q = encodeURIComponent(item.productName);
            return (
                '<a class="home-recent-chip" href="/search/prices?product_name=' + q + '">' +
                '<span>' + escapeHtml(item.productName) + '</span>' +
                '</a>'
            );
        }).join('');
        container.innerHTML = html;
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    var api = { add: add, load: load, render: render };
    global.PricePilotRecent = api;

    document.addEventListener('DOMContentLoaded', function () {
        var page = document.querySelector('[data-track-search]');
        if (page) {
            add(page.getAttribute('data-track-search'));
        }
        render(document.getElementById('home-recent-searches'));
    });
}(window));
