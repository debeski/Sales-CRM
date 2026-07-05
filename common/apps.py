from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Project-shared app with NO models — exists so DjangoLux discovers
    ``common/translations.py`` (shared UI strings, table headers, choice labels)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "common"
    verbose_name = "Common"

    def ready(self):
        # Enforce per-employee row ownership on the dlux dynamic-modal
        # edit/view/delete object lookup (see common.access). Installed on the
        # first request rather than here: importing dlux.views at app-init time
        # triggers section discovery (a DB query during startup). request_started
        # fires before any view dispatch, so the patch is always in place before
        # a modal can resolve an object.
        from django.core.signals import request_started

        def _install(sender, **kwargs):
            from common.access import install_modal_ownership_patch

            install_modal_ownership_patch()
            request_started.disconnect(_install)

        request_started.connect(_install, weak=False)
