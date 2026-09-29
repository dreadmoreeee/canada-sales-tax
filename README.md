# canada-sales-tax

Canadian sales tax (GST, HST, PST, QST) for any province or territory, **by date**, with **exact cents**.

```python
from canada_sales_tax import calculate

b = calculate("19.99", "QC")
b.lines()        # ['Subtotal: 19.99', 'GST (5%): 1.00', 'QST (9.975%): 1.99', 'Total: 22.98']
b.lines("fr")    # ['Sous-total: 19.99', 'TPS (5%): 1.00', 'TVQ (9.975%): 1.99', 'Total: 22.98']

calculate("115.00", "NB", tax_included=True).subtotal   # Decimal('100.00')
```

Why another tax helper:

- **Decimal, never float**, and each tax rounded to the cent separately, the way it prints on a Canadian invoice (half-up, like a till: 0.505 → 0.51).
- **Dated rates.** Nova Scotia's HST dropped from 15% to 14% on April 1, 2025; `calculate(..., on=date)` gives the rate that applied that day, so old invoices and refunds stay right.
- **Tax-included prices that add up.** From a price the customer paid, it works out the subtotal and taxes so that they sum to **exactly** that price, in every province (tested on ~2,000 prices × 13 provinces).
- **English and French labels** (GST/TPS, HST/TVH, PST/TVP, QST/TVQ) ready for invoices.
- **No dependencies.** Standard library only, Python 3.10+.

## Measured result

```
$ python -m canada_sales_tax 100 QC
Subtotal: 100.00
GST (5%): 5.00
QST (9.975%): 9.98
Total: 114.98

$ python -m canada_sales_tax 50 NS --included --lang fr
Sous-total: 43.86
TVH (14%): 6.14
Total: 50.00

$ python -m pytest -q
.........................................
41 passed in 0.15s
```

## Rates

| Province / territory | Tax |
|---|---|
| NB, NL, PE | HST 15% |
| NS | HST 14% (15% before 2025-04-01) |
| ON | HST 13% |
| QC | GST 5% + QST 9.975% |
| BC | GST 5% + PST 7% |
| MB | GST 5% + PST 7% |
| SK | GST 5% + PST 6% |
| AB, NT, NU, YT | GST 5% |

Source: Canada Revenue Agency GST/HST rates (checked September 2026). Dates from 2019-07-01 are supported; earlier dates raise `ValueError` rather than guess. This computes tax on taxable supplies; it does not decide what is exempt or zero-rated, or when PST applies to a service. Check with an accountant for those.

## API

- `calculate(amount, province, on=None, tax_included=False) -> Breakdown` with `.subtotal`, `.taxes` (code, percent, amount), `.tax_total`, `.total`, `.lines(lang)`.
- `rates(province, on=None) -> list[Rate]`
- `PROVINCES` — codes with English and French names.

## Author

Marvin Palencia, founder of [DeMark Studio](https://demarkstudio.ca), Miramichi, New Brunswick, Canada. I build websites, Stripe payment integrations and Python automations for small businesses. Portfolio: [marvin.demarkstudio.ca](https://marvin.demarkstudio.ca)

MIT License.
