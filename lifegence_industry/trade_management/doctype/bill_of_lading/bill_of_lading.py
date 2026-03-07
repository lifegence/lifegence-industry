import frappe
from frappe.model.document import Document


class BillofLading(Document):
	def validate(self):
		self.validate_bl_status_transition()

	def validate_bl_status_transition(self):
		if self.is_new():
			return

		old_status = frappe.db.get_value("Bill of Lading", self.name, "bl_status")
		if not old_status or old_status == self.bl_status:
			return

		valid_transitions = {
			"Draft": ["Original Issued"],
			"Original Issued": ["Surrendered", "Released"],
			"Surrendered": ["Released"],
			"Released": ["Accomplished"],
		}

		if self.bl_type == "Sea Waybill":
			valid_transitions["Draft"] = ["Released"]

		allowed = valid_transitions.get(old_status, [])
		if self.bl_status not in allowed:
			frappe.throw(
				f"Cannot change B/L status from {old_status} to {self.bl_status}. "
				f"Allowed transitions: {', '.join(allowed) if allowed else 'None'}"
			)
