"""python -m canada_sales_tax 100 NB [--included] [--on 2025-03-31] [--lang fr]"""
import argparse
import datetime as dt
import sys

from canada_sales_tax import PROVINCES, calculate


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="canada_sales_tax", description="Canadian GST/HST/PST/QST for an amount.")
    p.add_argument("amount")
    p.add_argument("province", help=", ".join(PROVINCES))
    p.add_argument("--included", action="store_true", help="the amount already includes tax")
    p.add_argument("--on", type=dt.date.fromisoformat, help="date (YYYY-MM-DD); default today")
    p.add_argument("--lang", choices=("en", "fr"), default="en")
    a = p.parse_args(argv)
    try:
        b = calculate(a.amount, a.province, on=a.on, tax_included=a.included)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print("\n".join(b.lines(a.lang)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
