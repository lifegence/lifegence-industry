import frappe
from frappe.model.document import Document
from frappe.utils import flt


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
		total_points = 0
		for line in self.details:
			line.line_total_points = (line.fee_points or 0) * (line.quantity or 1)
			total_points += line.line_total_points

		self.total_points = total_points

		settings = frappe.get_single("Medical Receipt Settings")
		unit_price = flt(settings.point_unit_price) or 10
		self.total_amount = self.total_points * unit_price

		insurance = frappe.get_doc("Patient Insurance Info", self.patient_insurance)
		copay_rate_str = insurance.copay_rate or "30%"
		copay_rate = flt(copay_rate_str.replace("%", "")) / 100

		self.copay_amount = flt(self.total_amount * copay_rate, 0)
		self.insurance_claim_amount = flt(self.total_amount - self.copay_amount, 0)

	def _validate_claim_month(self):
		if self.claim_month and (self.claim_month < 1 or self.claim_month > 12):
			frappe.throw("請求月は1から12の間である必要があります")
