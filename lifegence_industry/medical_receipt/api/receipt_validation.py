# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def validate_receipt(receipt_id):
	"""Run validation checks on a Receipt and log results."""
	receipt = frappe.get_doc("Receipt", receipt_id)

	# Clear previous logs
	frappe.db.delete("Receipt Validation Log", {"receipt": receipt_id})

	errors = 0
	warnings = 0

	def _log(log_type, check_name, message):
		nonlocal errors, warnings
		if log_type == "Error":
			errors += 1
		elif log_type == "Warning":
			warnings += 1

		frappe.get_doc({
			"doctype": "Receipt Validation Log",
			"receipt": receipt_id,
			"log_type": log_type,
			"check_name": check_name,
			"checked_by": frappe.session.user,
			"checked_date": now_datetime(),
			"message": message,
		}).insert(ignore_permissions=True)

	# Check 1: Details exist
	if not receipt.details or len(receipt.details) == 0:
		_log("Error", "明細行チェック", "レセプトに明細行がありません")

	# Check 2: Diagnoses exist
	if not receipt.receipt_diagnoses or len(receipt.receipt_diagnoses) == 0:
		_log("Error", "傷病名チェック", "レセプトに傷病名がありません")

	# Check 3: Insurance validity
	insurance = frappe.get_doc("Patient Insurance Info", receipt.patient_insurance)
	if not insurance.is_active:
		_log("Error", "保険有効性チェック", "患者の保険情報が無効です")

	if insurance.valid_to:
		from frappe.utils import getdate, add_months, get_last_day

		claim_date = get_last_day(f"{receipt.claim_year}-{receipt.claim_month:02d}-01")
		if getdate(insurance.valid_to) < claim_date:
			_log("Error", "保険期間チェック", "請求月時点で保険資格が失効しています")

	# Check 4: Service code validity
	for line in receipt.details:
		if line.medical_service:
			service = frappe.get_doc("Medical Service Master", line.medical_service)
			if not service.is_active:
				_log(
					"Warning",
					"診療行為有効性チェック",
					f"診療行為 {service.service_name} ({service.service_code}) は無効です",
				)

	# Check 5: Points consistency
	calculated_total = sum(
		(line.fee_points or 0) * (line.quantity or 1)
		for line in receipt.details
	)
	if calculated_total != receipt.total_points:
		_log(
			"Error",
			"点数整合性チェック",
			f"計算点数 ({calculated_total}) とレセプト合計点数 ({receipt.total_points}) が一致しません",
		)

	# Update receipt validation info
	receipt.db_set("validation_errors", errors)
	receipt.db_set("validation_warnings", warnings)
	receipt.db_set("validated_by", frappe.session.user)
	receipt.db_set("validated_date", now_datetime())

	if errors == 0:
		receipt.db_set("status", "Validated")

	frappe.db.commit()

	return {
		"receipt": receipt_id,
		"errors": errors,
		"warnings": warnings,
		"status": "Validated" if errors == 0 else "Draft",
	}
