import json
import time
from typing import Any, Dict
from urllib.parse import urlparse, urljoin

import frappe
import uuid
from frappe.utils.safe_exec import get_safe_globals
from frappe.utils import now_datetime, add_months, cint

from . import utils as sap_utils
from .context import wrap_doc_for_template


def _file_b64(value: str) -> str:
    if not value:
        return ""
    try:
        name = None
        if value.startswith("/files") or value.startswith("http") or value.startswith("/private/files"):
            name = frappe.db.get_value("File", {"file_url": value}, "name")
        else:
            name = value
        if not name:
            return ""
        file_doc = frappe.get_doc("File", name)
        content, _ = file_doc.get_content()
        if isinstance(content, bytes):
            raw = content
        else:
            raw = content.encode("utf-8")
        import base64

        return base64.b64encode(raw).decode("utf-8")
    except Exception:
        return ""


def _get_context(doc):
    return {
        "doc": wrap_doc_for_template(doc),
        "utils": get_safe_globals().get("frappe").get("utils"),
        "file_b64": _file_b64,
        "random_digits": sap_utils.random_digits,
        "fiscal_year_start": sap_utils.fiscal_year_start,
        "fiscal_year_end": sap_utils.fiscal_year_end,
    }


def _get_all_sap_wraps():
    wraps = frappe.get_all(
        "SAP Wrap",
        fields=[
            "name",
            "enabled",
            "target_doctype",
            "doc_event",
            "condition",
            "is_dynamic_url",
            "request_method",
            "endpoint_url",
            "timeout",
            "retry_count",
            "retry_interval",
            "request_body_template",
            "update_field_map",
            "background_jobs_queue",
            "api_endpoint",
        ],
        filters={"enabled": 1},
    )

    # map per doctype
    out = {}
    for w in wraps:
        out.setdefault(w.target_doctype, []).append(w)
    return out


def run_sap_wraps(doc, method):
    frappe_flags = frappe.local.flags
    if (
        frappe_flags.in_import
        or frappe_flags.in_patch
        or frappe_flags.in_install
        or frappe_flags.in_migrate
    ):
        return

    wraps_map = frappe.cache.get_value("sap_wraps", _get_all_sap_wraps)
    wraps_for_doc = wraps_map.get(doc.doctype)
    if not wraps_for_doc:
        return

    event_list = [
        "on_update",
        "after_insert",
        "on_submit",
        "on_cancel",
        "on_trash",
    ]
    if not doc.flags.in_insert:
        event_list.append("on_change")
        event_list.append("on_update_after_submit")

    for w in wraps_for_doc:
        trigger = False
        event = method if method in event_list else None
        if not w.condition:
            trigger = True
        else:
            try:
                trigger = frappe.safe_eval(w.condition, eval_locals=_get_context(doc))
            except Exception:
                trigger = False

        if trigger and event and w.doc_event == event:
            _add_to_queue(w, doc)


def _add_to_queue(wrap, doc):
    if not getattr(frappe.local, "_sap_wrap_queue", None):
        frappe.local._sap_wrap_queue = []
        frappe.db.after_commit.add(flush_queue)

    frappe.local._sap_wrap_queue.append(frappe._dict(doc=doc, wrap=wrap))


def flush_queue():
    if not getattr(frappe.local, "_sap_wrap_queue", None):
        return

    uniq = set()
    unique_last = []
    frappe.local._sap_wrap_queue.reverse()
    for item in frappe.local._sap_wrap_queue:
        key = (item.wrap.get("name"), item.doc.get("name"))
        if key not in uniq:
            uniq.add(key)
            unique_last.append(item)

    del frappe.local._sap_wrap_queue
    unique_last.reverse()

    for item in unique_last:
        frappe.enqueue(
            "sap_wrap_integration.sap_wrap.runner.enqueue_sap_wrap",
            doc=item.doc,
            wrap=item.wrap,
            now=frappe.flags.in_test,
            queue=item.wrap.background_jobs_queue or "default",
        )


def _render_headers(doc, wrap):
    headers = {}
    if getattr(wrap, "sap_wrap_headers", None):
        for h in wrap.sap_wrap_headers:
            if h.key:
                headers[h.key] = frappe.render_template(h.value or "", _get_context(doc))
    return headers


def _render_body(doc, wrap):
    data = {}
    rendered_text = None
    if wrap.request_body_template:
        rendered_text = frappe.render_template(wrap.request_body_template, _get_context(doc))
        data = json.loads(rendered_text)
    return data, rendered_text


def _workflow_state_for_status(wrap, status_code: int) -> str | None:
    rows = getattr(wrap, "workflow_state_mappings", None) or []
    if not rows or status_code is None:
        return None
    for row in rows:
        try:
            if cint(row.status_code) == cint(status_code) and row.workflow_state:
                return row.workflow_state
        except Exception:
            continue
    return None


def _apply_workflow_state(doc, wrap, status_code: int) -> str | None:
    # Ensure we have child rows; queued wraps may be slim objects
    if (not getattr(wrap, "workflow_state_mappings", None)) and getattr(wrap, "name", None):
        try:
            wrap = frappe.get_doc("SAP Wrap", wrap.name)
        except Exception:
            pass

    rows = getattr(wrap, "workflow_state_mappings", None) or []
    state = _workflow_state_for_status(wrap, status_code)
    if not state:
        return None
    meta = getattr(doc, "meta", None)
    if not meta or not meta.has_field("workflow_state"):
        return None
    try:
        frappe.db.set_value(doc.doctype, doc.name, "workflow_state", state)
        doc.workflow_state = state
    except Exception:
        return None
    return state


def _get_value_by_path(data: Dict[str, Any], path: str):
    cur: Any = data
    for key in (path or "").split("."):
        if key == "":
            continue
        if isinstance(cur, dict):
            cur = cur.get(key)
        elif isinstance(cur, list):
            # support numeric index access for arrays
            try:
                idx = int(key)
            except Exception:
                return None
            if 0 <= idx < len(cur):
                cur = cur[idx]
            else:
                return None
        else:
            return None
    return cur


def _apply_transform(val, transform: str):
    t = (transform or "None").lower()
    try:
        if t == "to int":
            return int(val) if val is not None else None
        if t == "to float":
            return float(val) if val is not None else None
        if t == "to string":
            return "" if val is None else str(val)
        if t == "length":
            return len(val) if val is not None else 0
        if t == "digits only":
            import re
            s = "" if val is None else str(val)
            m = re.findall(r"\d+", s)
            return "".join(m) if m else ""
    except Exception:
        return val
    return val


def _collect_mappings(wrap):
    """Return normalized response mappings, loading the wrap if needed."""

    def _build(rows):
        return [
            frappe._dict(
                path=r.response_path,
                field=r.target_field,
                transform=r.transform,
                default_value=r.default_value,
                required=r.required,
                regex_pattern=getattr(r, "regex_pattern", None),
            )
            for r in rows
        ]

    rows = getattr(wrap, "response_mappings", None) or []
    if not rows and getattr(wrap, "name", None):
        try:
            full_wrap = frappe.get_doc("SAP Wrap", wrap.name)
            rows = getattr(full_wrap, "response_mappings", None) or []
        except Exception:
            rows = []
    if rows:
        return _build(rows)

    # legacy JSON map
    try:
        mappings = json.loads(getattr(wrap, "update_field_map", "") or "[]")
        return [frappe._dict(path=m.get("path"), field=m.get("field")) for m in mappings]
    except Exception:
        return []


def _update_doc_fields(doc, wrap, response_json):
    mappings = _collect_mappings(wrap)
    if not mappings:
        return
    updates = {}
    for m in mappings:
        path = m.get("path")
        field = m.get("field")
        if not path or not field:
            continue
        raw_value = _get_value_by_path(response_json, path)
        value = raw_value
        if value is None:
            value = m.get("default_value")
            if m.get("required"):
                # skip required missing for now; could raise/log
                pass
        value = _apply_transform(value, m.get("transform"))
        if (m.get("transform") or "").lower() == "regex":
            import re
            pattern = m.get("regex_pattern") or ""
            try:
                s = "" if value is None else str(value)
                grp = re.search(pattern, s)
                value = grp.group(1) if grp and grp.groups() else (grp.group(0) if grp else "")
            except Exception:
                pass
        updates[field] = value
    if updates:
        frappe.db.set_value(doc.doctype, doc.name, updates)


def compute_updates_for_response(doc, wrap, response_json):
    """Pure function to compute updates from a given response JSON without writing to DB.

    Returns a dict: { fieldname: value }
    """
    updates = {}
    mappings = _collect_mappings(wrap)
    for m in mappings:
        path = m.get("path")
        field = m.get("field")
        if not path or not field:
            continue
        value = _get_value_by_path(response_json, path)
        if value is None:
            value = m.get("default_value")
        value = _apply_transform(value, m.get("transform"))
        if (m.get("transform") or "").lower() == "regex":
            import re
            pattern = m.get("regex_pattern") or ""
            try:
                s = "" if value is None else str(value)
                grp = re.search(pattern, s)
                value = grp.group(1) if grp and grp.groups() else (grp.group(0) if grp else "")
            except Exception:
                pass
        updates[field] = value
    return updates


def _log_request(
    wrap,
    doc,
    url,
    headers,
    data,
    response_text=None,
    error_text=None,
    res=None,
    status_code=None,
    response_time_ms=None,
    ):
    # Prefer actual request headers if available
    final_headers = None
    if res is not None:
        try:
            final_headers = dict(res.request.headers)
        except Exception:
            final_headers = None
    if final_headers is None:
        final_headers = headers

    final_status_code = status_code if status_code is not None else getattr(res, "status_code", None)
    if response_time_ms is None and getattr(res, "elapsed", None):
        try:
            response_time_ms = res.elapsed.total_seconds() * 1000
        except Exception:
            response_time_ms = None

    def _as_pretty_json(payload):
        try:
            parsed = json.loads(payload) if isinstance(payload, str) else payload
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception:
            try:
                return json.dumps(payload, ensure_ascii=False)
            except Exception:
                return frappe.as_json(payload)

    if isinstance(data, str):
        request_payload = _as_pretty_json(data)
    elif data:
        try:
            request_payload = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            request_payload = _as_pretty_json(data)
    else:
        request_payload = None

    log = frappe.get_doc(
        {
            "doctype": "SAP Wrap Request Log",
            "sap_wrap": wrap.name,
            "reference_doctype": doc.doctype,
            "reference_document": doc.name,
            "user": frappe.session.user if frappe.session.user else None,
            "url": url,
            "headers": frappe.as_json(final_headers) if final_headers else None,
            "data": request_payload,
            "response": response_text,
            "error": error_text,
            "status_code": final_status_code,
            "response_time_ms": response_time_ms,
            "response_time_sec": (response_time_ms / 1000.0) if response_time_ms is not None else None,
            "created_at": now_datetime(),
        }
    )
    log.save(ignore_permissions=True)


def enqueue_sap_wrap(doc, wrap):
    # Execute in worker, normal flow (updates doc fields)
    perform_sap_call(doc, wrap, test_mode=False)


def perform_sap_call(doc, wrap, test_mode: bool = False):
    request_url = None
    headers = None
    data = None
    resp = None
    status_code = None
    response_time_ms = None
    try:
        if not hasattr(wrap, "doctype"):
            wrap = frappe.get_doc("SAP Wrap", wrap.name)

        # Optionally load API endpoint defaults
        endpoint_doc = None
        if getattr(wrap, "api_endpoint", None):
            try:
                endpoint_doc = frappe.get_doc("SAP API Endpoint", wrap.api_endpoint)
            except Exception:
                endpoint_doc = None

        # Build URL from wrap or endpoint
        raw_path_or_url = wrap.endpoint_url or (endpoint_doc.path if endpoint_doc else None)
        if not raw_path_or_url:
            raise ValueError("No endpoint URL or API Endpoint path provided")
        rendered_path_or_url = (
            frappe.render_template(raw_path_or_url, _get_context(doc)) if wrap.is_dynamic_url else raw_path_or_url
        )
        settings = (
            frappe.get_single("SAP Wrap Settings")
            if frappe.db.exists("DocType", "SAP Wrap Settings")
            else None
        )
        base_url = getattr(settings, "base_url", None) if settings else None
        if urlparse(rendered_path_or_url).scheme:
            request_url = rendered_path_or_url
        else:
            request_url = urljoin(base_url + ("/" if base_url and not base_url.endswith("/") else "") if base_url else "", rendered_path_or_url)

        # Headers: prefer wrap headers, else endpoint headers
        headers = _render_headers(doc, wrap) if getattr(wrap, "sap_wrap_headers", None) else (
            _render_headers(doc, endpoint_doc) if endpoint_doc else {}
        )
        # Trace ID
        trace_id = uuid.uuid4().hex
        headers.setdefault("frappe-trace-id", trace_id)
        # Body: prefer wrap template, else endpoint template
        if wrap.request_body_template:
            data, raw_body_text = _render_body(doc, wrap)
        elif endpoint_doc and endpoint_doc.body_template:
            class _Tmp:  # lightweight shim with request_body_template attribute
                request_body_template = endpoint_doc.body_template

            data, raw_body_text = _render_body(doc, _Tmp)
        else:
            data = {}
            raw_body_text = None

        from sap_wrap_integration.sap_wrap.client import SAPClient
        sap_client_id = (settings.sap_client_id if settings else None)
        credentials_list = (settings.credentials_list if settings else None)
        timeout = wrap.timeout or (settings.timeout if settings else None)
        csrf_fetch_timeout = (settings.csrf_fetch_timeout if settings else None)
        verify_ssl = bool(getattr(settings, "verify_ssl", 0)) if settings else False

        client = SAPClient(
            credentials_list=credentials_list,
            sap_client_id=sap_client_id,
            timeout=timeout,
            csrf_fetch_timeout=csrf_fetch_timeout,
            verify_ssl=verify_ssl,
        )

        method = (wrap.request_method or "POST").upper()
        attempts = int(wrap.retry_count or 0) + 1
        interval = int(wrap.retry_interval or 0)
        last_exc = None
        for attempt in range(attempts):
            attempt_start = time.perf_counter()
            try:
                if method == "GET":
                    resp = client.get(request_url, params=data, headers=headers, timeout=client.timeout)
                elif method == "POST":
                    resp = client.post(request_url, data=data, headers=headers, timeout=client.timeout, raw_text=raw_body_text)
                elif method == "DELETE":
                    resp = client.delete(request_url, data=data, headers=headers, timeout=client.timeout)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                status_code = getattr(resp, "status_code", None)
                response_time_ms = (time.perf_counter() - attempt_start) * 1000
                break
            except Exception as e:
                last_exc = e
                response_time_ms = (time.perf_counter() - attempt_start) * 1000
                resp = getattr(e, "response", resp)
                if resp is not None and status_code is None:
                    status_code = getattr(resp, "status_code", None)
                if attempt < attempts - 1 and interval > 0:
                    time.sleep(interval)
                else:
                    raise

        text = None
        try:
            text = resp.text
            json_resp = resp.json()
        except Exception:
            json_resp = {}
        _log_request(
            wrap,
            doc,
            request_url,
            headers,
            raw_body_text if raw_body_text is not None else data,
            response_text=text,
            res=resp,
            status_code=status_code,
            response_time_ms=response_time_ms,
        )
        applied_state = None
        if json_resp and not test_mode:
            _update_doc_fields(doc, wrap, json_resp)
        if not test_mode:
            applied_state = _apply_workflow_state(doc, wrap, status_code)
        else:
            applied_state = _workflow_state_for_status(wrap, status_code)
        return {
            "status": "ok",
            "response_text": text,
            "response_json": json_resp,
            "applied_workflow_state": applied_state,
        }

    except Exception:
        _log_request(
            wrap,
            doc,
            request_url or (wrap.endpoint_url if wrap else None),
            headers,
            data,
            response_text=getattr(resp, "text", None) if resp else None,
            error_text=frappe.get_traceback(),
            res=resp,
            status_code=status_code,
            response_time_ms=response_time_ms,
        )
        return {
            "status": "error",
            "response_text": getattr(resp, "text", None),
            "applied_workflow_state": None,
        }


def cleanup_old_sap_wrap_request_logs(months: int = 2):
    """Delete SAP Wrap Request Logs older than the provided number of months."""
    threshold = add_months(now_datetime(), -abs(months))
    # Using direct delete for performance on large log tables
    frappe.db.delete("SAP Wrap Request Log", {"creation": ("<", threshold)})
    frappe.db.commit()
