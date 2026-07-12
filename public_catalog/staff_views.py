import functools
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.generic import TemplateView

from catalog.models import Product, Service

from .models import PublicCatalogListing
from .settings import PUBLIC_CATALOG_NS, get_public_catalog_config, set_public_catalog_config

EDIT_PERM = "public_catalog.change_publiccataloglisting"


def mutation_endpoint(view):
    """Write-only builder endpoint.

    POST mutates with permission. Direct browser navigation returns to the builder
    page; passive GET/HEAD probes stay silent and never mutate.
    """

    @login_required
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.method not in ("POST", "PUT", "PATCH"):
            if request.method == "GET" and _is_navigation_get(request):
                return redirect("public_catalog_staff:builder")
            return HttpResponse(status=204)
        if not request.user.has_perm(EDIT_PERM):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def _is_navigation_get(request):
    fetch_mode = request.headers.get("Sec-Fetch-Mode", "")
    accept = request.headers.get("Accept", "")
    return fetch_mode == "navigate" or "text/html" in accept


TEXT_FIELDS = ("public_title", "public_summary", "public_body", "installation_notes", "warranty_notes")
BOOL_FIELDS = ("is_featured", "show_price", "show_availability", "show_when_unavailable")


def _builder_items():
    products = list(
        Product.objects.filter(is_active=True, deleted_at__isnull=True)
        .select_related("category")
        .prefetch_related("variants")
        .order_by("name")
    )
    services = list(
        Service.objects.filter(is_active=True, deleted_at__isnull=True).order_by("service_type", "name")
    )
    listings_p = {l.product_id: l for l in PublicCatalogListing.objects.filter(product__in=products)}
    listings_s = {l.service_id: l for l in PublicCatalogListing.objects.filter(service__in=services)}

    items = []
    for product in products:
        items.append(listings_p.get(product.pk) or PublicCatalogListing(product=product))
    for service in services:
        items.append(listings_s.get(service.pk) or PublicCatalogListing(service=service))

    items.sort(key=lambda l: (
        0 if (l.pk and l.is_published) else 1,
        l.sort_order if l.pk else 100,
        (l.display_title or "").lower(),
    ))
    return items


def _counts(items):
    published = [i for i in items if i.pk and i.is_published]
    return {
        "total": len(items),
        "published": len(published),
        "featured": sum(1 for i in published if i.is_featured),
        "available": sum(1 for i in published if i.is_available_for_public),
    }


def _listing_json(listing):
    price = listing.price_lyd
    return {
        "id": listing.pk,
        "kind": listing.source_kind,
        "source_id": listing.product_id or listing.service_id,
        "is_published": listing.is_published,
        "is_featured": listing.is_featured,
        "show_price": listing.show_price,
        "show_availability": listing.show_availability,
        "show_when_unavailable": listing.show_when_unavailable,
        "sort_order": listing.sort_order,
        "public_title": listing.public_title,
        "display_title": listing.display_title,
        "public_summary": listing.public_summary,
        "public_body": listing.public_body,
        "installation_notes": listing.installation_notes,
        "warranty_notes": listing.warranty_notes,
        "image_url": listing.image_url,
        "public_url": listing.get_absolute_url() if listing.pk else "",
        "availability_code": listing.availability_code,
        "availability_label": listing.availability_label,
        "price_lyd": float(price) if price is not None else None,
    }


def _resolve_listing(request, *, create):
    listing_id = request.POST.get("listing_id")
    if listing_id:
        try:
            return PublicCatalogListing.objects.get(pk=listing_id), False
        except PublicCatalogListing.DoesNotExist:
            raise Http404("listing not found")

    kind = request.POST.get("kind")
    source_id = request.POST.get("id")
    if kind == "product":
        existing = PublicCatalogListing.objects.filter(product_id=source_id).first()
    elif kind == "service":
        existing = PublicCatalogListing.objects.filter(service_id=source_id).first()
    else:
        raise Http404("invalid source")
    if existing:
        return existing, False
    if not create:
        raise Http404("listing not found")

    if kind == "product":
        source = Product.objects.filter(pk=source_id, is_active=True, deleted_at__isnull=True).first()
        listing = PublicCatalogListing(product=source) if source else None
    else:
        source = Service.objects.filter(pk=source_id, is_active=True, deleted_at__isnull=True).first()
        listing = PublicCatalogListing(service=source) if source else None
    if listing is None:
        raise Http404("source not found")

    cfg = get_public_catalog_config()
    listing.show_price = cfg["show_price"]
    listing.show_availability = cfg["show_availability"]
    return listing, True


class PublicCatalogBuilderView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "public_catalog/shop_builder.html"
    permission_required = "public_catalog.view_publiccataloglisting"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        items = _builder_items()
        ctx.update({
            "builder_items": items,
            "public_config": get_public_catalog_config(),
            "public_settings_ns": PUBLIC_CATALOG_NS,
            "builder_counts": _counts(items),
            "can_edit": self.request.user.has_perm(EDIT_PERM),
        })
        return ctx


@mutation_endpoint
def builder_toggle_publish(request):
    listing, created = _resolve_listing(request, create=True)
    listing.is_published = True if created else not listing.is_published
    if not listing.is_published:
        listing.is_featured = False
    listing.save()
    return JsonResponse({"ok": True, "listing": _listing_json(listing)})


@mutation_endpoint
def builder_update_listing(request):
    listing, _created = _resolve_listing(request, create=True)

    for field in TEXT_FIELDS:
        if field in request.POST:
            setattr(listing, field, (request.POST.get(field) or "").strip())
    for field in BOOL_FIELDS:
        if field in request.POST:
            setattr(listing, field, request.POST.get(field) in ("1", "true", "on", "True"))
    if "sort_order" in request.POST:
        try:
            listing.sort_order = max(0, int(request.POST.get("sort_order") or 0))
        except (TypeError, ValueError):
            pass
    if request.POST.get("clear_image") in ("1", "true", "on"):
        listing.image_override = ""
    if "image_override" in request.FILES:
        listing.image_override = request.FILES["image_override"]
    if listing.is_featured and not listing.is_published:
        listing.is_featured = False

    listing.save()
    return JsonResponse({"ok": True, "listing": _listing_json(listing)})


@mutation_endpoint
def builder_reorder(request):
    try:
        order = json.loads(request.body.decode() or "[]")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "bad payload"}, status=400)
    ids = [int(pk) for pk in order if str(pk).isdigit()]
    listings = {l.pk: l for l in PublicCatalogListing.objects.filter(pk__in=ids)}
    for index, pk in enumerate(ids):
        listing = listings.get(pk)
        if listing and listing.sort_order != index:
            listing.sort_order = index
            listing.save(update_fields=["sort_order"])
    return JsonResponse({"ok": True})


@mutation_endpoint
def builder_settings(request):
    patch = {}
    if "storefront_enabled" in request.POST:
        patch["storefront_enabled"] = request.POST.get("storefront_enabled") in ("1", "true", "on", "True")
    if "featured_limit" in request.POST:
        try:
            patch["featured_limit"] = max(0, int(request.POST.get("featured_limit") or 0))
        except (TypeError, ValueError):
            pass
    cfg = set_public_catalog_config(patch, request=request)
    return JsonResponse({"ok": True, "config": {
        "storefront_enabled": cfg["storefront_enabled"],
        "featured_limit": cfg["featured_limit"],
    }})


# --------------------------------------------------------------------------- #
# Public homepage (landing page) builder
# --------------------------------------------------------------------------- #
def _save_homepage_image(uploaded, prefix):
    import os
    from uuid import uuid4

    from django.core.files.storage import default_storage

    ext = os.path.splitext(uploaded.name)[1].lower() or ".png"
    name = f"public_homepage/{prefix}-{uuid4().hex}{ext}"
    saved = default_storage.save(name, uploaded)
    return default_storage.url(saved)


class PublicHomepageBuilderView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "public_catalog/homepage_builder.html"
    permission_required = "public_catalog.view_publiccataloglisting"

    def get_context_data(self, **kwargs):
        from common.i18n import t
        from .homepage import HOMEPAGE_NS, get_homepage_config, resolve_sections

        ctx = super().get_context_data(**kwargs)
        cfg = get_homepage_config()
        ctx.update({
            "homepage_config": cfg,
            "homepage_sections": resolve_sections(cfg),
            "homepage_settings_ns": HOMEPAGE_NS,
            "hero_media_choices": [
                ("featured", t("hp_media_featured", "Featured image")),
                ("logo", t("hp_media_logo", "Logo")),
                ("custom", t("hp_media_custom", "Custom image")),
                ("gradient", t("hp_media_gradient", "Gradient")),
            ],
            "accent_presets": ["#345b86", "#0ea5e9", "#16a34a", "#dc2626", "#9333ea", "#f59e0b", "#0f172a"],
            "can_edit": self.request.user.has_perm(EDIT_PERM),
        })
        return ctx


@mutation_endpoint
def homepage_save(request):
    from .homepage import HOMEPAGE_DEFAULTS, set_homepage_config

    post = request.POST
    patch = {}
    for key, default in HOMEPAGE_DEFAULTS.items():
        if key in ("sections", "hero_image", "story_image"):
            continue
        if key in ("hero_show_contact", "show_stats"):
            if key in post:
                patch[key] = post.get(key) in ("1", "true", "on", "True")
        elif key == "hero_overlay":
            if key in post:
                patch[key] = post.get(key)
        elif isinstance(default, str):
            if key in post:
                patch[key] = (post.get(key) or "").strip()

    if "hero_image" in request.FILES:
        patch["hero_image"] = _save_homepage_image(request.FILES["hero_image"], "hero")
    elif post.get("clear_hero_image") in ("1", "true", "on"):
        patch["hero_image"] = ""
    if "story_image" in request.FILES:
        patch["story_image"] = _save_homepage_image(request.FILES["story_image"], "story")
    elif post.get("clear_story_image") in ("1", "true", "on"):
        patch["story_image"] = ""

    if "sections" in post:
        try:
            patch["sections"] = json.loads(post.get("sections") or "[]")
        except ValueError:
            pass

    cfg = set_homepage_config(patch, request=request)
    return JsonResponse({"ok": True, "config": cfg})
