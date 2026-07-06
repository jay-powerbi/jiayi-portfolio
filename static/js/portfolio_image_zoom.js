(function () {
    document.querySelectorAll(".pf-magnifier-lens, .pf-img-zoom-wrap .pf-magnifier-lens").forEach((el) => el.remove());
    document.querySelectorAll(".pf-img-zoom-wrap").forEach((wrap) => {
        const img = wrap.querySelector("img");
        if (img) {
            wrap.replaceWith(img);
        }
    });

    const MIN_SCALE = 1;
    const MAX_SCALE = 3;
    const ZOOM_STEP = 0.35;

    let lightbox;
    let stage;
    let lightboxImg;
    let galleryImages = [];
    let galleryIndex = 0;
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
            '    <span class="pf-zoom-gallery-count" data-zoom-gallery-count hidden></span>',
            '    <button type="button" class="pf-zoom-tool pf-zoom-close-btn" data-zoom-close aria-label="Close zoom view">',
            '      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"></path></svg>',
            "    </button>",
            "  </div>",
            '  <div class="pf-zoom-stage-wrap">',
            '    <button type="button" class="pf-zoom-nav pf-zoom-nav-prev" data-zoom-prev aria-label="Previous dashboard screenshot">',
            '      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6 6 6"></path></svg>',
            "    </button>",
            '    <div class="pf-zoom-stage" data-zoom-stage>',
            '      <img class="pf-zoom-img" alt="">',
            "    </div>",
            '    <button type="button" class="pf-zoom-nav pf-zoom-nav-next" data-zoom-next aria-label="Next dashboard screenshot">',
            '      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"></path></svg>',
            "    </button>",
            "  </div>",
            '  <p class="pf-zoom-hint">Use arrow keys or buttons to browse · Scroll to zoom · Drag to pan · Esc to close</p>',
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
        lightbox.querySelector("[data-zoom-prev]").addEventListener("click", () => goGallery(-1));
        lightbox.querySelector("[data-zoom-next]").addEventListener("click", () => goGallery(1));

        stage.addEventListener("wheel", onWheel, { passive: false });
        stage.addEventListener("pointerdown", onPointerDown);
        stage.addEventListener("pointermove", onPointerMove);
        stage.addEventListener("pointerup", onPointerUp);
        stage.addEventListener("pointercancel", onPointerUp);
        stage.addEventListener("pointerleave", onPointerUp);

        document.addEventListener("keydown", onKeyDown, true);
    }

    function onKeyDown(event) {
        if (!lightbox || lightbox.hidden) {
            return;
        }

        if (event.key === "Escape") {
            event.stopPropagation();
            closeLightbox();
            return;
        }

        if (galleryImages.length <= 1) {
            return;
        }

        if (event.key === "ArrowLeft") {
            event.preventDefault();
            event.stopPropagation();
            goGallery(-1);
        } else if (event.key === "ArrowRight") {
            event.preventDefault();
            event.stopPropagation();
            goGallery(1);
        }
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

    function updateGalleryUI() {
        const hasGallery = galleryImages.length > 1;
        const counter = lightbox.querySelector("[data-zoom-gallery-count]");
        const prevBtn = lightbox.querySelector("[data-zoom-prev]");
        const nextBtn = lightbox.querySelector("[data-zoom-next]");

        counter.hidden = !hasGallery;
        prevBtn.hidden = !hasGallery;
        nextBtn.hidden = !hasGallery;

        if (hasGallery) {
            counter.textContent = `${galleryIndex + 1} / ${galleryImages.length}`;
        }
    }

    function syncCarouselSlide() {
        const img = galleryImages[galleryIndex];
        if (!img) {
            return;
        }

        const carousel = img.closest("[data-carousel]");
        if (!carousel) {
            return;
        }

        const slides = Array.from(carousel.querySelectorAll(".pf-cs-carousel-slide"));
        const dots = Array.from(carousel.querySelectorAll("[data-carousel-dot]"));
        const counter = carousel.querySelector("[data-carousel-current]");
        const slideIndex = slides.findIndex((slide) => slide.contains(img));

        if (slideIndex < 0) {
            return;
        }

        slides.forEach((slide, index) => {
            slide.classList.toggle("is-active", index === slideIndex);
        });
        dots.forEach((dot, index) => {
            const isActive = index === slideIndex;
            dot.classList.toggle("is-active", isActive);
            dot.setAttribute("aria-selected", isActive ? "true" : "false");
        });
        if (counter) {
            counter.textContent = String(slideIndex + 1);
        }
    }

    function showImageAt(index) {
        const img = galleryImages[index];
        if (!img) {
            return;
        }

        galleryIndex = index;
        resetView();
        lightboxImg.src = img.currentSrc || img.src;
        lightboxImg.alt = img.alt || "Dashboard zoom view";
        updateGalleryUI();
        syncCarouselSlide();
    }

    function goGallery(delta) {
        if (galleryImages.length <= 1) {
            return;
        }
        const nextIndex = (galleryIndex + delta + galleryImages.length) % galleryImages.length;
        showImageAt(nextIndex);
    }

    function openLightbox(img, images) {
        if (!lightbox) {
            createLightbox();
        }

        galleryImages = images && images.length ? images : [img];
        galleryIndex = Math.max(0, galleryImages.indexOf(img));

        showImageAt(galleryIndex);
        lightbox.hidden = false;
        document.body.classList.add("pf-zoom-open");

        if (typeof window.pfTrack === "function") {
            window.pfTrack("dashboard_zoom_open", {
                image_src: lightboxImg.src,
                gallery_index: galleryIndex + 1,
                gallery_total: galleryImages.length,
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
        galleryImages = [];
        galleryIndex = 0;
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

    function initZoomButtons() {
        document.querySelectorAll("[data-carousel-zoom]").forEach((btn) => {
            btn.addEventListener("click", (event) => {
                event.stopPropagation();
                const carousel = btn.closest("[data-carousel]");
                if (!carousel) {
                    return;
                }

                const images = Array.from(carousel.querySelectorAll(".pf-cs-carousel-slide img"));
                const active = carousel.querySelector(".pf-cs-carousel-slide.is-active img") || images[0];
                if (active) {
                    openLightbox(active, images);
                }
            });
        });
    }

    initZoomButtons();
})();
