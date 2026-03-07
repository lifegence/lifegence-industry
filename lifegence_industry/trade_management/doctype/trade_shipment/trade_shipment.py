import frappe
from frappe.model.document import Document
from frappe.utils import flt


class TradeShipment(Document):
	def before_naming(self, set_name=None, force=False):
		if self.shipment_type == "Export":
			self.naming_series = "TS-EXP-.YYYY.-"
		elif self.shipment_type == "Import":
			self.naming_series = "TS-IMP-.YYYY.-"

	def validate(self):
		self.calculate_totals()
		self.calculate_charges()
		self.set_party_names()

	def calculate_totals(self):
		self.total_packages = 0
		self.total_gross_weight = 0
		self.total_net_weight = 0
		self.total_volume = 0
		self.total_value = 0

		for item in self.get("items", []):
			item.amount = flt(item.qty) * flt(item.rate)
			self.total_packages += flt(item.packages)
			self.total_gross_weight += flt(item.gross_weight)
			self.total_net_weight += flt(item.net_weight)
			self.total_volume += flt(item.volume)
			self.total_value += flt(item.amount)

	def calculate_charges(self):
		self.total_charges = 0
		for charge in self.get("charges", []):
			charge.amount_company_currency = flt(charge.amount) * flt(charge.exchange_rate or 1)
			self.total_charges += flt(charge.amount_company_currency)

	def set_party_names(self):
		if self.shipper and not self.shipper_name:
			self.shipper_name = self.shipper
		if self.consignee and not self.consignee_name:
			self.consignee_name = self.consignee

	def on_submit(self):
		if self.status == "Draft":
			self.db_set("status", "Booked")

	def on_cancel(self):
		self.db_set("status", "Cancelled")
