(function () {
    "use strict";

    function filterVariants(form) {
        var product = form.querySelector('[name="product"]');
        var variant = form.querySelector('[name="variant"]');
        if (!product || !variant || variant.tagName !== "SELECT") return;

        var pid = product.value || "";
        var current = variant.value;
        var currentStillValid = false;

        Array.prototype.forEach.call(variant.options, function (opt) {
            if (!opt.value) {
                opt.hidden = false;
                opt.disabled = false;
                return;
            }
            var owner = opt.getAttribute("data-product");
            var show = pid !== "" && owner === pid;
            opt.hidden = !show;
            opt.disabled = !show;
            if (show && opt.value === current) currentStillValid = true;
        });

        if (!currentStillValid) variant.value = "";
    }

    function initIn(root) {
        if (!root.querySelectorAll) return;
        root.querySelectorAll('select[name="variant"]').forEach(function (variant) {
            var form = variant.closest("form");
            if (form) filterVariants(form);
        });
    }

    document.addEventListener("change", function (e) {
        if (e.target && e.target.matches && e.target.matches('[name="product"]')) {
            var form = e.target.closest("form");
            if (form) filterVariants(form);
        }
    });

    new MutationObserver(function (mutations) {
        mutations.forEach(function (m) {
            m.addedNodes.forEach(function (node) {
                if (node.nodeType === 1) initIn(node);
            });
        });
    }).observe(document.body, { childList: true, subtree: true });

    initIn(document);
})();
