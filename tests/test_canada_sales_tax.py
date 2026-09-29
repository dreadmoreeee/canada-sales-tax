import datetime as dt
from decimal import Decimal as D

import pytest

from canada_sales_tax import EARLIEST_DATE, PROVINCES, calculate, rates
from canada_sales_tax.__main__ import main

TODAY_RATES = {  # CRA GST/HST calculator, checked September 2026
    "AB": {"GST": "5"}, "BC": {"GST": "5", "PST": "7"}, "MB": {"GST": "5", "PST": "7"},
    "NB": {"HST": "15"}, "NL": {"HST": "15"}, "NS": {"HST": "14"}, "NT": {"GST": "5"},
    "NU": {"GST": "5"}, "ON": {"HST": "13"}, "PE": {"HST": "15"},
    "QC": {"GST": "5", "QST": "9.975"}, "SK": {"GST": "5", "PST": "6"}, "YT": {"GST": "5"},
}
DAY = dt.date(2026, 9, 28)


@pytest.mark.parametrize("prov", sorted(PROVINCES))
def test_current_rates_for_every_province(prov):
    got = {r.code: r.percent for r in rates(prov, on=DAY)}
    assert got == {k: D(v) for k, v in TODAY_RATES[prov].items()}


def test_nova_scotia_hst_dropped_to_14_on_april_1_2025():
    assert rates("NS", on=dt.date(2025, 3, 31))[0].percent == D("15")
    assert rates("NS", on=dt.date(2025, 4, 1))[0].percent == D("14")


def test_simple_hst():
    b = calculate("100", "NB", on=DAY)
    assert b.subtotal == D("100.00") and b.total == D("115.00")
    assert [(t.code, t.amount) for t in b.taxes] == [("HST", D("15.00"))]


def test_quebec_rounds_each_tax_separately():
    b = calculate("19.99", "QC", on=DAY)
    assert [(t.code, t.amount) for t in b.taxes] == [("GST", D("1.00")), ("QST", D("1.99"))]
    assert b.total == D("22.98")


def test_half_cent_rounds_up():
    # 10.10 * 5% = 0.505 -> 0.51 (ROUND_HALF_UP, like a till), not banker's 0.50
    assert calculate("10.10", "AB", on=DAY).taxes[0].amount == D("0.51")


@pytest.mark.parametrize("prov", sorted(PROVINCES))
def test_tax_included_always_adds_up_to_the_price_paid(prov):
    for cents in list(range(1, 2000)) + [99999, 123456, 1000000]:
        gross = D(cents) / 100
        b = calculate(gross, prov, on=DAY, tax_included=True)
        assert b.total == gross, (prov, gross, b)
        assert all(t.amount >= 0 for t in b.taxes)


def test_tax_included_example():
    b = calculate("115.00", "NB", on=DAY, tax_included=True)
    assert b.subtotal == D("100.00") and b.taxes[0].amount == D("15.00")


def test_invoice_lines_in_english_and_french():
    b = calculate("100", "QC", on=DAY)
    assert b.lines() == ["Subtotal: 100.00", "GST (5%): 5.00", "QST (9.975%): 9.98", "Total: 114.98"]
    assert b.lines("fr") == ["Sous-total: 100.00", "TPS (5%): 5.00", "TVQ (9.975%): 9.98", "Total: 114.98"]


def test_lowercase_and_spaces_in_province_code():
    assert calculate("10", " on ", on=DAY).total == D("11.30")


@pytest.mark.parametrize("bad", ["XX", "", "Ontario"])
def test_unknown_province_is_an_error(bad):
    with pytest.raises(ValueError, match="unknown province"):
        calculate("10", bad, on=DAY)


@pytest.mark.parametrize("bad", ["abc", "NaN", "Infinity"])
def test_bad_amount_is_an_error(bad):
    with pytest.raises(ValueError, match="not an amount"):
        calculate(bad, "ON", on=DAY)


def test_dates_before_the_table_are_refused():
    with pytest.raises(ValueError, match="only tabulated"):
        rates("ON", on=EARLIEST_DATE - dt.timedelta(days=1))


def test_cli(capsys):
    assert main(["100", "NS", "--on", "2025-03-31"]) == 0
    assert capsys.readouterr().out.splitlines() == ["Subtotal: 100.00", "HST (15%): 15.00", "Total: 115.00"]
    assert main(["100", "ZZ"]) == 2
