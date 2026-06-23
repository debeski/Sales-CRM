from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Project-shared app with NO models — exists so DjangoLux discovers
    ``common/translations.py`` (shared UI strings, table headers, choice labels)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "common"
    verbose_name = "Common"
