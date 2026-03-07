import re

import frappe
from frappe.model.document import Document


class DiseaseMaster(Document):
	def validate(self):
		if self.icd10_code:
			pattern = r"^[A-Z]\d{2}(\.\d{1,2})?$"
			if not re.match(pattern, self.icd10_code.strip()):
				frappe.throw("ICD-10コードの形式が正しくありません（例: A01, B02.1）")
