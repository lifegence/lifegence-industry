import frappe
from frappe.model.document import Document


class MedicalReceiptSettings(Document):
	def validate(self):
		if self.clinic_code:
			code = self.clinic_code.strip()
			if not (len(code) == 7 and code.isdigit()):
				frappe.throw("医療機関コードは7桁の数字である必要があります")
