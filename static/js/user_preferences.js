(function (global) {
    var STORAGE_KEY = 'pricepilot_user_prefs';
    var LEGACY_STORAGE_KEY = 'pricefinder_user_prefs';

    function migrateLegacyStorage() {
        if (localStorage.getItem(STORAGE_KEY)) return;
        var legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
        if (legacy) {
            localStorage.setItem(STORAGE_KEY, legacy);
        }
    }

    migrateLegacyStorage();

    function defaultAssistantPrefs() {
        return {
            alertMode: 'hybrid',
            productAlerts: true,
            storeAlerts: true,
            shoppingEventAlerts: true,
            deliveryAlerts: true,
            aiAlerts: false,
            preferredStores: [],
            trackedProducts: [],
            preferredZipCode: '',
            favoriteRetailers: [],
            hiddenRetailers: [],
            productAlertOptions: {
                priceDrops: true,
                targetPriceReached: true,
                backInStock: true,
            },
            storeAlertOptions: {
                weeklyDeals: true,
                newPromotions: true,
                clearanceDeals: true,
            },
            shoppingEventOptions: {
                primeDay: true,
                blackFriday: true,
                backToSchool: true,
                holidaySales: true,
            },
            deliveryOptions: {
                freeShippingOnly: false,
                pickupNearby: true,
                fastDelivery: true,
            },
            aiAlertOptions: {
                buyNow: false,
                wait: false,
            },
        };
    }

    function mergeOptions(defaults, raw) {
        var merged = {};
        Object.keys(defaults).forEach(function (key) {
            merged[key] = raw && typeof raw[key] === 'boolean' ? raw[key] : defaults[key];
        });
        return merged;
    }

    function normalizePrefs(raw) {
        var defaults = defaultAssistantPrefs();
        raw = raw && typeof raw === 'object' ? raw : {};

        return {
            alertMode: ['products', 'stores', 'hybrid'].indexOf(raw.alertMode) >= 0 ? raw.alertMode : defaults.alertMode,
            productAlerts: typeof raw.productAlerts === 'boolean' ? raw.productAlerts : defaults.productAlerts,
            storeAlerts: typeof raw.storeAlerts === 'boolean' ? raw.storeAlerts : defaults.storeAlerts,
            shoppingEventAlerts: typeof raw.shoppingEventAlerts === 'boolean' ? raw.shoppingEventAlerts : defaults.shoppingEventAlerts,
            deliveryAlerts: typeof raw.deliveryAlerts === 'boolean' ? raw.deliveryAlerts : defaults.deliveryAlerts,
            aiAlerts: typeof raw.aiAlerts === 'boolean' ? raw.aiAlerts : defaults.aiAlerts,
            preferredStores: Array.isArray(raw.preferredStores) ? raw.preferredStores.slice() : [],
            trackedProducts: Array.isArray(raw.trackedProducts) ? raw.trackedProducts.slice() : [],
            preferredZipCode: typeof raw.preferredZipCode === 'string' ? raw.preferredZipCode : '',
            favoriteRetailers: Array.isArray(raw.favoriteRetailers) ? raw.favoriteRetailers.slice() : [],
            hiddenRetailers: Array.isArray(raw.hiddenRetailers) ? raw.hiddenRetailers.slice() : [],
            productAlertOptions: mergeOptions(defaults.productAlertOptions, raw.productAlertOptions),
            storeAlertOptions: mergeOptions(defaults.storeAlertOptions, raw.storeAlertOptions),
            shoppingEventOptions: mergeOptions(defaults.shoppingEventOptions, raw.shoppingEventOptions),
            deliveryOptions: mergeOptions(defaults.deliveryOptions, raw.deliveryOptions),
            aiAlertOptions: mergeOptions(defaults.aiAlertOptions, raw.aiAlertOptions),
        };
    }

    function defaultPrefs() {
        return normalizePrefs({});
    }

    function loadPrefs() {
        try {
            var stored = localStorage.getItem(STORAGE_KEY);
            if (!stored) {
                return defaultPrefs();
            }
            return normalizePrefs(JSON.parse(stored));
        } catch (err) {
            return defaultPrefs();
        }
    }

    function savePrefs(prefs) {
        var payload = normalizePrefs(prefs);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
        return payload;
    }

    function isRetailerVisible(retailerId, prefs, filterIds) {
        if (!retailerId) {
            return true;
        }
        if (filterIds.indexOf(retailerId) === -1) {
            return true;
        }
        return prefs.hiddenRetailers.indexOf(retailerId) === -1;
    }

    var api = {
        STORAGE_KEY: STORAGE_KEY,
        defaultPrefs: defaultPrefs,
        defaultAssistantPrefs: defaultAssistantPrefs,
        loadPrefs: loadPrefs,
        savePrefs: savePrefs,
        normalizePrefs: normalizePrefs,
        isRetailerVisible: isRetailerVisible,
    };
    global.PricePilotPrefs = api;
}(window));
