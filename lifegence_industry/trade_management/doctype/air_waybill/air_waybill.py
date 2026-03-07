from frappe.model.document import Document


class AirWaybill(Document):
	def validate(self):
		self.calculate_total_charge()

	def calculate_total_charge(self):
		self.total_charge = (self.weight_charge or 0) + (self.valuation_charge or 0)
