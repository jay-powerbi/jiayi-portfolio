(function () {
    var Prefs = window.PricePilotPrefs;
    if (!Prefs) {
        return;
    }

    var form = document.getElementById('assistant-prefs-form');
    if (!form) {
        return;
    }

    var statusEl = document.getElementById('assistant-save-status');
    var sectionMap = {
        productAlerts: '.assistant-section--product',
        storeAlerts: '.assistant-section--store',
        shoppingEventAlerts: '.assistant-section--events',
        deliveryAlerts: '.assistant-section--delivery',
        aiAlerts: '.assistant-section--ai',
    };

    function setStatus(message, type) {
        if (!statusEl) {
            return;
        }
        statusEl.textContent = message;
        statusEl.className = 'assistant-save-status assistant-save-status--' + (type || 'info');
        statusEl.hidden = !message;
    }

    function setSectionEnabled(sectionKey, enabled) {
        var selector = sectionMap[sectionKey];
        if (!selector) {
            return;
        }
        var section = form.querySelector(selector);
        if (!section) {
            return;
        }
        section.classList.toggle('is-disabled', !enabled);
        section.querySelectorAll('input[type="checkbox"]').forEach(function (input) {
            if (input.name === sectionKey) {
                return;
            }
            input.disabled = !enabled;
        });
    }

    function applyAlertMode(mode) {
        form.querySelectorAll('[data-alert-mode]').forEach(function (btn) {
            var active = btn.getAttribute('data-alert-mode') === mode;
            btn.classList.toggle('is-active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });

        var productMaster = form.querySelector('input[name="productAlerts"]');
        var storeMaster = form.querySelector('input[name="storeAlerts"]');

        if (mode === 'products') {
            if (productMaster) {
                productMaster.disabled = false;
                productMaster.checked = true;
            }
            if (storeMaster) {
                storeMaster.disabled = true;
                storeMaster.checked = false;
            }
        } else if (mode === 'stores') {
            if (storeMaster) {
                storeMaster.disabled = false;
                storeMaster.checked = true;
            }
            if (productMaster) {
                productMaster.disabled = true;
                productMaster.checked = false;
            }
        } else {
            if (productMaster) {
                productMaster.disabled = false;
            }
            if (storeMaster) {
                storeMaster.disabled = false;
            }
        }

        setSectionEnabled('productAlerts', productMaster && productMaster.checked && !productMaster.disabled);
        setSectionEnabled('storeAlerts', storeMaster && storeMaster.checked && !storeMaster.disabled);
    }

    function readForm() {
        var prefs = Prefs.loadPrefs();
        var alertModeBtn = form.querySelector('[data-alert-mode].is-active');
        prefs.alertMode = alertModeBtn ? alertModeBtn.getAttribute('data-alert-mode') : prefs.alertMode;

        ['productAlerts', 'storeAlerts', 'shoppingEventAlerts', 'deliveryAlerts', 'aiAlerts'].forEach(function (key) {
            var input = form.querySelector('input[name="' + key + '"]');
            if (input) {
                prefs[key] = input.checked;
            }
        });

        Object.keys(prefs.productAlertOptions).forEach(function (key) {
            var input = form.querySelector('[name="productAlertOptions.' + key + '"]');
            if (input) {
                prefs.productAlertOptions[key] = input.checked;
            }
        });
        Object.keys(prefs.storeAlertOptions).forEach(function (key) {
            var input = form.querySelector('[name="storeAlertOptions.' + key + '"]');
            if (input) {
                prefs.storeAlertOptions[key] = input.checked;
            }
        });
        Object.keys(prefs.shoppingEventOptions).forEach(function (key) {
            var input = form.querySelector('[name="shoppingEventOptions.' + key + '"]');
            if (input) {
                prefs.shoppingEventOptions[key] = input.checked;
            }
        });
        Object.keys(prefs.deliveryOptions).forEach(function (key) {
            var input = form.querySelector('[name="deliveryOptions.' + key + '"]');
            if (input) {
                prefs.deliveryOptions[key] = input.checked;
            }
        });
        Object.keys(prefs.aiAlertOptions).forEach(function (key) {
            var input = form.querySelector('[name="aiAlertOptions.' + key + '"]');
            if (input) {
                prefs.aiAlertOptions[key] = input.checked;
            }
        });

        var zipInput = form.querySelector('[name="preferredZipCode"]');
        if (zipInput) {
            prefs.preferredZipCode = zipInput.value.replace(/\D/g, '').slice(0, 5);
        }

        return prefs;
    }

    function fillForm(prefs) {
        form.querySelectorAll('[data-alert-mode]').forEach(function (btn) {
            var active = btn.getAttribute('data-alert-mode') === prefs.alertMode;
            btn.classList.toggle('is-active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });

        ['productAlerts', 'storeAlerts', 'shoppingEventAlerts', 'deliveryAlerts', 'aiAlerts'].forEach(function (key) {
            var input = form.querySelector('input[name="' + key + '"]');
            if (input) {
                input.checked = !!prefs[key];
            }
        });

        Object.keys(prefs.productAlertOptions).forEach(function (key) {
            var input = form.querySelector('[name="productAlertOptions.' + key + '"]');
            if (input) {
                input.checked = !!prefs.productAlertOptions[key];
            }
        });
        Object.keys(prefs.storeAlertOptions).forEach(function (key) {
            var input = form.querySelector('[name="storeAlertOptions.' + key + '"]');
            if (input) {
                input.checked = !!prefs.storeAlertOptions[key];
            }
        });
        Object.keys(prefs.shoppingEventOptions).forEach(function (key) {
            var input = form.querySelector('[name="shoppingEventOptions.' + key + '"]');
            if (input) {
                input.checked = !!prefs.shoppingEventOptions[key];
            }
        });
        Object.keys(prefs.deliveryOptions).forEach(function (key) {
            var input = form.querySelector('[name="deliveryOptions.' + key + '"]');
            if (input) {
                input.checked = !!prefs.deliveryOptions[key];
            }
        });
        Object.keys(prefs.aiAlertOptions).forEach(function (key) {
            var input = form.querySelector('[name="aiAlertOptions.' + key + '"]');
            if (input) {
                input.checked = !!prefs.aiAlertOptions[key];
            }
        });

        var zipInput = form.querySelector('[name="preferredZipCode"]');
        if (zipInput && prefs.preferredZipCode) {
            zipInput.value = prefs.preferredZipCode;
        }

        applyAlertMode(prefs.alertMode);
        setSectionEnabled('productAlerts', prefs.productAlerts);
        setSectionEnabled('storeAlerts', prefs.storeAlerts);
        setSectionEnabled('shoppingEventAlerts', prefs.shoppingEventAlerts);
        setSectionEnabled('deliveryAlerts', prefs.deliveryAlerts);
        setSectionEnabled('aiAlerts', prefs.aiAlerts);
    }

    function syncZipFromPage() {
        var zipInput = form.querySelector('[name="preferredZipCode"]');
        if (!zipInput || zipInput.value) {
            return;
        }
        var label = document.querySelector('.zip-saved-label');
        if (!label) {
            return;
        }
        var match = (label.textContent || '').match(/\b(\d{5})\b/);
        if (match) {
            zipInput.value = match[1];
        }
    }

    fillForm(Prefs.loadPrefs());
    syncZipFromPage();

    form.querySelector('.assistant-mode-switch') && form.querySelector('.assistant-mode-switch').addEventListener('click', function (event) {
        var btn = event.target.closest('[data-alert-mode]');
        if (!btn) {
            return;
        }
        applyAlertMode(btn.getAttribute('data-alert-mode'));
    });

    ['productAlerts', 'storeAlerts', 'shoppingEventAlerts', 'deliveryAlerts', 'aiAlerts'].forEach(function (key) {
        var input = form.querySelector('input[name="' + key + '"]');
        if (!input) {
            return;
        }
        input.addEventListener('change', function () {
            setSectionEnabled(key, input.checked);
        });
    });

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        var saved = Prefs.savePrefs(readForm());
        setStatus(form.getAttribute('data-saved-message') || 'Preferences saved.', 'success');
        fillForm(saved);
    });

    form.addEventListener('reset', function () {
        window.setTimeout(function () {
            fillForm(Prefs.defaultPrefs());
            setStatus('', 'info');
        }, 0);
    });
}());
