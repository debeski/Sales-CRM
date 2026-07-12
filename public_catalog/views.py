from django.db.models import Q
from django.http import Http404, JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.generic import DetailView, TemplateView

from .forms import PublicContactForm
from .models import PublicCatalogListing, PublicContactMessage
from .settings import contact_links, get_public_catalog_config


def _public_listings():
    listings = list(PublicCatalogListing.objects.published())
    return [
        listing
        for listing in listings
        if listing.show_when_unavailable or listing.is_available_for_public
    ]


def _listing_counts(listings):
    return {
        "total": len(listings),
        "products": sum(1 for listing in listings if listing.source_kind == "product"),
        "services": sum(1 for listing in listings if listing.source_kind == "service"),
    }


class _StorefrontGateMixin:
    def dispatch(self, request, *args, **kwargs):
        cfg = get_public_catalog_config()
        if not cfg.get("storefront_enabled", True):
            return render(request, "public_catalog/coming_soon.html", {"public_config": cfg}, status=503)
        return super().dispatch(request, *args, **kwargs)


class PublicLandingView(_StorefrontGateMixin, TemplateView):
    template_name = "public_catalog/landing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cfg = get_public_catalog_config()
        limit = cfg.get("featured_limit") or 4
        listings = _public_listings()
        featured = [listing for listing in listings if listing.is_featured][:limit]
        hero_listing = (featured or listings[:1] or [None])[0]
        ctx.update({
            "public_config": cfg,
            "hero_listing": hero_listing,
            "featured_listings": featured or listings[:limit],
            "listing_counts": _listing_counts(listings),
            "contact_links": contact_links(),
        })
        return ctx


class PublicShopView(_StorefrontGateMixin, TemplateView):
    template_name = "public_catalog/shop.html"

    def _filtered_listings(self):
        qs = PublicCatalogListing.objects.published()
        kind = (self.request.GET.get("kind") or "").strip()
        if kind == "products":
            qs = qs.filter(product__isnull=False)
        elif kind == "services":
            qs = qs.filter(service__isnull=False)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(public_title__icontains=q)
                | Q(public_summary__icontains=q)
                | Q(public_body__icontains=q)
                | Q(product__name__icontains=q)
                | Q(product__description__icontains=q)
                | Q(product__category__name__icontains=q)
                | Q(service__name__icontains=q)
                | Q(service__description__icontains=q)
            )
        return [
            listing
            for listing in qs
            if listing.show_when_unavailable or listing.is_available_for_public
        ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        listings = self._filtered_listings()
        all_listings = _public_listings()
        ctx.update({
            "public_config": get_public_catalog_config(),
            "listings": listings,
            "listing_counts": _listing_counts(all_listings),
            "filtered_count": len(listings),
            "contact_links": contact_links(),
            "q": self.request.GET.get("q", ""),
            "kind": self.request.GET.get("kind", ""),
        })
        return ctx


class PublicItemDetailView(_StorefrontGateMixin, DetailView):
    model = PublicCatalogListing
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "public_catalog/item_detail.html"
    context_object_name = "listing"

    def get_queryset(self):
        return PublicCatalogListing.objects.published()

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.show_when_unavailable and not obj.is_available_for_public:
            raise Http404("Listing is unavailable.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "public_config": get_public_catalog_config(),
            "contact_links": contact_links(self.object),
        })
        return ctx


def public_item_modal(request, slug):
    if not get_public_catalog_config().get("storefront_enabled", True):
        raise Http404("Storefront is offline.")
    listing = get_object_or_404(PublicCatalogListing.objects.published(), slug=slug)
    if not listing.show_when_unavailable and not listing.is_available_for_public:
        raise Http404("Listing is unavailable.")
    html = render_to_string(
        "public_catalog/_item_modal.html",
        {
            "listing": listing,
            "public_config": get_public_catalog_config(),
            "contact_links": contact_links(listing),
        },
        request=request,
    )
    return JsonResponse({"html": html})


def _contact_recipient():
    cfg = get_public_catalog_config()
    return str(cfg.get("contact_email") or settings.DEFAULT_FROM_EMAIL or "").strip()


def _render_contact_modal(request, form=None, sent=False):
    html = render_to_string(
        "public_catalog/_contact_modal.html",
        {
            "form": form or PublicContactForm(source_path=request.GET.get("next") or request.META.get("HTTP_REFERER", "")),
            "sent": sent,
            "public_config": get_public_catalog_config(),
        },
        request=request,
    )
    return JsonResponse({"html": html})


def _send_contact_email(message):
    recipient = _contact_recipient()
    if not recipient:
        message.email_status = PublicContactMessage.STATUS_SKIPPED
        message.email_error = "No public catalog contact email or DEFAULT_FROM_EMAIL configured."
        message.save(update_fields=["email_status", "email_error", "updated_at"])
        return

    subject = message.subject or f"Public catalog contact from {message.name}"
    body = "\n".join([
        f"Name: {message.name}",
        f"Email: {message.email}",
        f"Phone: {message.phone or '-'}",
        f"Source: {message.source_path or '-'}",
        "",
        message.message,
    ])
    try:
        send_mail(
            subject=f"[Switch public catalog] {subject}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as exc:
        message.email_status = PublicContactMessage.STATUS_FAILED
        message.email_recipient = recipient
        message.email_error = str(exc)[:2000]
        message.save(update_fields=["email_status", "email_recipient", "email_error", "updated_at"])
        return

    message.email_status = PublicContactMessage.STATUS_SENT
    message.email_recipient = recipient
    message.email_sent_at = timezone.now()
    message.email_error = ""
    message.save(update_fields=["email_status", "email_recipient", "email_sent_at", "email_error", "updated_at"])


def public_contact_modal(request):
    if request.method == "GET":
        sent = bool(request.session.pop("public_contact_sent", False))
        return _render_contact_modal(request, sent=sent)
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method."}, status=405)

    form = PublicContactForm(request.POST)
    if not form.is_valid():
        return _render_contact_modal(request, form=form)

    if form.cleaned_data.get("company"):
        request.session["public_contact_sent"] = True
        return JsonResponse({"success": True})

    key = form.cleaned_data["idempotency_key"]
    defaults = {
        "name": form.cleaned_data["name"],
        "email": form.cleaned_data["email"],
        "phone": form.cleaned_data.get("phone", ""),
        "subject": form.cleaned_data.get("subject", ""),
        "message": form.cleaned_data["message"],
        "source_path": form.cleaned_data.get("source_path", ""),
        "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:300],
    }
    created = False
    try:
        with transaction.atomic():
            message, created = PublicContactMessage.objects.get_or_create(
                idempotency_key=key,
                defaults=defaults,
            )
    except IntegrityError:
        message = PublicContactMessage.objects.get(idempotency_key=key)

    if created:
        _send_contact_email(message)

    request.session["public_contact_sent"] = True
    return JsonResponse({"success": True})
