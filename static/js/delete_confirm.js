(function () {
    function confirmDelete(form) {
        var title = form.getAttribute("data-confirm-title") || "Delete this product?";
        var body = form.getAttribute("data-confirm-body") || "";
        var message = body ? title + "\n\n" + body : title;
        return window.confirm(message);
    }

    document.addEventListener("submit", function (event) {
        var form = event.target;
        if (!form || !form.classList.contains("js-delete-product-form")) {
            return;
        }
        if (!confirmDelete(form)) {
            event.preventDefault();
        }
    });
})();
