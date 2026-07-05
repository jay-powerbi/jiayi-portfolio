(function () {
    var Prefs = window.PricePilotPrefs;
    if (!Prefs) {
        return;
    }

    function parseFilterIds(root) {
        var raw = (root && root.getAttribute('data-filter-ids')) || '';
        return raw.split(',').map(function (id) {
            return id.trim();
        }).filter(Boolean);
    }

    function syncPreferredZip(prefs) {
        var zipMatch = document.querySelector('.zip-saved-label');
        if (zipMatch) {
            var text = zipMatch.textContent || '';
            var found = text.match(/\b(\d{5})\b/);
            if (found) {
                prefs.preferredZipCode = found[1];
            }
        }
        return prefs;
    }

    function setChipState(chip, active) {
        chip.classList.toggle('is-active', active);
        chip.setAttribute('aria-pressed', active ? 'true' : 'false');
    }

    function updateHiddenFromChips(root, prefs, filterIds) {
        prefs.hiddenRetailers = filterIds.filter(function (id) {
            var chip = root.querySelector('[data-retailer-id="' + id + '"]');
            return chip && !chip.classList.contains('is-active');
        });
        return syncPreferredZip(prefs);
    }

    function applyFilter(root, prefs, filterIds) {
        var scope = document.querySelector('[data-retailer-filter-scope]') || document;
        var items = scope.querySelectorAll('[data-retailer-filter-item]');
        var visibleCount = 0;

        items.forEach(function (item) {
            var retailerId = item.getAttribute('data-retailer-id') || '';
            var show = Prefs.isRetailerVisible(retailerId, prefs, filterIds);
            item.hidden = !show;
            item.classList.toggle('is-retailer-filtered-out', !show);
            if (show) {
                visibleCount += 1;
            }
        });

        var emptyEl = root.querySelector('[data-retailer-filter-empty]');
        if (emptyEl) {
            emptyEl.hidden = visibleCount > 0;
        }

        if (scope.querySelector('.retailer-cards')) {
            recalcBestDeal(scope);
        }

        var countEl = root.querySelector('[data-retailer-filter-count]');
        if (countEl) {
            var active = filterIds.length - prefs.hiddenRetailers.length;
            countEl.textContent = active + ' / ' + filterIds.length;
        }
    }

    function recalcBestDeal(scope) {
        var cards = scope.querySelectorAll('.retailer-card');
        cards.forEach(function (card) {
            card.classList.remove('retailer-card--best');
            var badge = card.querySelector('.retailer-best-badge');
            if (badge) {
                badge.remove();
            }
        });

        var candidates = [];
        cards.forEach(function (card) {
            if (card.hidden || card.classList.contains('is-retailer-filtered-out')) {
                return;
            }
            if (card.getAttribute('data-abnormal') === 'true') {
                return;
            }
            candidates.push(card);
        });

        if (!candidates.length) {
            return;
        }

        candidates.sort(function (a, b) {
            var totalA = parseFloat(a.getAttribute('data-total') || '0');
            var totalB = parseFloat(b.getAttribute('data-total') || '0');
            if (totalA !== totalB) {
                return totalA - totalB;
            }
            var directA = a.getAttribute('data-seller-type') === 'direct' ? 0 : 1;
            var directB = b.getAttribute('data-seller-type') === 'direct' ? 0 : 1;
            return directA - directB;
        });

        var best = candidates[0];
        best.classList.add('retailer-card--best');
        var label = best.getAttribute('data-best-deal-label') || 'Best Deal';
        var badgeEl = document.createElement('span');
        badgeEl.className = 'retailer-best-badge';
        badgeEl.textContent = '🏆 ' + label;
        best.insertBefore(badgeEl, best.firstChild);
    }

    function initPanel(root) {
        var filterIds = parseFilterIds(root);
        if (!filterIds.length) {
            return;
        }

        var prefs = Prefs.loadPrefs();

        filterIds.forEach(function (id) {
            var chip = root.querySelector('[data-retailer-id="' + id + '"]');
            if (!chip) {
                return;
            }
            var active = prefs.hiddenRetailers.indexOf(id) === -1;
            setChipState(chip, active);
        });

        applyFilter(root, prefs, filterIds);

        root.addEventListener('click', function (event) {
            var chip = event.target.closest('[data-retailer-id]');
            if (chip && root.contains(chip)) {
                var active = !chip.classList.contains('is-active');
                setChipState(chip, active);
                prefs = Prefs.savePrefs(updateHiddenFromChips(root, prefs, filterIds));
                applyFilter(root, prefs, filterIds);
                return;
            }

            var actionBtn = event.target.closest('[data-filter-action]');
            if (!actionBtn || !root.contains(actionBtn)) {
                return;
            }

            var action = actionBtn.getAttribute('data-filter-action');
            filterIds.forEach(function (id) {
                var chipEl = root.querySelector('[data-retailer-id="' + id + '"]');
                if (!chipEl) {
                    return;
                }
                setChipState(chipEl, action === 'select-all');
            });
            prefs = Prefs.savePrefs(updateHiddenFromChips(root, prefs, filterIds));
            applyFilter(root, prefs, filterIds);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-retailer-filter]').forEach(initPanel);
    });
}());
