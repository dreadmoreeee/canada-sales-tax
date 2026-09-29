"""Canadian sales tax (GST, HST, PST, QST) by province and date, with exact cents.

    >>> from canada_sales_tax import calculate
    >>> b = calculate("100.00", "NB")
    >>> b.total
    Decimal('115.00')
    >>> [(t.code, str(t.amount)) for t in b.taxes]
    [('HST', '15.00')]

Money is handled with Decimal and each tax is rounded to the cent separately,
the way it appears on a Canadian invoice. Rates are dated: pass `on=` to get the
rate that applied on a given day (supported from 2019-07-01).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

__all__ = ["PROVINCES", "Rate", "Tax", "Breakdown", "rates", "calculate", "EARLIEST_DATE"]
__version__ = "1.0.0"

CENT = Decimal("0.01")
EARLIEST_DATE = dt.date(2019, 7, 1)

PROVINCES = {
    "AB": ("Alberta", "Alberta"),
    "BC": ("British Columbia", "Colombie-Britannique"),
    "MB": ("Manitoba", "Manitoba"),
    "NB": ("New Brunswick", "Nouveau-Brunswick"),
    "NL": ("Newfoundland and Labrador", "Terre-Neuve-et-Labrador"),
    "NS": ("Nova Scotia", "Nouvelle-Écosse"),
    "NT": ("Northwest Territories", "Territoires du Nord-Ouest"),
    "NU": ("Nunavut", "Nunavut"),
    "ON": ("Ontario", "Ontario"),
    "PE": ("Prince Edward Island", "Île-du-Prince-Édouard"),
    "QC": ("Quebec", "Québec"),
    "SK": ("Saskatchewan", "Saskatchewan"),
    "YT": ("Yukon", "Yukon"),
}

# (tax code, EN label, FR label)
_LABELS = {
    "GST": ("GST", "TPS"),
    "HST": ("HST", "TVH"),
    "PST": ("PST", "TVP"),
    "QST": ("QST", "TVQ"),
}

# Rate table: province -> list of (valid_from, {tax_code: percent}), newest last.
# Source: Canada Revenue Agency GST/HST rates and provincial finance ministries.
# Only changes on or after EARLIEST_DATE are listed; older dates raise ValueError.
_TABLE: dict[str, list[tuple[dt.date, dict[str, str]]]] = {
    "AB": [(EARLIEST_DATE, {"GST": "5"})],
    "BC": [(EARLIEST_DATE, {"GST": "5", "PST": "7"})],
    "MB": [(EARLIEST_DATE, {"GST": "5", "PST": "7"})],
    "NB": [(EARLIEST_DATE, {"HST": "15"})],
    "NL": [(EARLIEST_DATE, {"HST": "15"})],
    "NS": [(EARLIEST_DATE, {"HST": "15"}), (dt.date(2025, 4, 1), {"HST": "14"})],
    "NT": [(EARLIEST_DATE, {"GST": "5"})],
    "NU": [(EARLIEST_DATE, {"GST": "5"})],
    "ON": [(EARLIEST_DATE, {"HST": "13"})],
    "PE": [(EARLIEST_DATE, {"HST": "15"})],
    "QC": [(EARLIEST_DATE, {"GST": "5", "QST": "9.975"})],
    "SK": [(EARLIEST_DATE, {"GST": "5", "PST": "6"})],
    "YT": [(EARLIEST_DATE, {"GST": "5"})],
}


@dataclass(frozen=True)
class Rate:
    code: str            # GST, HST, PST or QST
    percent: Decimal     # e.g. Decimal("15")

    def label(self, lang: str = "en") -> str:
        en, fr = _LABELS[self.code]
        return fr if lang == "fr" else en


@dataclass(frozen=True)
class Tax:
    code: str
    percent: Decimal
    amount: Decimal

    def label(self, lang: str = "en") -> str:
        return Rate(self.code, self.percent).label(lang)


@dataclass(frozen=True)
class Breakdown:
    province: str
    subtotal: Decimal
    taxes: list[Tax] = field(default_factory=list)

    @property
    def tax_total(self) -> Decimal:
        return sum((t.amount for t in self.taxes), Decimal("0.00"))

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.tax_total

    def lines(self, lang: str = "en") -> list[str]:
        """Invoice-ready lines, e.g. ['Subtotal: 100.00', 'HST (15%): 15.00', 'Total: 115.00']."""
        words = {"en": ("Subtotal", "Total"), "fr": ("Sous-total", "Total")}[lang if lang == "fr" else "en"]
        out = [f"{words[0]}: {self.subtotal}"]
        out += [f"{t.label(lang)} ({_pct(t.percent)}%): {t.amount}" for t in self.taxes]
        out.append(f"{words[1]}: {self.total}")
        return out


def _pct(p: Decimal) -> str:
    return format(p.normalize(), "f")


def _province(code: str) -> str:
    c = (code or "").strip().upper()
    if c not in PROVINCES:
        raise ValueError(f"unknown province or territory {code!r}; use one of {', '.join(PROVINCES)}")
    return c


def _money(value) -> Decimal:
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"not an amount: {value!r}") from None
    if not d.is_finite():
        raise ValueError(f"not an amount: {value!r}")
    return d


def rates(province: str, on: dt.date | None = None) -> list[Rate]:
    """The taxes that applied in `province` on date `on` (default: today)."""
    p = _province(province)
    day = on or dt.date.today()
    if day < EARLIEST_DATE:
        raise ValueError(f"rates are only tabulated from {EARLIEST_DATE.isoformat()}")
    vigentes = [r for desde, r in _TABLE[p] if desde <= day][-1]
    return [Rate(code, Decimal(pct)) for code, pct in vigentes.items()]


def calculate(amount, province: str, on: dt.date | None = None, tax_included: bool = False) -> Breakdown:
    """Tax breakdown for `amount` in `province`.

    With tax_included=True, `amount` is the price the customer pays; the subtotal
    is worked out so that subtotal + rounded taxes adds up to exactly that price.
    """
    p = _province(province)
    value = _money(amount)
    rs = rates(p, on)
    if not tax_included:
        subtotal = value.quantize(CENT, ROUND_HALF_UP)
        taxes = [Tax(r.code, r.percent, (subtotal * r.percent / 100).quantize(CENT, ROUND_HALF_UP)) for r in rs]
        return Breakdown(p, subtotal, taxes)

    gross = value.quantize(CENT, ROUND_HALF_UP)
    total_pct = sum((r.percent for r in rs), Decimal(0))
    subtotal = (gross / (1 + total_pct / 100)).quantize(CENT, ROUND_HALF_UP)
    taxes = [Tax(r.code, r.percent, (subtotal * r.percent / 100).quantize(CENT, ROUND_HALF_UP)) for r in rs]
    # Rounding can leave the sum a cent off the price paid: absorb it in the largest tax line.
    diff = gross - (subtotal + sum(t.amount for t in taxes))
    if diff and taxes:
        i = max(range(len(taxes)), key=lambda k: taxes[k].percent)
        taxes[i] = Tax(taxes[i].code, taxes[i].percent, taxes[i].amount + diff)
    return Breakdown(p, subtotal, taxes)
