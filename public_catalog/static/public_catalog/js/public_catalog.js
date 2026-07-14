(function () {
    "use strict";

    document.addEventListener("click", function (event) {
        var trigger = event.target.closest("[data-dynamic-modal]");
        if (!trigger) return;
        var modal = document.getElementById("universalDynamicModal");
        var dialog = modal ? modal.querySelector(".modal-dialog") : null;
        if (!dialog) return;
        var fullscreen = trigger.getAttribute("data-public-modal-size") === "fullscreen";
        dialog.classList.toggle("modal-fullscreen", fullscreen);
        dialog.classList.toggle("modal-dialog-centered", !fullscreen);
    }, true);

    document.addEventListener("hidden.bs.modal", function (event) {
        if (!event.target || event.target.id !== "universalDynamicModal") return;
        var dialog = event.target.querySelector(".modal-dialog");
        if (!dialog) return;
        dialog.classList.remove("modal-fullscreen");
        dialog.classList.add("modal-dialog-centered");
    });

    // Hero carousel: cross-fade featured images with dot navigation + autoplay.
    function initHeroCarousel(hero) {
        var slides = Array.prototype.slice.call(hero.querySelectorAll(".public-hero__slide"));
        var dots = Array.prototype.slice.call(hero.querySelectorAll("[data-hero-dots] button"));
        if (slides.length < 2) return;
        var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        var motion = hero.getAttribute("data-motion-level") || "subtle";
        var autoplay = motion !== "none" && !reducedMotion;
        var intervalMs = motion === "lively" ? 4200 : 5500;
        var index = 0;
        var timer = null;

        function show(next) {
            index = (next + slides.length) % slides.length;
            slides.forEach(function (s, i) { s.classList.toggle("is-active", i === index); });
            dots.forEach(function (d, i) { d.classList.toggle("is-active", i === index); });
        }
        function start() {
            stop();
            if (!autoplay) return;
            timer = setInterval(function () { show(index + 1); }, intervalMs);
        }
        function stop() { if (timer) { clearInterval(timer); timer = null; } }

        dots.forEach(function (dot, i) {
            dot.addEventListener("click", function () { show(i); start(); });
        });
        hero.addEventListener("mouseenter", stop);
        hero.addEventListener("mouseleave", start);
        start();
    }

    function initCarousels(root) {
        (root || document).querySelectorAll("[data-hero-carousel]").forEach(initHeroCarousel);
    }
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { initCarousels(document); });
    } else {
        initCarousels(document);
    }
})();
