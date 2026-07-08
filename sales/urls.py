from django.urls import path
from django.views.generic import RedirectView

from .views import (
    CustomerListView,
    DashboardView,
    DeliveryListView,
    FinancialReportView,
    InvoiceCancelView,
    InvoiceCreateView,
    InvoiceDetailView,
    InvoiceIssueView,
    InvoiceListView,
    InvoicePrintView,
    InvoiceUpdateView,
    PaymentCreateView,
    PaymentListView,
    SalesReportExportView,
    SalesReportView,
)

app_name = "sales"

# The XLSX download is a file response, not a page — hide it from the dlux
# auto-discovered sidebar (see discovery._is_candidate -> sidebar_exclude).
_report_export = SalesReportExportView.as_view()
_report_export.sidebar_exclude = True

# Bare /sales/ redirects to the dashboard (the app home). The invoice list lives
# at /sales/invoices/ so its sidebar URL doesn't prefix-match every other sales
# page (which made "Invoices" highlight on the dashboard, customers, etc.).
_sales_home = RedirectView.as_view(pattern_name="sales:dashboard", permanent=False)
_sales_home.sidebar_exclude = True

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("", _sales_home, name="sales_home"),
    path("invoices/", InvoiceListView.as_view(), name="invoice_list"),
    path("new/", InvoiceCreateView.as_view(), name="invoice_create"),
    path("<int:pk>/", InvoiceDetailView.as_view(), name="invoice_detail"),
    path("<int:pk>/edit/", InvoiceUpdateView.as_view(), name="invoice_edit"),
    path("<int:pk>/issue/", InvoiceIssueView.as_view(), name="invoice_issue"),
    path("<int:pk>/cancel/", InvoiceCancelView.as_view(), name="invoice_cancel"),
    path("<int:pk>/print/", InvoicePrintView.as_view(), name="invoice_print"),
    path("<int:pk>/pay/", PaymentCreateView.as_view(), name="payment_add"),
    path("customers/", CustomerListView.as_view(), name="customer_list"),
    path("deliveries/", DeliveryListView.as_view(), name="delivery_list"),
    path("payments/", PaymentListView.as_view(), name="payment_list"),
    path("report/", SalesReportView.as_view(), name="report"),
    path("report/export/", _report_export, name="report_export"),
    path("financial/", FinancialReportView.as_view(), name="financial_report"),
]
