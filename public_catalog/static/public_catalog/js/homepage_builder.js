(function () {
    "use strict";

    var root = document.querySelector("[data-hpb]");
    if (!root) return;

    var form = root.querySelector("[data-hpb-form]");
    var frame = root.querySelector("[data-hpb-frame]");
    var statusEl = root.querySelector("[data-hpb-status]");
    var canEdit = root.dataset.canEdit === "1";
    var saveUrl = root.dataset.saveUrl;
    var previewUrl = root.dataset.previewUrl;
    var clearFlags = {};

    function csrf() {
        var m = document.querySelector('meta[name="csrf-token"]');
        return m ? m.getAttribute("content") : "";
    }
    function status(msg, kind) {
        if (!statusEl) return;
        statusEl.textContent = msg || "";
        statusEl.className = "hpb__status" + (kind ? " is-" + kind : "");
    }
    function reloadPreview() {
        if (frame) frame.src = previewUrl + "&t=" + Date.now();
    }

    function sectionsJson() {
        var out = [];
        root.querySelectorAll("[data-section-key]").forEach(function (row) {
            var toggle = row.querySelector("[data-section-enabled]");
            out.push({ key: row.dataset.sectionKey, enabled: !!(toggle && toggle.checked) });
        });
        return JSON.stringify(out);
    }

    function collect() {
        var fd = new FormData();
        form.querySelectorAll("[name]").forEach(function (el) {
            var name = el.getAttribute("name");
            if (el.type === "file") return;
            if (el.type === "checkbox") { fd.append(name, el.checked ? "1" : "0"); return; }
            if (el.type === "radio") { if (el.checked) fd.append(name, el.value); return; }
            fd.append(name, el.value);
        });
        // Accent: honour the "theme default" state.
        var accentEnabled = form.querySelector("[data-accent-enabled]");
        if (accentEnabled && accentEnabled.value === "0") fd.set("accent", "");
        // Files (only when freshly picked).
        var heroInput = form.querySelector("[data-hero-input]");
        if (heroInput && heroInput.files && heroInput.files[0]) fd.append("hero_image", heroInput.files[0]);
        var storyInput = form.querySelector("[data-story-input]");
        if (storyInput && storyInput.files && storyInput.files[0]) fd.append("story_image", storyInput.files[0]);
        Object.keys(clearFlags).forEach(function (k) { if (clearFlags[k]) fd.append("clear_" + k, "1"); });
        fd.append("sections", sectionsJson());
        return fd;
    }

    var timer = null;
    function scheduleSave() {
        if (!canEdit) return;
        status(root.dataset.savingMsg, "saving");
        clearTimeout(timer);
        timer = setTimeout(save, 450);
    }
    function save() {
        fetch(saveUrl, { method: "POST", headers: { "X-CSRFToken": csrf() }, body: collect() })
            .then(function (r) { if (!r.ok) throw new Error("save"); return r.json(); })
            .then(function () {
                clearFlags = {};
                var hi = form.querySelector("[data-hero-input]"); if (hi) hi.value = "";
                var si = form.querySelector("[data-story-input]"); if (si) si.value = "";
                status(root.dataset.savedMsg, "ok");
                reloadPreview();
            })
            .catch(function () { status(root.dataset.errorMsg, "error"); });
    }

    if (!canEdit) {
        form.querySelectorAll("input, textarea, select, button").forEach(function (el) { el.disabled = true; });
    }

    // Any edit -> autosave.
    form.addEventListener("input", scheduleSave);
    form.addEventListener("change", scheduleSave);

    // Overlay live readout.
    var overlay = form.querySelector("[data-overlay]");
    var overlayOut = form.querySelector("[data-overlay-out]");
    if (overlay && overlayOut) overlay.addEventListener("input", function () { overlayOut.textContent = overlay.value; });

    // Hero media -> show custom image field only for "custom".
    form.querySelectorAll('input[name="hero_media"]').forEach(function (radio) {
        radio.addEventListener("change", function () {
            var field = form.querySelector("[data-hero-image-field]");
            if (field) field.hidden = form.querySelector('input[name="hero_media"]:checked').value !== "custom";
        });
    });

    // Image pick previews.
    function wireImage(inputSel, previewSel, key) {
        var input = form.querySelector(inputSel);
        var preview = form.querySelector(previewSel);
        if (!input) return;
        input.addEventListener("change", function () {
            var file = input.files && input.files[0];
            if (file && preview) { preview.innerHTML = '<img src="' + URL.createObjectURL(file) + '" alt="">'; }
            clearFlags[key] = false;
            var clr = form.querySelector('[data-clear="' + key + '"]');
            if (clr) clr.hidden = false;
        });
    }
    wireImage("[data-hero-input]", "[data-hero-preview]", "hero_image");
    wireImage("[data-story-input]", "[data-story-preview]", "story_image");

    form.querySelectorAll("[data-clear]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            var key = btn.dataset.clear;
            clearFlags[key] = true;
            var input = form.querySelector('[data-' + (key === "hero_image" ? "hero" : "story") + '-input]');
            if (input) input.value = "";
            var preview = form.querySelector('[data-' + (key === "hero_image" ? "hero" : "story") + '-preview]');
            if (preview) preview.innerHTML = '<i class="bi bi-image"></i>';
            btn.hidden = true;
            scheduleSave();
        });
    });

    // Section reorder (up/down — no native drag).
    root.addEventListener("click", function (e) {
        var mv = e.target.closest("[data-move]");
        if (!mv || !canEdit) return;
        var row = mv.closest("[data-section-key]");
        var container = row.parentElement;
        if (mv.dataset.move === "up" && row.previousElementSibling) {
            container.insertBefore(row, row.previousElementSibling);
        } else if (mv.dataset.move === "down" && row.nextElementSibling) {
            container.insertBefore(row.nextElementSibling, row);
        }
        scheduleSave();
    });

    // Accent presets + reset.
    var accentInput = form.querySelector("[data-accent-input]");
    var accentEnabled = form.querySelector("[data-accent-enabled]");
    root.querySelectorAll("[data-accent]").forEach(function (sw) {
        sw.addEventListener("click", function () {
            if (accentInput) accentInput.value = sw.dataset.accent;
            if (accentEnabled) accentEnabled.value = "1";
            scheduleSave();
        });
    });
    if (accentInput) accentInput.addEventListener("input", function () { if (accentEnabled) accentEnabled.value = "1"; });
    var accentReset = root.querySelector("[data-accent-reset]");
    if (accentReset) accentReset.addEventListener("click", function () {
        if (accentEnabled) accentEnabled.value = "0";
        scheduleSave();
    });

    // Preview controls.
    var frameWrap = root.querySelector("[data-frame-wrap]");
    root.querySelectorAll("[data-viewport]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            root.querySelectorAll("[data-viewport]").forEach(function (b) { b.classList.remove("is-active"); });
            btn.classList.add("is-active");
            if (frameWrap) frameWrap.classList.toggle("is-mobile", btn.dataset.viewport === "mobile");
        });
    });
    var refresh = root.querySelector("[data-hpb-refresh]");
    if (refresh) refresh.addEventListener("click", reloadPreview);
})();
