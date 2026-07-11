(function () {
    "use strict";

    var DEFAULT_NS = "switch_pos.products_layout";

    document.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-products-layout-option]");
        if (!btn) return;
        e.preventDefault();

        if (btn.getAttribute("aria-pressed") === "true" || btn.classList.contains("btn-primary")) {
            return;
        }

        var value = btn.getAttribute("data-products-layout-option");
        var group = btn.closest("[data-products-layout-switch]");
        var ns = (group && group.getAttribute("data-products-layout-ns")) || DEFAULT_NS;

        if (group) {
            group.querySelectorAll("[data-products-layout-option]").forEach(function (b) {
                b.disabled = true;
            });
        }

        function reload() { window.location.reload(); }

        if (typeof window.updateAppPreference === "function") {
            window.updateAppPreference(ns, value).then(reload, reload);
        } else {
            reload();
        }
    });
})();
