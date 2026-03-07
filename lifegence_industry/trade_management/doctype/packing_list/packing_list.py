from frappe.model.document import Document


class PackingList(Document):
	def validate(self):
		self.calculate_totals()

	def calculate_totals(self):
		self.total_packages = 0
		self.total_gross_weight = 0
		self.total_net_weight = 0
		self.total_volume = 0

		for item in self.items:
			self.total_packages += item.packages or 0
			self.total_gross_weight += item.gross_weight or 0
			self.total_net_weight += item.net_weight or 0
			self.total_volume += item.volume or 0
