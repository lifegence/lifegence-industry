import frappe
from frappe.model.document import Document


class ReceiptBatch(Document):
	def validate(self):
		if self.batch_month is not None and (self.batch_month < 1 or self.batch_month > 12):
			frappe.throw("請求月は1から12の間である必要があります")
