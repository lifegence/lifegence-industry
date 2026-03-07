import frappe
from frappe.model.document import Document


class MedicalServiceMaster(Document):
	def validate(self):
		if self.fee_points is not None and self.fee_points < 0:
			frappe.throw("点数は0以上である必要があります")
		if self.effective_from and self.effective_to:
			if self.effective_to < self.effective_from:
				frappe.throw("適用終了日は適用開始日より後である必要があります")
