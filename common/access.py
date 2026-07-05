"""
Row-level (per-employee) visibility on top of dlux's model-level permissions.

Django permissions are model-level ("can view invoices"). This module adds the
*which rows* layer: a regular employee sees only records they own, while a
manager (or superuser) with the model's ``view_all_<model>`` permission sees
everything.

Ownership is declared per model by an ``OWNER_FIELDS`` class attribute — a tuple
of ORM lookups that point at a user (e.g. ``("salesperson", "created_by")`` or
``("invoice__salesperson",)``). A model without ``OWNER_FIELDS`` is treated as
shared (the product catalog, exchange rates, …) and never row-filtered.

Filtering is applied at the READ choke points only (list pages, the dynamic
modal edit/view/delete lookup, invoice detail/report). It is deliberately NOT a
model manager: whether you may see a ``Payment`` depends on context — its own
standalone list is owner-filtered, but the payments *of an invoice you already
own* must all show, regardless of who keyed them in.
"""
from django.db.models import Q


def view_all_perm(model):
    """The permission codename that lets a user see every row of ``model``."""
    opts = model._meta
    return f"{opts.app_label}.view_all_{opts.model_name}"


def user_can_view_all(user, model):
    """True if ``user`` bypasses row-filtering for ``model`` (manager/admin)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user.has_perm(view_all_perm(model))


def apply_ownership(queryset, user):
    """Restrict ``queryset`` to rows ``user`` owns, unless the model is shared or
    the user may view all. Safe to call on any queryset — a model without
    ``OWNER_FIELDS`` is returned unchanged."""
    model = queryset.model
    owner_fields = getattr(model, "OWNER_FIELDS", None)
    if not owner_fields:
        return queryset  # shared model — no row filtering
    if user_can_view_all(user, model):
        return queryset
    if user is None or not getattr(user, "is_authenticated", False):
        return queryset.none()
    predicate = Q()
    for lookup in owner_fields:
        predicate |= Q(**{lookup: user})
    # OR across related lookups can multiply rows via joins — collapse them.
    return queryset.filter(predicate).distinct()


def install_modal_ownership_patch():
    """Layer ownership onto dlux's dynamic-modal object lookup.

    The project's ``scoped_modal_manager`` / ``scoped_modal_delete`` routes use
    dlux ``DynamicModalManagerView`` / ``DynamicModalDeleteView``, which resolve
    the edited/deleted object through a module-level
    ``_scope_filtered_modal_queryset(model, user)`` helper. Without this, a rep
    could open another rep's Customer/Payment/Delivery by guessing its id. We
    wrap that single helper (all three edit/view/delete call sites route through
    it) so the owner filter is enforced everywhere the modal touches an object.
    Idempotent and a no-op for shared models.
    """
    try:
        from dlux.views import sections
    except Exception:  # pragma: no cover - dlux always present at runtime
        return
    original = getattr(sections, "_scope_filtered_modal_queryset", None)
    if original is None or getattr(original, "_ownership_wrapped", False):
        return

    def wrapped(model, user):
        return apply_ownership(original(model, user), user)

    wrapped._ownership_wrapped = True
    sections._scope_filtered_modal_queryset = wrapped
