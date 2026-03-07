# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

import csv
import io

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def export_receipt_csv(batch_id):
	"""Export receipts in a batch to CSV format.

	Format:
	- Header record: clinic info
	- Receipt common record per patient
	- Service detail records
	- Diagnosis records
	"""
	batch = frappe.get_doc("Receipt Batch", batch_id)
	settings = frappe.get_single("Medical Receipt Settings")

	receipts = frappe.get_all(
		"Receipt",
		filters={"receipt_batch": batch_id},
		fields=["name"],
		order_by="name",
	)

	if not receipts:
		frappe.throw("エクスポートするレセプトがありません")

	output = io.StringIO()
	writer = csv.writer(output)

	# Header record
	writer.writerow([
		"HE",
		settings.clinic_code or "",
		settings.clinic_name or "",
		settings.clinic_prefecture or "",
		settings.clinic_address or "",
		batch.batch_year,
		batch.batch_month,
		settings.submission_method or "電子",
	])

	for r in receipts:
		receipt = frappe.get_doc("Receipt", r.name)
		insurance = frappe.get_doc("Patient Insurance Info", receipt.patient_insurance)

		# Receipt common record
		writer.writerow([
			"RE",
			receipt.name,
			insurance.patient_name,
			insurance.patient_name_kana,
			insurance.date_of_birth,
			insurance.sex,
			insurance.insurance_type,
			insurance.insurer_number or "",
			insurance.insurance_card_id,
			insurance.member_type,
			insurance.copay_rate or "30%",
			receipt.total_points,
			receipt.total_amount,
			receipt.copay_amount,
			receipt.insurance_claim_amount,
		])

		# Service detail records
		for line in receipt.details:
			writer.writerow([
				"SI",
				receipt.name,
				line.encounter_date or "",
				line.service_code or "",
				line.service_name or "",
				line.fee_points or 0,
				line.quantity or 1,
				line.line_total_points or 0,
			])

		# Diagnosis records
		for diag in receipt.receipt_diagnoses:
			writer.writerow([
				"SY",
				receipt.name,
				diag.disease_name or "",
				diag.icd10_code or "",
				diag.diagnosis_type or "",
				diag.onset_date or "",
				diag.outcome or "",
			])

	# Footer
	writer.writerow([
		"GO",
		batch.receipt_count or len(receipts),
		batch.total_points,
		batch.total_amount,
	])

	csv_content = output.getvalue()
	output.close()

	# Save file
	file_name = f"receipt_batch_{batch.batch_year}_{batch.batch_month:02d}.csv"
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": file_name,
		"attached_to_doctype": "Receipt Batch",
		"attached_to_name": batch_id,
		"content": csv_content,
		"is_private": 1,
	})
	file_doc.save(ignore_permissions=True)

	batch.db_set("export_file", file_doc.file_url)
	batch.db_set("exported_date", now_datetime())
	batch.db_set("status", "Exported")
	frappe.db.commit()

	return {
		"batch": batch_id,
		"file_url": file_doc.file_url,
		"receipt_count": len(receipts),
	}
