(function () {
    var FEEDBACK_DELAY_MS = 180000;
    var OWNER_KEY = "jiayi_portfolio_owner";
    var DONE_KEY = "jiayi_portfolio_feedback_done";
    var DISMISSED_KEY = "jiayi_portfolio_feedback_dismissed";
    var startedAt = Date.now();
    var liked = "";

    var params = new URLSearchParams(window.location.search);
    if (params.get("owner") === "1" || params.get("preview") === "owner") {
        localStorage.setItem(OWNER_KEY, "1");
    }

    if (localStorage.getItem(OWNER_KEY) === "1" || localStorage.getItem(DONE_KEY) === "1" || sessionStorage.getItem(DISMISSED_KEY) === "1") {
        return;
    }

    function getModal() {
        return document.getElementById("pf-feedback-modal");
    }

    function openModal() {
        var modal = getModal();
        if (!modal) return;
        modal.hidden = false;
        document.body.classList.add("pf-feedback-open");
    }

    function closeModal(markDismissed) {
        var modal = getModal();
        if (!modal) return;
        modal.hidden = true;
        document.body.classList.remove("pf-feedback-open");
        if (markDismissed) {
            sessionStorage.setItem(DISMISSED_KEY, "1");
        }
    }

    function setStatus(message) {
        var status = document.getElementById("pf-feedback-status");
        if (status) status.textContent = message;
    }

    function setLiked(value, button) {
        liked = value;
        document.querySelectorAll("[data-feedback-liked]").forEach(function (btn) {
            btn.classList.toggle("active", btn === button);
        });
    }

    function submitFeedback() {
        var messageEl = document.getElementById("pf-feedback-message");
        var submit = document.getElementById("pf-feedback-submit");
        var message = messageEl ? messageEl.value.trim() : "";

        if (!liked && !message) {
            setStatus("Please choose an option or write a short comment.");
            return;
        }

        if (submit) submit.disabled = true;
        setStatus("Sending...");

        fetch("/portfolio/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                liked: liked,
                message: message,
                page: window.location.pathname,
                time_on_page_seconds: Math.round((Date.now() - startedAt) / 1000)
            })
        })
            .then(function (response) {
                if (!response.ok) throw new Error("Feedback request failed");
                localStorage.setItem(DONE_KEY, "1");
                if (typeof window.pfTrack === "function") {
                    window.pfTrack("feedback_submit", {
                        liked: liked || "not_selected",
                        page_path: window.location.pathname,
                        has_message: message ? "yes" : "no",
                    });
                }
                setStatus("Thank you. Your feedback was saved.");
                window.setTimeout(function () {
                    closeModal(false);
                }, 900);
            })
            .catch(function () {
                setStatus("Sorry, feedback could not be sent. Please try again.");
                if (submit) submit.disabled = false;
            });
    }

    document.addEventListener("click", function (event) {
        var closeTarget = event.target.closest("[data-feedback-close]");
        if (closeTarget) {
            closeModal(true);
            return;
        }

        var likedButton = event.target.closest("[data-feedback-liked]");
        if (likedButton) {
            setLiked(likedButton.getAttribute("data-feedback-liked"), likedButton);
            return;
        }

        if (event.target && event.target.id === "pf-feedback-submit") {
            submitFeedback();
        }
    });

    window.setTimeout(openModal, FEEDBACK_DELAY_MS);
})();
