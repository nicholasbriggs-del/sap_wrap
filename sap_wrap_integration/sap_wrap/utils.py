"""Utility helpers exposed to SAP Wrap templates."""

from __future__ import annotations

from datetime import date
import random
import string
from typing import Optional

import frappe
from frappe.utils import getdate, nowdate


def _safe_length(value: Optional[int], minimum: int = 1, maximum: int = 18) -> int:
    try:
        length = int(value)
    except (TypeError, ValueError):
        length = minimum
    return max(minimum, min(length, maximum))


def random_digits(length: int = 6) -> str:
    """Return a string of random numeric characters of the given length."""

    length = _safe_length(length)
    return "".join(random.choices(string.digits, k=length))


def fiscal_year_start(company: Optional[str] = None, fmt: str = "%d.%m.%Y") -> str:
    """Return the current fiscal year's start date formatted as ``fmt`` (default DD.MM.YYYY)."""

    _ = company  # unused; kept for API symmetry
    today = getdate(nowdate())
    year = today.year
    if today.month < 4:
        year -= 1
    start = date(year, 4, 1)
    try:
        return start.strftime(fmt)
    except Exception:
        return start.strftime("%Y-%m-%d")


def fiscal_year_end(company: Optional[str] = None, fmt: str = "%d.%m.%Y") -> str:
    """Return the current fiscal year's end date formatted as ``fmt`` (default DD.MM.YYYY)."""

    _ = company
    today = getdate(nowdate())
    year = today.year
    if today.month < 4:
        year -= 1
    end = date(year + 1, 3, 31)
    try:
        return end.strftime(fmt)
    except Exception:
        return end.strftime("%Y-%m-%d")


__all__ = [
    "random_digits",
    "fiscal_year_start",
    "fiscal_year_end",
]
