import frappe
from frappe.model.document import Document


class PatientInsuranceInfo(Document):
	def validate(self):
		self._validate_insurer_number()
		self._validate_dates()

	def _validate_insurer_number(self):
		if self.insurance_type != "自費" and self.insurer_number:
			num = self.insurer_number.strip()
			if not (len(num) == 8 and num.isdigit()):
				frappe.throw("保険者番号は8桁の数字である必要があります")

	def _validate_dates(self):
		if self.valid_from and self.valid_to:
			if self.valid_to < self.valid_from:
				frappe.throw("資格喪失日は資格取得日より後である必要があります")
