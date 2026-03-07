import frappe
from frappe.model.document import Document


class PortMaster(Document):
	def autoname(self):
		if self.port_code:
			self.port_code = self.port_code.upper().strip()
			self.name = self.port_code

	def validate(self):
		if self.port_code:
			self.port_code = self.port_code.upper().strip()
		if self.port_code and len(self.port_code) != 5:
			frappe.throw("Port Code (UN/LOCODE) must be exactly 5 characters (e.g., JPYOK).")
