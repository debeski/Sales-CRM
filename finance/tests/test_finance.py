from unittest import mock

from django import forms
from django.test import SimpleTestCase

from common.forms import translate_choice_fields

from ..urls import app_name
from .. import services


class ChoiceTranslationTests(SimpleTestCase):
    """common.forms.translate_choice_fields localizes dropdown option labels."""

    def test_translates_options_keeps_single_placeholder(self):
        class F(forms.Form):
            method = forms.ChoiceField(
                choices=[("", "Method"), ("cash", "x"), ("cheque", "y")]
            )

        form = F()
        translate_choice_fields(form)
        rendered = list(form.fields["method"].widget.choices)
        # First-choice placeholder label is preserved, not duplicated.
        self.assertEqual(rendered[0], ("", "Method"))
        self.assertEqual([v for v, _ in rendered].count(""), 1)
        # Values untouched; labels resolved from the choice_<value> keys.
        self.assertEqual([v for v, _ in rendered], ["", "cash", "cheque"])
        self.assertEqual(dict(rendered)["cash"], "Cash")
        self.assertEqual(dict(rendered)["cheque"], "Cheque")


class FinanceConfigScaffoldTests(SimpleTestCase):
    def test_urls_namespace_matches_app_name(self):
        self.assertEqual(app_name, "finance")


# A trimmed sample of the CBL currency table (USD row, as served) so the scraper
# is exercised without a live network call.
_CBL_SAMPLE = """
<table id="currency-table">
<tr><th>التاريخ</th><th>العملة</th></tr>
<tr>
  <td><span class="uk-text-bold">التاريخ: </span>2026-07-02</td>
  <td><span class="uk-text-bold">العملة: </span>الدولار الأمريكي</td>
  <td><span class="uk-text-bold">المتوسط: </span>6.4117&nbspد.ل</td>
  <td><span class="uk-text-bold">بيع: </span>6.4277&nbspد.ل</td>
  <td><span class="uk-text-bold">شراء: </span>6.3956&nbspد.ل</td>
</tr>
<tr>
  <td><span>العملة: </span>الدولار الكندي</td>
  <td><span>المتوسط: </span>4.5118&nbspد.ل</td>
</tr>
</table>
"""


class CblRateScraperTests(SimpleTestCase):
    def test_parses_usd_row(self):
        fake = mock.Mock()
        fake.read.return_value = _CBL_SAMPLE.encode("utf-8")
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda *a: False
        with mock.patch("urllib.request.urlopen", return_value=fake):
            data = services.fetch_cbl_usd_rate()
        self.assertIsNotNone(data)
        # Must pick the American-dollar row, not the Canadian one below it.
        self.assertEqual(data["average"], "6.4117")
        self.assertEqual(data["sell"], "6.4277")
        self.assertEqual(data["buy"], "6.3956")
        self.assertEqual(data["date"], "2026-07-02")

    def test_returns_none_on_network_error(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("boom")):
            self.assertIsNone(services.fetch_cbl_usd_rate())


# A trimmed sample of the eanlibya table: the dollar row (with a "down" trend
# arrow whose `fa-2x` class must not be mistaken for the rate) plus a euro row.
_EAN_SAMPLE = """
<table>
<tr><th class="column-1"></th><th class="column-2">العملة</th><th class="column-3">السعر</th></tr>
<tr>
  <td class="column-1"><img alt="الدولار"></td>
  <td class="column-2">الدولار</td>
  <td class="column-3"><i class="far fa-arrow-alt-circle-down fa-2x" style="color:red"></i> 8.50</td>
</tr>
<tr>
  <td class="column-1"><img alt="اليورو"></td>
  <td class="column-2">اليورو</td>
  <td class="column-3"><i class="far fa-arrow-alt-circle-up fa-2x" style="color:green"></i> 9.71</td>
</tr>
</table>
"""


class EanRateScraperTests(SimpleTestCase):
    def test_parses_dollar_row(self):
        fake = mock.Mock()
        fake.read.return_value = _EAN_SAMPLE.encode("utf-8")
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda *a: False
        with mock.patch("urllib.request.urlopen", return_value=fake):
            data = services.fetch_ean_usd_rate()
        self.assertIsNotNone(data)
        self.assertEqual(data["rate"], "8.50")  # not "2" from fa-2x, not the euro 9.71
        self.assertEqual(data["trend"], "down")

    def test_returns_none_on_network_error(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("boom")):
            self.assertIsNone(services.fetch_ean_usd_rate())
