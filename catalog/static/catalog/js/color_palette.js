(function () {
    function ready(fn) {
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
        else fn();
    }

    function initPalette(palette) {
        if (!palette || palette.dataset.colorPaletteReady === '1') return;
        palette.dataset.colorPaletteReady = '1';
        const input = palette.querySelector('input[type="hidden"]');
        const trigger = palette.querySelector('[data-color-trigger]');
        const popover = palette.querySelector('[data-color-popover]');
        const currentSwatch = palette.querySelector('[data-color-current-swatch]');
        const currentLabel = palette.querySelector('[data-color-current-label]');
        const buttons = Array.from(palette.querySelectorAll('[data-color-value]'));
        if (!input || !buttons.length) return;

        function sync(value) {
            let activeButton = null;
            buttons.forEach((button) => {
                const active = (button.dataset.colorValue || '') === (value || '');
                if (active) activeButton = button;
                button.classList.toggle('is-active', active);
                button.style.outline = active ? '2px solid var(--bs-primary,#0d6efd)' : '';
                button.style.outlineOffset = active ? '2px' : '';
            });
            if (currentLabel) {
                currentLabel.textContent = activeButton?.dataset.colorLabel || palette.dataset.emptyLabel || 'No color';
            }
            if (currentSwatch) {
                const style = activeButton ? window.getComputedStyle(activeButton) : null;
                currentSwatch.style.background = style ? style.backgroundColor : 'transparent';
                currentSwatch.style.borderColor = style ? style.borderTopColor : 'var(--bs-border-color,#adb5bd)';
            }
        }

        function close() {
            if (popover) popover.hidden = true;
            if (trigger) trigger.setAttribute('aria-expanded', 'false');
        }

        if (trigger && popover) {
            trigger.setAttribute('aria-expanded', 'false');
            trigger.addEventListener('click', (event) => {
                event.stopPropagation();
                popover.hidden = !popover.hidden;
                trigger.setAttribute('aria-expanded', popover.hidden ? 'false' : 'true');
            });
            popover.addEventListener('click', (event) => event.stopPropagation());
        }

        buttons.forEach((button) => {
            button.addEventListener('click', () => {
                input.value = button.dataset.colorValue || '';
                input.dataset.userEdited = '1';
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
                sync(input.value);
                close();
            });
        });
        input.addEventListener('input', () => sync(input.value));
        input.addEventListener('change', () => sync(input.value));
        sync(input.value);
    }

    function initAll() {
        document.querySelectorAll('[data-color-palette]').forEach(initPalette);
    }

    ready(initAll);
    document.addEventListener('click', () => {
        document.querySelectorAll('[data-color-popover]').forEach((popover) => {
            popover.hidden = true;
        });
        document.querySelectorAll('[data-color-trigger]').forEach((trigger) => {
            trigger.setAttribute('aria-expanded', 'false');
        });
    });
    window.initCatalogColorPalettes = initAll;
})();
