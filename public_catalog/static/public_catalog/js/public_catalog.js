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
})();
