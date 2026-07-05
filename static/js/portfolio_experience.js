(function () {
    var list = document.querySelector(".pf-exp-list");
    if (!list) return;

    var tabs = Array.prototype.slice.call(list.querySelectorAll(".pf-exp-item"));
    var panels = Array.prototype.slice.call(document.querySelectorAll(".pf-exp-panel"));

    function activate(id) {
        tabs.forEach(function (tab) {
            var isActive = tab.getAttribute("data-exp-id") === id;
            tab.classList.toggle("is-active", isActive);
            tab.setAttribute("aria-selected", isActive ? "true" : "false");
        });

        panels.forEach(function (panel) {
            var isActive = panel.id === "exp-panel-" + id;
            panel.classList.toggle("is-active", isActive);
            panel.hidden = !isActive;
        });
    }

    list.addEventListener("click", function (event) {
        var tab = event.target.closest(".pf-exp-item");
        if (!tab || !list.contains(tab)) return;
        activate(tab.getAttribute("data-exp-id"));
    });

    list.addEventListener("keydown", function (event) {
        var currentIndex = tabs.findIndex(function (tab) {
            return tab.classList.contains("is-active");
        });
        if (currentIndex < 0) return;

        var nextIndex = currentIndex;
        if (event.key === "ArrowDown" || event.key === "ArrowRight") {
            nextIndex = (currentIndex + 1) % tabs.length;
        } else if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
            nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
        } else {
            return;
        }

        event.preventDefault();
        tabs[nextIndex].focus();
        activate(tabs[nextIndex].getAttribute("data-exp-id"));
    });
})();
