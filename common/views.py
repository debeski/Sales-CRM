"""
Reusable view building blocks shared by every domain app.

The slick DjangoLux pattern for simple models is: a single permission-gated
``ListView`` per model, with create/edit/view/delete handled by the framework's
dynamic modal manager (``modal_manager``) which auto-resolves ``<Model>Form``.
``ScopedListView`` wires that whole surface up in a few lines, so the apps stay
thin and consistent.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import FieldDoesNotExist
from django.urls import reverse
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from dlux.translations import get_current_language_code, get_strings
from dlux.utils import get_user_scope, is_scope_enabled, setup_filter_helper


def scope_filtered_queryset(queryset, user):
    """Defence-in-depth scope guard (the ScopedManager already scopes; this keeps
    parity with the dlux scaffold and protects custom querysets)."""
    if not is_scope_enabled() or getattr(user, "is_superuser", False):
        return queryset
    try:
        queryset.model._meta.get_field("scope")
    except FieldDoesNotExist:
        return queryset
    user_scope = get_user_scope(user)
    if user_scope is None:
        return queryset.none()
    return queryset.filter(scope=user_scope)


class ScopedListView(LoginRequiredMixin, PermissionRequiredMixin, SingleTableMixin, FilterView):
    """Standard list page: filter form + DluxTable + a permission-gated "Add"
    button that opens the framework dynamic-modal create form.

    Subclasses set ``model``, ``table_class``, ``filterset_class``,
    ``permission_required`` and (optionally) ``page_title`` / ``page_subtitle``.
    """

    raise_exception = True
    template_name = "common/scoped_list.html"
    ordering = "-created_at"
    #: DLUX_STRINGS keys (preferred — bilingual). Fall back to the literals below.
    page_title_key = ""
    page_subtitle_key = ""
    page_title = ""
    page_subtitle = ""
    #: set False for models that should not be created from the list page
    allow_add = True

    def get_queryset(self):
        qs = self.model._default_manager.all()
        if self.ordering:
            order = [self.ordering] if isinstance(self.ordering, str) else list(self.ordering)
            qs = qs.order_by(*order)
        return scope_filtered_queryset(qs, self.request.user)

    def get_filterset(self, filterset_class):
        filterset = super().get_filterset(filterset_class)
        setup_filter_helper(filterset, request=self.request)
        return filterset

    def get_add_modal_url(self):
        opts = self.model._meta
        return reverse("modal_manager", args=[opts.app_label, opts.object_name, "new"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        opts = self.model._meta
        strings = get_strings(get_current_language_code(self.request))
        can_add = self.allow_add and self.request.user.has_perm(
            f"{opts.app_label}.add_{opts.model_name}"
        )
        title = (
            (self.page_title_key and strings.get(self.page_title_key))
            or self.page_title
            or strings.get(f"model_{opts.model_name}")
            or str(opts.verbose_name_plural).title()
        )
        subtitle = (self.page_subtitle_key and strings.get(self.page_subtitle_key)) or self.page_subtitle
        context.update(
            {
                "page_title": title,
                "page_subtitle": subtitle,
                "add_modal_url": self.get_add_modal_url() if can_add else None,
                "add_label": strings.get("ui_add", "Add"),
                "model_verbose_name": opts.verbose_name,
            }
        )
        return context
