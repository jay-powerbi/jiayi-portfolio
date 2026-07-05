(function () {
    function initCarousel(root) {
        const slides = Array.from(root.querySelectorAll(".pf-cs-carousel-slide"));
        const dots = Array.from(root.querySelectorAll("[data-carousel-dot]"));
        const prevBtn = root.querySelector("[data-carousel-prev]");
        const nextBtn = root.querySelector("[data-carousel-next]");
        const counter = root.querySelector("[data-carousel-current]");

        if (!slides.length) {
            return;
        }

        let index = slides.findIndex((slide) => slide.classList.contains("is-active"));
        if (index < 0) {
            index = 0;
        }

        function goTo(nextIndex) {
            index = (nextIndex + slides.length) % slides.length;

            slides.forEach((slide, slideIndex) => {
                slide.classList.toggle("is-active", slideIndex === index);
            });

            dots.forEach((dot, dotIndex) => {
                const isActive = dotIndex === index;
                dot.classList.toggle("is-active", isActive);
                dot.setAttribute("aria-selected", isActive ? "true" : "false");
            });

            if (counter) {
                counter.textContent = String(index + 1);
            }
        }

        prevBtn?.addEventListener("click", () => goTo(index - 1));
        nextBtn?.addEventListener("click", () => goTo(index + 1));

        dots.forEach((dot, dotIndex) => {
            dot.addEventListener("click", () => goTo(dotIndex));
        });

        root.addEventListener("keydown", (event) => {
            if (event.key === "ArrowLeft") {
                goTo(index - 1);
            } else if (event.key === "ArrowRight") {
                goTo(index + 1);
            }
        });
    }

    document.querySelectorAll("[data-carousel]").forEach(initCarousel);
})();
