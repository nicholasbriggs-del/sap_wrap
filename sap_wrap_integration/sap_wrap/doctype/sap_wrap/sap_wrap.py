import json

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint
from frappe.utils.jinja import validate_template
from frappe.utils.safe_exec import get_safe_globals
import base64

from sap_wrap_integration.sap_wrap import utils as sap_utils
from sap_wrap_integration.sap_wrap.context import wrap_doc_for_template


def _file_b64(value: str) -> str:
    if not value:
        return ""
    try:
        name = None
        if isinstance(value, str) and (value.startswith("/files") or value.startswith("http") or value.startswith("/private/files")):
            name = frappe.db.get_value("File", {"file_url": value}, "name")
        else:
            name = value
        if not name:
            return ""
        file_doc = frappe.get_doc("File", name)
        content, _ = file_doc.get_content()
        raw = content if isinstance(content, bytes) else content.encode("utf-8")
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


class SAPWrap(Document):
    def validate(self):
        # Basic validations similar to Webhook
        self._validate_request_url()
        self._validate_condition()
        self._validate_templates()
        self._validate_workflow_state_mappings()

    def on_update(self):
        # drop cache of sap wraps map
        frappe.cache.delete_value("sap_wraps")

    def _validate_request_url(self):
        if not self.endpoint_url:
            frappe.throw(_("Endpoint URL is required"))

    def _validate_condition(self):
        if self.condition and self.target_doctype:
            temp = frappe.new_doc(self.target_doctype)
            try:
                frappe.safe_eval(self.condition, eval_locals=_get_context(temp))
            except Exception as e:
                frappe.throw(_("Invalid Condition: {}".format(e)))

    def _validate_templates(self):
        if self.request_body_template:
            validate_template(self.request_body_template)
        # headers are in child table; values can include jinja and are rendered at runtime
        if self.update_field_map:
            # ensure valid JSON after simple sanity
            try:
                json.loads(self.update_field_map)
            except Exception as e:
                frappe.throw(_("Invalid Update Field Map JSON: {}".format(e)))

    def _validate_workflow_state_mappings(self):
        rows = getattr(self, "workflow_state_mappings", []) or []
        if not rows:
            return
        if not self.target_doctype:
            frappe.throw(_("Select a Target DocType before configuring workflow state mappings."))

        # Ensure the document actually has workflow_state field
        try:
            meta = frappe.get_meta(self.target_doctype)
        except frappe.DoesNotExistError:
            frappe.throw(_("Target DocType {0} not found.").format(self.target_doctype))
        if not meta.has_field("workflow_state"):
            frappe.throw(
                _("{0} does not have a workflow_state field and cannot be updated via workflow mappings.").format(
                    self.target_doctype
                )
            )

        allowed_states = set(_workflow_states_for_doctype(self.target_doctype))
        if not allowed_states:
            frappe.throw(
                _("No active workflow states found for {0}. Configure a Workflow before adding mappings.").format(
                    self.target_doctype
                )
            )

        seen = set()
        for row in rows:
            code = cint(row.status_code)
            if code in seen:
                frappe.throw(_("Duplicate status code {0} in workflow state mappings.").format(code))
            seen.add(code)
            if row.workflow_state not in allowed_states:
                if frappe.flags.in_fixtures:
                    # Fixture import order is non-deterministic; workflow fixtures may sync later.
                    continue
                frappe.throw(
                    _("Workflow state {0} is not part of the active workflow for {1}.").format(
                        row.workflow_state, self.target_doctype
                    )
                )

    @frappe.whitelist()
    def generate_preview(self):
        # No-op: virtual fields are evaluated automatically
        pass

    @property
    def meets_condition(self):
        if not self.condition:
            return _("Yes")
        if not (self.preview_document and self.target_doctype):
            return _("Select a document to check if it meets conditions.")
        try:
            doc = frappe.get_cached_doc(self.target_doctype, self.preview_document)
            met = frappe.safe_eval(self.condition, eval_locals=_get_context(doc))
        except Exception as e:
            return _("Failed to evaluate conditions: {}".format(e))
        return _("Yes") if met else _("No")

    @property
    def preview_request_body(self):
        if not (self.preview_document and self.target_doctype):
            return _("Select a document to preview request data")
        try:
            doc = frappe.get_cached_doc(self.target_doctype, self.preview_document)
            # build as runner would
            if self.request_body_template:
                rendered = frappe.render_template(self.request_body_template, _get_context(doc))
                # return raw rendered string to preserve key order
                return rendered
            else:
                return _("No request body template configured")
        except Exception as e:
            return _("Failed to compute request body: {}".format(e))


@frappe.whitelist()
def load_last_response(name: str, docname: str) -> dict:
    wrap = frappe.get_doc("SAP Wrap", name)
    log = frappe.get_all(
        "SAP Wrap Request Log",
        filters={"sap_wrap": wrap.name, "reference_document": docname},
        fields=["name", "response", "modified"],
        order_by="modified desc",
        limit=1,
    )
    if not log:
        return {}
    try:
        return json.loads(log[0]["response"] or "{}")
    except Exception:
        return {"_raw": log[0]["response"]}


@frappe.whitelist()
def get_file_base64(file_name: str) -> str:
    # kept for compatibility; not used in new tool flow
    return _file_b64(file_name)


@frappe.whitelist()
def test_execute(name: str, docname: str):
    """Execute the configured SAP Wrap against a specific document in test mode."""
    wrap = frappe.get_doc("SAP Wrap", name)
    doc = frappe.get_doc(wrap.target_doctype, docname)
    from sap_wrap_integration.sap_wrap.runner import perform_sap_call

    return perform_sap_call(doc, wrap, test_mode=True)


@frappe.whitelist()
def load_endpoint_defaults(api_endpoint: str) -> dict:
    """Return defaults from SAP API Endpoint to populate SAP Wrap fields."""
    ep = frappe.get_doc("SAP API Endpoint", api_endpoint)
    headers = []
    for h in getattr(ep, "headers", []) or []:
        if h.key:
            headers.append({"key": h.key, "value": h.value or ""})
    return {
        "request_method": ep.method,
        "endpoint_url": ep.path,
        "headers": headers,
        "request_body_template": ep.body_template or "",
        "response_sample": ep.response_sample or "",
    }


@frappe.whitelist()
def get_response_samples(name: str, docname: str) -> dict:
    """Return response samples from linked endpoint and last execution log."""
    wrap = frappe.get_doc("SAP Wrap", name)
    endpoint_sample = None
    if wrap.api_endpoint:
        try:
            ep = frappe.get_doc("SAP API Endpoint", wrap.api_endpoint)
            endpoint_sample = ep.response_sample
        except Exception:
            endpoint_sample = None
    last = load_last_response(name, docname)
    return {"endpoint_sample": endpoint_sample, "last_response": last}


@frappe.whitelist()
def test_mapping(name: str, docname: str):
    """Compute mapping output against last logged response (without updating the document)."""
    wrap = frappe.get_doc("SAP Wrap", name)
    # Prefer last response from logs
    last = load_last_response(name, docname)
    if not last:
        return {"updates": {}, "info": "No last response found in logs for this document."}
    from sap_wrap_integration.sap_wrap.runner import compute_updates_for_response

    updates = compute_updates_for_response(frappe.get_doc(wrap.target_doctype, docname), wrap, last)
    return {"updates": updates}


def _workflow_states_for_doctype(document_type: str) -> list[str]:
    if not document_type:
        return []
    workflows = frappe.get_all(
        "Workflow",
        filters={"document_type": document_type, "is_active": 1},
        fields=["name"],
    )
    if not workflows:
        return []
    workflow_names = [wf.name for wf in workflows]
    states = frappe.get_all(
        "Workflow Document State",
        filters={"parent": ("in", workflow_names)},
        pluck="state",
        distinct=True,
    )
    return sorted(states)


@frappe.whitelist()
def get_workflow_states(document_type: str) -> list[str]:
    """Return list of workflow states available for the provided DocType."""

    return _workflow_states_for_doctype(document_type)
