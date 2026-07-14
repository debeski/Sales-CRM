(function () {
    "use strict";

    var root = document.querySelector("[data-shop-builder]");
    if (!root) return;

    var canEdit = root.dataset.canEdit === "1";
    var URLS = {
        toggle: root.dataset.toggleUrl,
        update: root.dataset.updateUrl,
        reorder: root.dataset.reorderUrl,
        settings: root.dataset.settingsUrl,
    };

    function csrf() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    function toast(msg) {
        if (msg && typeof window.showToast === "function") window.showToast(msg);
    }

    function post(url, body, isForm) {
        var headers = { "X-CSRFToken": csrf() };
        if (!isForm) headers["Content-Type"] = "application/json";
        return fetch(url, {
            method: "POST",
            headers: headers,
            body: isForm ? body : JSON.stringify(body),
        }).then(function (r) {
            if (!r.ok) throw new Error("request-failed");
            return r.json();
        });
    }

    function formOf(fields) {
        var fd = new FormData();
        Object.keys(fields).forEach(function (k) {
            if (fields[k] !== undefined && fields[k] !== null) fd.append(k, fields[k]);
        });
        return fd;
    }

    function cardKey(card) {
        var lid = card.dataset.listingId;
        return lid
            ? { listing_id: lid }
            : { kind: card.dataset.kind, id: card.dataset.sourceId };
    }

    // ---- stats ------------------------------------------------------------
    function recomputeStats() {
        var cards = root.querySelectorAll("[data-card]");
        var published = 0, featured = 0, available = 0;
        cards.forEach(function (c) {
            if (c.dataset.published === "1") {
                published++;
                if (c.dataset.featured === "1") featured++;
                if (c.dataset.available === "1") available++;
            }
        });
        setStat("published", published);
        setStat("featured", featured);
        setStat("available", available);
    }
    function setStat(name, value) {
        var el = root.querySelector('[data-stat="' + name + '"]');
        if (el) el.textContent = value;
    }

    // ---- card sync from server listing json --------------------------------
    function applyListing(card, listing) {
        card.dataset.listingId = listing.id || "";
        card.dataset.published = listing.is_published ? "1" : "0";
        card.dataset.featured = listing.is_featured ? "1" : "0";
        card.dataset.available = listing.availability_code !== "unavailable" ? "1" : "0";
        card.dataset.sort = listing.sort_order;
        card.dataset.title = listing.public_title || "";
        card.dataset.summary = listing.public_summary || "";
        card.dataset.body = listing.public_body || "";
        card.dataset.installation = listing.installation_notes || "";
        card.dataset.warranty = listing.warranty_notes || "";
        card.dataset.showPrice = listing.show_price ? "1" : "0";
        card.dataset.showAvailability = listing.show_availability ? "1" : "0";
        card.dataset.showWhenUnavailable = listing.show_when_unavailable ? "1" : "0";
        card.dataset.image = listing.image_url || "";
        card.dataset.search = (listing.display_title || "").toLowerCase();

        card.classList.toggle("is-published", !!listing.is_published);
        card.classList.toggle("is-featured", !!listing.is_featured);

        var publishToggle = card.querySelector("[data-publish-toggle]");
        if (publishToggle) publishToggle.checked = !!listing.is_published;
        var publishLabel = card.querySelector("[data-publish-label]");
        if (publishLabel) publishLabel.textContent = listing.is_published ? root.dataset.txtPublished : root.dataset.txtPublish;

        var star = card.querySelector("[data-feature-toggle] i");
        if (star) star.className = "bi " + (listing.is_featured ? "bi-star-fill" : "bi-star");

        var titleEl = card.querySelector("[data-card-title]");
        if (titleEl) titleEl.textContent = listing.display_title;

        var img = card.querySelector("[data-card-image]");
        if (img) setCardImage(card, listing.image_url);

        var link = card.querySelector("[data-public-link]");
        if (link) {
            link.href = listing.public_url || "";
            link.hidden = !(listing.is_published && listing.public_url);
        }
        recomputeStats();
    }

    function setCardImage(card, url) {
        var media = card.querySelector(".scb-card__media");
        var current = card.querySelector("[data-card-image]");
        if (url) {
            if (current && current.tagName === "IMG") {
                current.src = url;
            } else if (current) {
                var img = document.createElement("img");
                img.setAttribute("data-card-image", "");
                img.setAttribute("draggable", "false");
                img.src = url;
                img.alt = card.dataset.name || "";
                current.replaceWith(img);
            }
        }
    }

    // ---- publish toggle ----------------------------------------------------
    root.addEventListener("change", function (e) {
        var toggle = e.target.closest ? e.target.closest("[data-publish-toggle]") : null;
        if (!toggle || !canEdit) return;
        var card = toggle.closest("[data-card]");
        toggle.disabled = true;
        post(URLS.toggle, formOf(cardKey(card)), true)
            .then(function (data) {
                applyListing(card, data.listing);
                toast(root.dataset.savedMsg);
            })
            .catch(function () {
                toggle.checked = !toggle.checked;
                toast(root.dataset.errorMsg);
            })
            .then(function () { toggle.disabled = false; });
    });

    // ---- feature toggle ----------------------------------------------------
    root.addEventListener("click", function (e) {
        var btn = e.target.closest ? e.target.closest("[data-feature-toggle]") : null;
        if (!btn || !canEdit) return;
        var card = toggleFeature(btn.closest("[data-card]"));
        if (!card) return;
    });

    function toggleFeature(card) {
        if (card.dataset.published !== "1") {
            toast(root.dataset.errorMsg);
            return null;
        }
        var next = card.dataset.featured === "1" ? "0" : "1";
        var fields = cardKey(card);
        fields.is_featured = next;
        post(URLS.update, formOf(fields), true)
            .then(function (data) { applyListing(card, data.listing); toast(root.dataset.savedMsg); })
            .catch(function () { toast(root.dataset.errorMsg); });
        return card;
    }

    // ---- customize modal ---------------------------------------------------
    var modal = document.querySelector("[data-customize-modal]");
    var modalForm = modal ? modal.querySelector("[data-customize-form]") : null;
    var activeCard = null;

    function openModal(card) {
        if (!modal) return;
        activeCard = card;
        setVal("title", card.dataset.title);
        setVal("summary", card.dataset.summary);
        setVal("body", card.dataset.body);
        setVal("installation", card.dataset.installation);
        setVal("warranty", card.dataset.warranty);
        setVal("sort", card.dataset.sort);
        setCheck("show_price", card.dataset.showPrice === "1");
        setCheck("show_availability", card.dataset.showAvailability === "1");
        setCheck("show_when_unavailable", card.dataset.showWhenUnavailable === "1");
        var input = modalForm.querySelector("[data-image-input]");
        if (input) input.value = "";
        renderPreview(card.dataset.image);
        modal.hidden = false;
        document.body.classList.add("scb-modal-open");
    }
    function closeModal() {
        if (!modal) return;
        modal.hidden = true;
        activeCard = null;
        document.body.classList.remove("scb-modal-open");
    }
    function setVal(field, value) {
        var el = modalForm.querySelector('[data-field="' + field + '"]');
        if (el) el.value = value || "";
    }
    function setCheck(name, on) {
        var el = modalForm.querySelector('[data-field="' + name + '"]');
        if (el) el.checked = !!on;
    }
    function renderPreview(url) {
        var preview = modalForm.querySelector("[data-image-preview]");
        var clear = modalForm.querySelector("[data-image-clear]");
        if (!preview) return;
        if (url) {
            preview.innerHTML = '<img src="' + url + '" alt="">';
            if (clear) clear.hidden = false;
        } else {
            preview.innerHTML = '<i class="bi bi-image"></i>';
            if (clear) clear.hidden = true;
        }
    }

    root.addEventListener("click", function (e) {
        var btn = e.target.closest ? e.target.closest("[data-customize]") : null;
        if (btn && canEdit) openModal(btn.closest("[data-card]"));
    });

    if (modal) {
        modal.addEventListener("click", function (e) {
            if (e.target.closest("[data-modal-close]")) closeModal();
        });
        var imgInput = modalForm.querySelector("[data-image-input]");
        if (imgInput) imgInput.addEventListener("change", function () {
            var file = imgInput.files && imgInput.files[0];
            if (file) renderPreview(URL.createObjectURL(file));
        });
        var clearBtn = modalForm.querySelector("[data-image-clear]");
        if (clearBtn) clearBtn.addEventListener("click", function () {
            modalForm.dataset.clearImage = "1";
            if (imgInput) imgInput.value = "";
            renderPreview("");
        });
        modalForm.addEventListener("submit", function (e) {
            e.preventDefault();
            if (!activeCard) return;
            var fields = cardKey(activeCard);
            fields.public_title = getVal("title");
            fields.public_summary = getVal("summary");
            fields.public_body = getVal("body");
            fields.installation_notes = getVal("installation");
            fields.warranty_notes = getVal("warranty");
            fields.sort_order = getVal("sort");
            fields.show_price = getCheck("show_price") ? "1" : "0";
            fields.show_availability = getCheck("show_availability") ? "1" : "0";
            fields.show_when_unavailable = getCheck("show_when_unavailable") ? "1" : "0";
            var fd = formOf(fields);
            var file = imgInput && imgInput.files && imgInput.files[0];
            if (file) fd.append("image_override", file);
            if (modalForm.dataset.clearImage === "1") fd.append("clear_image", "1");
            var saveBtn = modalForm.querySelector("[data-modal-save]");
            if (saveBtn) saveBtn.disabled = true;
            post(URLS.update, fd, true)
                .then(function (data) {
                    applyListing(activeCard, data.listing);
                    delete modalForm.dataset.clearImage;
                    toast(root.dataset.savedMsg);
                    closeModal();
                })
                .catch(function () { toast(root.dataset.errorMsg); })
                .then(function () { if (saveBtn) saveBtn.disabled = false; });
        });
    }
    function getVal(field) {
        var el = modalForm.querySelector('[data-field="' + field + '"]');
        return el ? el.value : "";
    }
    function getCheck(name) {
        var el = modalForm.querySelector('[data-field="' + name + '"]');
        return el ? el.checked : false;
    }
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && modal && !modal.hidden) closeModal();
    });

    // ---- storefront toggle -------------------------------------------------
    var storefront = root.querySelector("[data-storefront-toggle]");
    if (storefront && canEdit) {
        storefront.addEventListener("change", function () {
            storefront.disabled = true;
            post(URLS.settings, formOf({ shop_enabled: storefront.checked ? "1" : "0" }), true)
                .then(function (data) {
                    var label = root.querySelector("[data-storefront-label]");
                    if (label) label.textContent = data.config.shop_enabled ? root.dataset.txtLive : root.dataset.txtOffline;
                    toast(root.dataset.savedMsg);
                })
                .catch(function () {
                    storefront.checked = !storefront.checked;
                    toast(root.dataset.errorMsg);
                })
                .then(function () { storefront.disabled = false; });
        });
    }

    // ---- search + filters --------------------------------------------------
    var search = root.querySelector("[data-builder-search]");
    var grid = root.querySelector("[data-builder-grid]");
    var emptyMsg = root.querySelector("[data-builder-empty]");
    var activeFilter = "all";

    function applyFilters() {
        if (!grid) return;
        var q = (search && search.value || "").toLowerCase().trim();
        var visible = 0;
        grid.querySelectorAll("[data-card]").forEach(function (card) {
            var matchQ = !q || (card.dataset.search || "").indexOf(q) !== -1 || (card.dataset.name || "").toLowerCase().indexOf(q) !== -1;
            var matchF = true;
            if (activeFilter === "products") matchF = card.dataset.kind === "product";
            else if (activeFilter === "services") matchF = card.dataset.kind === "service";
            else if (activeFilter === "published") matchF = card.dataset.published === "1";
            else if (activeFilter === "unpublished") matchF = card.dataset.published !== "1";
            var show = matchQ && matchF;
            card.hidden = !show;
            if (show) visible++;
        });
        if (emptyMsg) emptyMsg.hidden = visible !== 0;
    }

    if (search) search.addEventListener("input", applyFilters);
    root.querySelectorAll("[data-filter]").forEach(function (chip) {
        chip.addEventListener("click", function () {
            root.querySelectorAll("[data-filter]").forEach(function (c) { c.classList.remove("is-active"); });
            chip.classList.add("is-active");
            activeFilter = chip.dataset.filter;
            applyFilters();
        });
    });

    // ---- drag reorder (published cards) ------------------------------------
    if (canEdit && grid) {
        var dragCard = null;
        var orderBefore = "";

        function publishedIds() {
            var ids = [];
            grid.querySelectorAll('[data-card][data-published="1"]').forEach(function (c) {
                if (c.dataset.listingId) ids.push(parseInt(c.dataset.listingId, 10));
            });
            return ids;
        }

        function clearDraggable() {
            grid.querySelectorAll('[data-card][draggable="true"]').forEach(function (c) {
                if (!c.classList.contains("is-dragging")) c.removeAttribute("draggable");
            });
        }

        grid.addEventListener("pointerdown", function (e) {
            var grip = e.target.closest("[data-card-grip]");
            if (!grip) return;
            var card = grip.closest("[data-card]");
            if (card && card.dataset.published === "1") card.setAttribute("draggable", "true");
        });
        grid.addEventListener("pointerup", clearDraggable);

        grid.addEventListener("dragstart", function (e) {
            var card = e.target.closest("[data-card]");
            if (!card || card.getAttribute("draggable") !== "true" || card.dataset.published !== "1") {
                e.preventDefault();
                return;
            }
            dragCard = card;
            orderBefore = publishedIds().join(",");
            card.classList.add("is-dragging");
            if (e.dataTransfer) {
                e.dataTransfer.effectAllowed = "move";
                // Neutralise any inherited link/text payload so the browser can't
                // treat the drop as a navigation.
                e.dataTransfer.setData("text/plain", card.dataset.sourceId || "");
            }
        });
        grid.addEventListener("dragover", function (e) {
            if (!dragCard) return;
            e.preventDefault();
            if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
            var over = e.target.closest("[data-card]");
            if (!over || over === dragCard || over.dataset.published !== "1") return;
            var rect = over.getBoundingClientRect();
            var after = (e.clientY - rect.top) > rect.height / 2;
            grid.insertBefore(dragCard, after ? over.nextSibling : over);
        });
        grid.addEventListener("drop", function (e) {
            if (dragCard) e.preventDefault();
        });
        grid.addEventListener("dragend", function () {
            if (!dragCard) return;
            dragCard.classList.remove("is-dragging");
            dragCard = null;
            clearDraggable();
            var ids = publishedIds();
            if (ids.length && ids.join(",") !== orderBefore) {
                post(URLS.reorder, ids, false).then(function () { toast(root.dataset.savedMsg); }).catch(function () {});
            }
        });
    }
})();
