(function () {
    const MIN_SCALE = 1;
    const MAX_SCALE = 3;
    const ZOOM_STEP = 0.35;
    const LENS_SIZE = 140;
    const LENS_ZOOM = 2.5;
    const isTouch = window.matchMedia("(hover: none), (pointer: coarse)").matches;

    let lightbox;
    let stage;
    let lightboxImg;
    let scale = 1;
    let panX = 0;
    let panY = 0;
    let dragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let panStartX = 0;
    let panStartY = 0;

    function createLightbox() {
        lightbox = document.createElement("div");
        lightbox.className = "pf-zoom-lightbox";
        lightbox.hidden = true;
        lightbox.innerHTML = [
            '<div class="pf-zoom-backdrop" data-zoom-close></div>',
            '<div class="pf-zoom-dialog" role="dialog" aria-modal="true" aria-label="Dashboard zoom view">',
            '  <div class="pf-zoom-toolbar">',
            '    <button type="button" class="pf-zoom-tool" data-zoom-out aria-label="Zoom out">−</button>',
            '    <button type="button" class="pf-zoom-tool pf-zoom-reset" data-zoom-reset aria-label="Reset zoom">100%</button>',
            '    <button type="button" class="pf-zoom-tool" data-zoom-in aria-label="Zoom in">+</button>',
            '    <button type="button" class="pf-zoom-tool pf-zoom-close-btn" data-zoom-close aria-label="Close zoom view">',
            '      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"></path></svg>',
            "    </button>",
            "  </div>",
            '  <div class="pf-zoom-stage" data-zoom-stage>',
            '    <img class="pf-zoom-img" alt="">',
            "  </div>",
            '  <p class="pf-zoom-hint">Scroll or pinch to zoom · Drag to pan · Esc to close</p>',
            "</div>",
        ].join("");
        document.body.appendChild(lightbox);

        stage = lightbox.querySelector("[data-zoom-stage]");
        lightboxImg = lightbox.querySelector(".pf-zoom-img");

        lightbox.querySelectorAll("[data-zoom-close]").forEach((el) => {
            el.addEventListener("click", closeLightbox);
        });
        lightbox.querySelector("[data-zoom-in]").addEventListener("click", () => setScale(scale + ZOOM_STEP));
        lightbox.querySelector("[data-zoom-out]").addEventListener("click", () => setScale(scale - ZOOM_STEP));
        lightbox.querySelector("[data-zoom-reset]").addEventListener("click", () => resetView());

        stage.addEventListener("wheel", onWheel, { passive: false });
        stage.addEventListener("pointerdown", onPointerDown);
        stage.addEventListener("pointermove", onPointerMove);
        stage.addEventListener("pointerup", onPointerUp);
        stage.addEventListener("pointercancel", onPointerUp);
        stage.addEventListener("pointerleave", onPointerUp);

        document.addEventListener("keydown", (event) => {
            if (!lightbox.hidden && event.key === "Escape") {
                closeLightbox();
            }
        });
    }

    function resetView() {
        scale = 1;
        panX = 0;
        panY = 0;
        applyTransform();
        updateResetLabel();
    }

    function setScale(nextScale, anchorX, anchorY) {
        const prev = scale;
        scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, nextScale));

        if (anchorX != null && anchorY != null && prev !== scale) {
            const ratio = scale / prev - 1;
            panX -= (anchorX - stage.clientWidth / 2 - panX) * ratio;
            panY -= (anchorY - stage.clientHeight / 2 - panY) * ratio;
        }

        applyTransform();
        updateResetLabel();
    }

    function applyTransform() {
        lightboxImg.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
        stage.classList.toggle("is-pannable", scale > 1);
    }

    function updateResetLabel() {
        const btn = lightbox.querySelector("[data-zoom-reset]");
        if (btn) {
            btn.textContent = `${Math.round(scale * 100)}%`;
        }
    }

    function openLightbox(img) {
        if (!lightbox) {
            createLightbox();
        }

        resetView();
        lightboxImg.src = img.currentSrc || img.src;
        lightboxImg.alt = img.alt || "Dashboard zoom view";
        lightbox.hidden = false;
        document.body.classList.add("pf-zoom-open");

        if (typeof window.pfTrack === "function") {
            window.pfTrack("dashboard_zoom_open", {
                image_src: lightboxImg.src,
                page_path: window.location.pathname,
            });
        }
    }

    function closeLightbox() {
        if (!lightbox || lightbox.hidden) {
            return;
        }
        lightbox.hidden = true;
        document.body.classList.remove("pf-zoom-open");
        lightboxImg.removeAttribute("src");
        resetView();
    }

    function onWheel(event) {
        event.preventDefault();
        const rect = stage.getBoundingClientRect();
        setScale(scale + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP), event.clientX - rect.left, event.clientY - rect.top);
    }

    function onPointerDown(event) {
        if (scale <= 1 || event.button !== 0) {
            return;
        }
        dragging = true;
        dragStartX = event.clientX;
        dragStartY = event.clientY;
        panStartX = panX;
        panStartY = panY;
        stage.setPointerCapture(event.pointerId);
        stage.classList.add("is-dragging");
    }

    function onPointerMove(event) {
        if (!dragging) {
            return;
        }
        panX = panStartX + (event.clientX - dragStartX);
        panY = panStartY + (event.clientY - dragStartY);
        applyTransform();
    }

    function onPointerUp(event) {
        if (!dragging) {
            return;
        }
        dragging = false;
        stage.classList.remove("is-dragging");
        if (stage.hasPointerCapture(event.pointerId)) {
            stage.releasePointerCapture(event.pointerId);
        }
    }

    function wrapZoomableImage(img) {
        if (img.closest(".pf-img-zoom-wrap")) {
            return img.closest(".pf-img-zoom-wrap");
        }

        const wrap = document.createElement("div");
        wrap.className = "pf-img-zoom-wrap";
        img.parentNode.insertBefore(wrap, img);
        wrap.appendChild(img);
        return wrap;
    }

    function initMagnifier(wrap, img) {
        const lens = document.createElement("div");
        lens.className = "pf-magnifier-lens";
        lens.hidden = true;
        lens.setAttribute("aria-hidden", "true");
        wrap.appendChild(lens);

        function updateLens(event) {
            const rect = img.getBoundingClientRect();
            const wrapRect = wrap.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;

            if (x < 0 || y < 0 || x > rect.width || y > rect.height) {
                lens.hidden = true;
                return;
            }

            lens.hidden = false;
            const src = img.currentSrc || img.src;
            lens.style.backgroundImage = `url("${src}")`;
            lens.style.backgroundSize = `${rect.width * LENS_ZOOM}px ${rect.height * LENS_ZOOM}px`;

            let left = x - LENS_SIZE / 2;
            let top = y - LENS_SIZE / 2;
            left = Math.max(0, Math.min(left, rect.width - LENS_SIZE));
            top = Math.max(0, Math.min(top, rect.height - LENS_SIZE));

            lens.style.width = `${LENS_SIZE}px`;
            lens.style.height = `${LENS_SIZE}px`;
            lens.style.left = `${left + (rect.left - wrapRect.left)}px`;
            lens.style.top = `${top + (rect.top - wrapRect.top)}px`;
            lens.style.backgroundPosition = `${-(x * LENS_ZOOM - LENS_SIZE / 2)}px ${-(y * LENS_ZOOM - LENS_SIZE / 2)}px`;
        }

        wrap.addEventListener("mouseenter", () => {
            lens.hidden = false;
        });
        wrap.addEventListener("mouseleave", () => {
            lens.hidden = true;
        });
        wrap.addEventListener("mousemove", updateLens);
    }

    function bindImage(img) {
        const wrap = wrapZoomableImage(img);
        img.classList.add("pf-zoomable-img");

        img.addEventListener("click", () => openLightbox(img));
        wrap.setAttribute("role", "button");
        wrap.setAttribute("tabindex", "0");
        wrap.setAttribute("aria-label", "Click to zoom dashboard image");
        wrap.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openLightbox(img);
            }
        });

        if (!isTouch) {
            initMagnifier(wrap, img);
        }
    }

    function initCarouselZoomButtons() {
        document.querySelectorAll("[data-carousel]").forEach((carousel) => {
            if (carousel.querySelector("[data-carousel-zoom]")) {
                return;
            }

            const controls = carousel.querySelector(".pf-cs-carousel-controls");
            if (!controls) {
                return;
            }

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "pf-cs-carousel-btn pf-cs-carousel-zoom-btn";
            btn.setAttribute("data-carousel-zoom", "");
            btn.setAttribute("aria-label", "Zoom current dashboard view");
            btn.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6"></circle><path d="M16 16l5 5"></path><path d="M11 8v6M8 11h6"></path></svg>';

            const nextBtn = carousel.querySelector("[data-carousel-next]");
            controls.insertBefore(btn, nextBtn);

            btn.addEventListener("click", () => {
                const active = carousel.querySelector(".pf-cs-carousel-slide.is-active img");
                if (active) {
                    openLightbox(active);
                }
            });
        });
    }

    document.querySelectorAll(".pf-cs-carousel-slide img, .pf-cs-hero-visual img").forEach(bindImage);
    initCarouselZoomButtons();
})();
