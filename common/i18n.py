"""Tiny helper to look up a DLUX_STRINGS key in the active request language.

``get_strings()`` resolves the language from the thread-local request (set by
DjangoLux middleware), so this works inside table ``render_*`` methods, services,
and views without threading a request through.
"""
from dlux.translations import get_strings


def t(key, fallback=""):
    return get_strings().get(key, fallback or key)
