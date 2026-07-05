(function () {
    function track(eventName, params) {
        var payload = params || {};
        if (typeof window.gtag === "function") {
            window.gtag("event", eventName, payload);
            return;
        }
        if (window.dataLayer) {
            window.dataLayer.push(Object.assign({ event: eventName }, payload));
        }
    }

    window.pfTrack = track;

    var projectMatch = window.location.pathname.match(/^\/portfolio\/projects\/([^/]+)/);
    if (projectMatch) {
        track("project_view", {
            project_slug: projectMatch[1],
            page_path: window.location.pathname,
            page_title: document.title,
        });
    }

    document.addEventListener("click", function (event) {
        var link = event.target.closest("a[href]");
        if (!link) return;

        var href = link.getAttribute("href") || "";
        var label = (link.getAttribute("aria-label") || link.textContent || "").trim().slice(0, 120);

        if (href.indexOf("/portfolio/resume") !== -1) {
            track("resume_download", {
                link_url: href,
                link_text: label,
                page_path: window.location.pathname,
            });
            return;
        }

        if (href.indexOf("github.com") !== -1) {
            track("github_click", {
                link_url: href,
                link_text: label,
                page_path: window.location.pathname,
            });
            return;
        }

        if (href.indexOf("linkedin.com") !== -1) {
            track("linkedin_click", {
                link_url: href,
                link_text: label,
                page_path: window.location.pathname,
            });
            return;
        }

        if (href.indexOf("mailto:") === 0) {
            track("contact_email_click", {
                link_url: href,
                page_path: window.location.pathname,
            });
        }
    });
})();
