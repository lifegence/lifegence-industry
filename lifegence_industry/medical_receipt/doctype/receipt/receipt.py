import frappe
from frappe.model.document import Document

from lifegence_industry.medical_receipt.utils import calculate_medical_totals


class Receipt(Document):
	def validate(self):
		self.calculate_totals()
		self._validate_claim_month()

	def on_submit(self):
		if self.status == "Draft":
			self.status = "Submitted"

	def on_cancel(self):
		self.status = "Cancelled"

	def calculate_totals(self):
		calculate_medical_totals(self, detail_field="details")

	def _validate_claim_month(self):
		if self.claim_month and (self.claim_month < 1 or self.claim_month > 12):
			frappe.throw("請求月は1から12の間である必要があります")
