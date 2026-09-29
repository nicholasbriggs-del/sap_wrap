import frappe
from frappe.model.document import Document


class SAPWrapWorkflowStateMap(Document):
    def validate(self):
        if not (self.status_code and isinstance(self.status_code, int)):
            frappe.throw(frappe._("Status Code is required."))
        if not (self.workflow_state or "").strip():
            frappe.throw(frappe._("Workflow State is required."))
