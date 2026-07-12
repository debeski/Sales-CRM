from django.urls import path

from .views import (
    PublicItemDetailView,
    PublicLandingView,
    PublicShopView,
    public_contact_modal,
    public_item_modal,
)

app_name = "public_catalog"

landing_view = PublicLandingView.as_view()
landing_view.sidebar_exclude = True
shop_view = PublicShopView.as_view()
shop_view.sidebar_exclude = True
contact_modal_view = public_contact_modal
contact_modal_view.sidebar_exclude = True

urlpatterns = [
    path("", landing_view, name="landing"),
    path("shop/", shop_view, name="shop"),
    path("contact/modal/", contact_modal_view, name="contact_modal"),
    path("shop/items/<slug:slug>/", PublicItemDetailView.as_view(), name="item_detail"),
    path("shop/items/<slug:slug>/modal/", public_item_modal, name="item_modal"),
]
