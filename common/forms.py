"""Shared form helpers."""
from django import forms

from dlux.translations import get_current_language_code, get_strings
from dlux.utils import translate_choices


def translate_choice_fields(form, request=None):
    """Localize static-choice dropdown option labels via dlux ``translate_choices``.

    Looks each option's value up under the ``choice_<value>`` DLUX_STRINGS key (so
    e.g. ``status`` renders "مسودة/صادرة…"). Skips ``ModelChoiceField`` (its options
    are DB objects, not translatable strings) and preserves any first-choice
    placeholder that ``set_field_attrs`` already set. Also covers widget-level
    choices such as ``NullBooleanSelect`` (the ``is_active`` yes/no/any filter).
    """
    strings = get_strings(get_current_language_code(request))
    for field in form.fields.values():
        if isinstance(field, forms.ModelChoiceField):
            continue
        # Prefer field.choices: for django_filters ChoiceFields it carries the
        # first-choice *label* placeholder that set_field_attrs/set_first_choice
        # set (e.g. "Method"), whereas the widget still holds the default
        # "---------". Fall back to widget.choices for fields without their own
        # (e.g. NullBooleanField's is_active yes/no/any).
        source = getattr(field, "choices", None) or getattr(field.widget, "choices", None)
        if not source:
            continue
        # Assign to the *widget* (what actually renders). Writing field.choices
        # instead would make django_filters re-prepend its empty option and drop
        # the placeholder label. Only labels change — values are untouched, so
        # field validation is unaffected.
        field.widget.choices = translate_choices(list(source), strings)


def translate_help_text(form, request=None):
    """Localize each field's ``help_text`` from DLUX_STRINGS.

    ``set_field_attrs`` translates field *labels* but leaves ``help_text`` as the
    English literal declared on the model, so form descriptions render in English
    even under Arabic. This mirrors that convention for help text: for every field
    it looks up ``help_<model>_<field>`` (then the generic ``help_<field>``) and,
    when found, overrides ``field.help_text``. Fields without a key keep whatever
    help text they already have, so partial coverage is safe.
    """
    strings = get_strings(get_current_language_code(request))
    model_name = ""
    if hasattr(form, "_meta") and getattr(form._meta, "model", None):
        model_name = form._meta.model.__name__.lower()
    for field_name, field in form.fields.items():
        text = None
        if model_name:
            text = strings.get(f"help_{model_name}_{field_name}")
        if not text:
            text = strings.get(f"help_{field_name}")
        if text:
            field.help_text = text
