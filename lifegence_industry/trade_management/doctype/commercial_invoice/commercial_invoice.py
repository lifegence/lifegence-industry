from frappe.model.document import Document


class CommercialInvoice(Document):
	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		self.subtotal = 0
		for item in self.items:
			item.amount = (item.qty or 0) * (item.rate or 0)
			self.subtotal += item.amount

		self.total_amount = self.subtotal + (self.freight or 0) + (self.insurance or 0)
