# Copyright (c) 2025, Lifegence and contributors
# For license information, please see license.txt

import frappe
from typing import Dict, Any, Optional


@frappe.whitelist()
def list_unbilled_receipts(
	limit: int = 20,
	claim_year: Optional[int] = None,
	claim_month: Optional[int] = None,
	insurance_type: Optional[str] = None,
) -> Dict[str, Any]:
	"""List unbilled receipts."""
	try:
		filters = {"status": ["in", ["Draft", "Validated"]]}
		if claim_year:
			filters["claim_year"] = claim_year
		if claim_month:
			filters["claim_month"] = claim_month
		if insurance_type:
			filters["insurance_type"] = insurance_type

		receipts = frappe.get_all(
			"Receipt",
			filters=filters,
			fields=[
				"name", "patient_name", "claim_year", "claim_month",
				"insurance_type", "status", "total_points", "total_amount",
				"copay_amount", "insurance_claim_amount",
			],
			order_by="creation desc",
			limit_page_length=limit,
		)

		return {
			"success": True,
			"count": len(receipts),
			"receipts": receipts,
		}

	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def validate_receipt_for_agent(receipt_name: str) -> Dict[str, Any]:
	"""Validate a receipt and return results in standard format."""
	try:
		if not frappe.db.exists("Receipt", receipt_name):
			return {"success": False, "error": f"Receipt '{receipt_name}' does not exist"}

		if not frappe.has_permission("Receipt", "read", receipt_name):
			return {"success": False, "error": f"No read permission for Receipt '{receipt_name}'"}

		# Use the validation API if available
		try:
			from lifegence_industry.medical_receipt.api.receipt_validation import validate_receipt
			result = validate_receipt(receipt_name)
			return {"success": True, "receipt_name": receipt_name, "validation": result}
		except ImportError:
			# Fallback: just return current validation status
			receipt = frappe.get_doc("Receipt", receipt_name)
			return {
				"success": True,
				"receipt_name": receipt_name,
				"status": receipt.status,
				"validation_errors": receipt.validation_errors or "",
				"validation_warnings": receipt.validation_warnings or "",
			}

	except Exception as e:
		return {"success": False, "error": str(e)}
