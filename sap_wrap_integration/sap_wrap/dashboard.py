"""Dashboard utilities and number card helpers for SAP Wrap."""

from __future__ import annotations

from typing import Iterable, List, Sequence

import frappe
from frappe import _
from frappe.utils import add_to_date, flt, get_datetime_str, now_datetime


def _normalize_filters(filters: Sequence | str | None) -> List:
    if not filters:
        return []
    if isinstance(filters, str):
        try:
            filters = frappe.parse_json(filters)
        except Exception:
            return []
    if isinstance(filters, (list, tuple)):
        return list(filters)
    return []


def _last_n_days_filter(days: int) -> List:
    start = add_to_date(now_datetime(), days=-abs(days))
    return [["SAP Wrap Request Log", "creation", ">=", get_datetime_str(start)]]


def _merge_filters(filters: Iterable, extra: Iterable) -> List:
    out = list(filters) if filters else []
    out.extend(list(extra) if extra else [])
    return out


@frappe.whitelist()
def get_recent_request_count(filters: Sequence | str | None = None):
    """Return request volume for the last 7 days."""

    base_filters = _merge_filters(_normalize_filters(filters), _last_n_days_filter(7))
    total = frappe.db.count("SAP Wrap Request Log", filters=base_filters)
    return {
        "value": int(total or 0),
        "fieldtype": "Int",
        "description": _("Requests logged in the last 7 days."),
    }


@frappe.whitelist()
def get_success_rate(filters: Sequence | str | None = None):
    """Return percentage of 2xx responses for the last 7 days."""

    base_filters = _merge_filters(_normalize_filters(filters), _last_n_days_filter(7))
    total = frappe.db.count("SAP Wrap Request Log", filters=base_filters)
    success_filters = _merge_filters(
        base_filters,
        [
            ["SAP Wrap Request Log", "status_code", ">=", 200],
            ["SAP Wrap Request Log", "status_code", "<", 300],
        ],
    )
    success = frappe.db.count("SAP Wrap Request Log", filters=success_filters)
    rate = 0.0
    if total:
        rate = (success or 0) * 100.0 / float(total)
    return {
        "value": flt(rate, 2),
        "fieldtype": "Percent",
        "precision": 2,
        "description": _("Share of successful calls in the last 7 days."),
    }


@frappe.whitelist()
def get_avg_response_time(filters: Sequence | str | None = None):
    """Return average response time (ms) for the last 7 days."""

    base_filters = _merge_filters(_normalize_filters(filters), _last_n_days_filter(7))
    result = frappe.db.get_all(
        "SAP Wrap Request Log",
        filters=base_filters,
        fields=["avg(response_time_ms) as avg_response"],
        as_list=False,
    )
    avg = result[0].get("avg_response") if result else 0
    avg = flt(avg or 0, 2)
    return {
        "value": avg,
        "fieldtype": "Float",
        "precision": 2,
        "description": _("Average API response time (ms) in the last 7 days."),
    }
