# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class JobApplication(Document):
	def validate(self):
		if not self.privacy_consent:
			frappe.throw(_("個人情報の取り扱いへの同意が必要です。"))
		if not self.consent_datetime:
			self.consent_datetime = frappe.utils.now_datetime()
