"""Shared form helpers."""
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Field, Layout, Row
from django import forms

from dlux.translations import get_current_language_code, get_strings
from dlux.utils import translate_choices

# Bootstrap column class per number of fields sharing a row.
_GRID_COL = {1: "col-12", 2: "col-md-6", 3: "col-md-4", 4: "col-md-3"}


def build_grid_helper(form, rows):
    """Give a modal ModelForm a multi-column crispy layout so short fields share
    a row instead of each taking a full row.

    The dlux ``DynamicModalManagerView`` renders ``{% crispy form %}`` but attaches
    **no** helper/layout, so without this crispy falls back to one field per row.
    A defined helper is honored by the template; we deliberately add no submit
    input, so dlux's own icon Save/Cancel buttons still render.

    ``rows`` is a list where each item is a tuple of field names (share one
    Bootstrap row) or a single field name (full width). Names absent from the
    form (e.g. a permission-gated field) are dropped and empty rows removed; any
    field not mentioned is appended full-width so nothing is ever lost.
    """
    helper = FormHelper()
    helper.form_tag = False       # the modal template provides <form> + csrf
    helper.disable_csrf = True
    components = []
    placed = set()
    for row in rows:
        names = (row,) if isinstance(row, str) else tuple(row)
        placed.update(names)
        present = [n for n in names if n in form.fields]
        if not present:
            continue
        css = _GRID_COL.get(len(present), "col-md-6")
        components.append(Row(*[Column(n, css_class=css) for n in present]))
    for name in form.fields:
        if name not in placed:
            # Hidden fields render as a bare input (no empty grid row).
            if isinstance(form.fields[name].widget, forms.HiddenInput):
                components.append(Field(name))
            else:
                components.append(Row(Column(name, css_class="col-12")))
    helper.layout = Layout(*components)
    form.helper = helper
    return helper


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
