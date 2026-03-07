import frappe
from frappe.model.document import Document


class CustomsDeclaration(Document):
	def before_naming(self):
		if self.declaration_type in ("Export", "Re-Export"):
			self.naming_series = "CD-EXP-.YYYY.-"
		else:
			self.naming_series = "CD-IMP-.YYYY.-"

	def validate(self):
		self.calculate_duty_and_taxes()

	def on_submit(self):
		self.db_set("status", "Submitted")

	def on_cancel(self):
		self.db_set("status", "Cancelled")

	def calculate_duty_and_taxes(self):
		self.total_duty = 0
		self.total_consumption_tax = 0

		for item in self.items:
			item.duty_amount = (item.customs_value or 0) * (item.duty_rate or 0) / 100
			if item.preferential_rate is not None and item.preferential_rate > 0:
				item.duty_amount = (item.customs_value or 0) * (item.preferential_rate or 0) / 100

			item.consumption_tax_amount = (
				(item.customs_value or 0) + (item.duty_amount or 0)
			) * (item.consumption_tax_rate or 0) / 100

			self.total_duty += item.duty_amount or 0
			self.total_consumption_tax += item.consumption_tax_amount or 0

		# Local consumption tax = 22/78 of consumption tax (Japanese tax law)
		self.total_local_tax = self.total_consumption_tax * 22 / 78 if self.total_consumption_tax else 0
		self.total_taxes = (self.total_duty or 0) + (self.total_consumption_tax or 0) + (self.total_local_tax or 0)

	@frappe.whitelist()
	def approve(self):
		"""Approve the customs declaration and optionally generate LCV."""
		if self.docstatus != 1:
			frappe.throw("Customs Declaration must be submitted before approval.")

		self.db_set("status", "Approved")
		self.db_set("permission_date", frappe.utils.today())

		# Auto-generate Landed Cost Voucher for import declarations
		if self.declaration_type in ("Import", "Re-Import"):
			self.create_landed_cost_voucher()

	@frappe.whitelist()
	def reject(self):
		"""Reject the customs declaration."""
		if self.docstatus != 1:
			frappe.throw("Customs Declaration must be submitted before rejection.")
		self.db_set("status", "Rejected")

	def create_landed_cost_voucher(self):
		"""Create Landed Cost Voucher from customs duty and taxes."""
		ts = frappe.get_doc("Trade Shipment", self.trade_shipment)

		# Need a Purchase Receipt linked to the Trade Shipment
		if not ts.purchase_receipt:
			frappe.msgprint(
				"No Purchase Receipt linked to Trade Shipment. "
				"Landed Cost Voucher not created automatically.",
				alert=True,
			)
			return

		company = ts.company

		lcv = frappe.get_doc({
			"doctype": "Landed Cost Voucher",
			"company": company,
			"posting_date": frappe.utils.today(),
			"purchase_receipts": [{
				"receipt_document_type": "Purchase Receipt",
				"receipt_document": ts.purchase_receipt,
				"supplier": frappe.db.get_value("Purchase Receipt", ts.purchase_receipt, "supplier"),
				"grand_total": frappe.db.get_value("Purchase Receipt", ts.purchase_receipt, "grand_total"),
			}],
			"taxes": [],
		})

		# Add customs duty as a landed cost tax
		if self.total_duty:
			lcv.append("taxes", {
				"expense_account": self._get_expense_account(company, "Customs Duty"),
				"description": f"Customs Duty - {self.name}",
				"amount": self.total_duty,
			})

		# Add consumption tax as a landed cost tax
		if self.total_consumption_tax:
			lcv.append("taxes", {
				"expense_account": self._get_expense_account(company, "Consumption Tax"),
				"description": f"Consumption Tax - {self.name}",
				"amount": self.total_consumption_tax,
			})

		if not lcv.taxes:
			return

		lcv.insert(ignore_permissions=True)
		self.db_set("landed_cost_voucher", lcv.name)
		frappe.msgprint(f"Landed Cost Voucher {lcv.name} created.", alert=True)

	def _get_expense_account(self, company, charge_type):
		"""Get expense account for the given charge type from Trade Charges or default."""
		# Try to find from Trade Shipment charges
		ts_charges = frappe.get_all(
			"Trade Charge",
			filters={"parent": self.trade_shipment, "charge_type": charge_type},
			fields=["account"],
			limit=1,
		)
		if ts_charges and ts_charges[0].account:
			return ts_charges[0].account

		# Fallback to default expense account
		default_account = frappe.db.get_value(
			"Company", company, "default_expense_account"
		)
		return default_account or frappe.db.get_value(
			"Account",
			{"company": company, "account_type": "Expense Account", "is_group": 0},
			"name",
		)
