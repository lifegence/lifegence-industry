# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, now_datetime, today


@frappe.whitelist()
def generate_monthly_receipts(year, month):
	"""Generate receipts for all submitted encounters in a given month.

	1. Create Receipt Batch
	2. Get submitted encounters for the month
	3. Group by patient_insurance
	4. Create Receipt per patient with aggregated detail lines and diagnoses
	5. Update batch statistics
	"""
	year = int(year)
	month = int(month)

	if month < 1 or month > 12:
		frappe.throw("月は1から12の間である必要があります")

	# 1. Create batch
	batch = frappe.get_doc({
		"doctype": "Receipt Batch",
		"batch_year": year,
		"batch_month": month,
		"status": "Draft",
	})
	batch.insert()

	# 2. Get submitted encounters for the month
	encounters = frappe.get_all(
		"Patient Encounter",
		filters={
			"encounter_date": ["between", [f"{year}-{month:02d}-01", f"{year}-{month:02d}-31"]],
			"docstatus": 1,
		},
		fields=["name", "patient_insurance"],
	)

	if not encounters:
		batch.status = "Generated"
		batch.receipt_count = 0
		batch.save()
		frappe.db.commit()
		return {
			"batch": batch.name,
			"receipt_count": 0,
			"total_points": 0,
			"total_amount": 0,
		}

	# 3. Group by patient_insurance
	grouped = {}
	for enc in encounters:
		grouped.setdefault(enc.patient_insurance, []).append(enc.name)

	# 4. Create receipt per patient
	total_batch_points = 0
	total_batch_amount = 0
	receipt_count = 0

	settings = frappe.get_single("Medical Receipt Settings")

	for patient_insurance, encounter_names in grouped.items():
		insurance = frappe.get_doc("Patient Insurance Info", patient_insurance)

		receipt = frappe.get_doc({
			"doctype": "Receipt",
			"patient_insurance": patient_insurance,
			"claim_year": year,
			"claim_month": month,
			"insurance_type": insurance.insurance_type,
			"status": "Draft",
			"receipt_batch": batch.name,
		})

		# Collect all service lines and diagnoses from encounters
		seen_diagnoses = set()

		for enc_name in encounter_names:
			enc_doc = frappe.get_doc("Patient Encounter", enc_name)

			for line in enc_doc.services:
				receipt.append("details", {
					"encounter": enc_name,
					"encounter_date": enc_doc.encounter_date,
					"medical_service": line.medical_service,
					"service_name": line.service_name,
					"service_code": line.service_code,
					"fee_points": line.fee_points,
					"quantity": line.quantity,
					"line_total_points": line.line_total_points,
				})

			for diag in enc_doc.diagnoses:
				diag_key = (diag.disease, diag.diagnosis_type)
				if diag_key not in seen_diagnoses:
					seen_diagnoses.add(diag_key)
					receipt.append("receipt_diagnoses", {
						"disease": diag.disease,
						"disease_name": diag.disease_name,
						"icd10_code": diag.icd10_code,
						"diagnosis_type": diag.diagnosis_type,
						"onset_date": diag.onset_date,
						"outcome": diag.outcome,
					})

		receipt.insert()

		total_batch_points += receipt.total_points
		total_batch_amount += flt(receipt.total_amount)
		receipt_count += 1

		# Mark encounters as billed
		for enc_name in encounter_names:
			frappe.db.set_value("Patient Encounter", enc_name, "status", "Billed")

	# Auto-validate if setting is enabled
	if settings.auto_validate_on_generate:
		from lifegence_industry.medical_receipt.api.receipt_validation import validate_receipt

		error_count = 0
		receipts = frappe.get_all("Receipt", filters={"receipt_batch": batch.name})
		for r in receipts:
			result = validate_receipt(r.name)
			error_count += result.get("errors", 0)
		batch.db_set("error_count", error_count)

	# 5. Update batch statistics
	batch.db_set("receipt_count", receipt_count)
	batch.db_set("total_points", total_batch_points)
	batch.db_set("total_amount", total_batch_amount)
	batch.db_set("status", "Generated")

	frappe.db.commit()

	return {
		"batch": batch.name,
		"receipt_count": receipt_count,
		"total_points": total_batch_points,
		"total_amount": total_batch_amount,
	}


def send_deadline_reminder():
	"""Scheduler job: Send reminder on the 5th of each month about submission deadline."""
	settings = frappe.get_single("Medical Receipt Settings")
	deadline_day = settings.submission_deadline_day or 10

	from frappe.utils import getdate

	current_date = getdate(today())
	year = current_date.year
	month = current_date.month

	# Check for un-submitted batches for current month
	pending_batches = frappe.get_all(
		"Receipt Batch",
		filters={
			"batch_year": year,
			"batch_month": month,
			"status": ["not in", ["Submitted", "Exported"]],
		},
		fields=["name", "status", "receipt_count"],
	)

	if pending_batches:
		admins = frappe.get_all(
			"Has Role",
			filters={"role": "System Manager", "parenttype": "User"},
			fields=["parent"],
		)
		for admin in admins:
			frappe.sendmail(
				recipients=[admin.parent],
				subject=f"レセプト提出期限リマインダー ({year}年{month}月)",
				message=(
					f"<p>{year}年{month}月のレセプト提出期限は{deadline_day}日です。</p>"
					f"<p>未提出のバッチが{len(pending_batches)}件あります。</p>"
				),
			)
