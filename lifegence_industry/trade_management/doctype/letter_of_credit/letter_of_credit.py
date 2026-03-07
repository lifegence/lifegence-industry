import frappe
from frappe.model.document import Document


class LetterofCredit(Document):
	def validate(self):
		self.calculate_balance()
		self.validate_expiry()

	def calculate_balance(self):
		self.balance = (self.lc_amount or 0) - (self.drawn_amount or 0)

	def validate_expiry(self):
		if self.expiry_date and self.date_of_issue and self.expiry_date < self.date_of_issue:
			frappe.throw("Expiry Date must be after Date of Issue.")

	@frappe.whitelist()
	def draw(self, amount):
		"""Record a drawing against this L/C."""
		amount = float(amount)
		if amount <= 0:
			frappe.throw("Drawing amount must be positive.")

		new_drawn = (self.drawn_amount or 0) + amount
		tolerance = 1 + (self.tolerance_percentage or 0) / 100
		max_amount = (self.lc_amount or 0) * tolerance

		if new_drawn > max_amount:
			frappe.throw(
				f"Drawing amount {amount} exceeds available balance. "
				f"Max drawable: {max_amount - (self.drawn_amount or 0)}"
			)

		self.drawn_amount = new_drawn
		self.balance = (self.lc_amount or 0) - self.drawn_amount

		if self.drawn_amount >= self.lc_amount:
			self.status = "Fully Drawn"
		else:
			self.status = "Partially Drawn"

		self.save()
