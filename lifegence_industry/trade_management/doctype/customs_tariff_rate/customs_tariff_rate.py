import frappe
from frappe.model.document import Document


class CustomsTariffRate(Document):
	def validate(self):
		self.validate_dates()

	def validate_dates(self):
		if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
			frappe.throw("Effective To date must be after Effective From date.")
