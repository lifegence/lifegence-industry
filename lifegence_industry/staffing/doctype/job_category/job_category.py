# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class JobCategory(Document):
	def validate(self):
		if self.parent_category == self.name:
			frappe.throw(frappe._("A category cannot be its own parent."))
