(function () {
    var STORAGE_KEY = 'pricepilot_theme';
    var root = document.documentElement;
    var btn = document.getElementById('theme-toggle');

    function applyTheme(theme) {
        if (theme === 'dark') {
            root.setAttribute('data-theme', 'dark');
        } else {
            root.removeAttribute('data-theme');
        }
    }

    function toggleTheme() {
        var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        localStorage.setItem(STORAGE_KEY, next);
        applyTheme(next);
    }

    applyTheme(localStorage.getItem(STORAGE_KEY));

    if (btn) {
        btn.addEventListener('click', toggleTheme);
    }
})();
