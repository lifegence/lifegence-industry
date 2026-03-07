# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

"""
Tests for Lifegence Medical Receipt App

Covers DocType validations, fee calculations, receipt generation,
validation checks, and export functionality.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days


def _ensure_settings():
	"""Ensure Medical Receipt Settings singleton exists with defaults."""
	if not frappe.db.exists("Medical Receipt Settings"):
		doc = frappe.new_doc("Medical Receipt Settings")
		doc.clinic_code = "1234567"
		doc.clinic_name = "テストクリニック"
		doc.clinic_prefecture = "東京都"
		doc.point_unit_price = 10
		doc.submission_deadline_day = 10
		doc.save(ignore_permissions=True)
	else:
		settings = frappe.get_single("Medical Receipt Settings")
		if not settings.clinic_code:
			settings.clinic_code = "1234567"
			settings.clinic_name = "テストクリニック"
			settings.clinic_prefecture = "東京都"
			settings.point_unit_price = 10
			settings.submission_deadline_day = 10
			settings.save(ignore_permissions=True)


def _create_fee_schedule_revision():
	"""Create a test Fee Schedule Revision."""
	name = "令和6年度改定"
	if frappe.db.exists("Fee Schedule Revision", name):
		return frappe.get_doc("Fee Schedule Revision", name)
	doc = frappe.get_doc({
		"doctype": "Fee Schedule Revision",
		"revision_name": name,
		"effective_date": "2024-04-01",
		"is_active": 1,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _create_patient_insurance(card_id="INS-TEST-001", copay="30%"):
	"""Create a test Patient Insurance Info."""
	if frappe.db.exists("Patient Insurance Info", card_id):
		return frappe.get_doc("Patient Insurance Info", card_id)
	doc = frappe.get_doc({
		"doctype": "Patient Insurance Info",
		"patient_name": "テスト太郎",
		"patient_name_kana": "テストタロウ",
		"date_of_birth": "1980-01-01",
		"sex": "男",
		"insurance_type": "社保",
		"insurer_number": "12345678",
		"insurance_card_id": card_id,
		"member_type": "本人",
		"copay_rate": copay,
		"valid_from": "2024-01-01",
		"is_active": 1,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _create_service(code="SVC001", name="初診料", points=288, category="初再診"):
	"""Create a test Medical Service Master."""
	if frappe.db.exists("Medical Service Master", code):
		return frappe.get_doc("Medical Service Master", code)
	doc = frappe.get_doc({
		"doctype": "Medical Service Master",
		"service_code": code,
		"service_name": name,
		"service_category": category,
		"fee_points": points,
		"effective_from": "2024-04-01",
		"is_active": 1,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _create_disease(code="DIS001", name="高血圧症", icd10="I10"):
	"""Create a test Disease Master."""
	if frappe.db.exists("Disease Master", code):
		return frappe.get_doc("Disease Master", code)
	doc = frappe.get_doc({
		"doctype": "Disease Master",
		"disease_code": code,
		"disease_name": name,
		"icd10_code": icd10,
		"disease_category": "主病",
		"is_active": 1,
	})
	doc.insert(ignore_permissions=True)
	return doc


def _cleanup_test_data():
	"""Remove test data for clean state."""
	# Clean all encounters (test environment only)
	for enc in frappe.get_all("Patient Encounter", pluck="name"):
		doc = frappe.get_doc("Patient Encounter", enc)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Patient Encounter", enc, force=True)

	# Clean all receipts
	for r in frappe.get_all("Receipt", pluck="name"):
		doc = frappe.get_doc("Receipt", r)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Receipt", r, force=True)

	# Clean batches
	for b in frappe.get_all("Receipt Batch", pluck="name"):
		frappe.delete_doc("Receipt Batch", b, force=True)

	# Clean validation logs
	frappe.db.delete("Receipt Validation Log", {})

	frappe.db.commit()


# ─── Medical Receipt Settings Tests ─────────────────────────────────────────


class TestMedicalReceiptSettings(FrappeTestCase):
	def setUp(self):
		_ensure_settings()

	def test_valid_clinic_code(self):
		"""Settings accept a valid 7-digit clinic code."""
		settings = frappe.get_single("Medical Receipt Settings")
		settings.clinic_code = "1234567"
		settings.save(ignore_permissions=True)
		self.assertEqual(settings.clinic_code, "1234567")

	def test_invalid_clinic_code_rejected(self):
		"""Settings reject non-7-digit clinic codes."""
		settings = frappe.get_single("Medical Receipt Settings")
		settings.clinic_code = "12345"
		self.assertRaises(frappe.ValidationError, settings.save)

	def test_default_point_unit_price(self):
		"""Default point unit price is 10."""
		settings = frappe.get_single("Medical Receipt Settings")
		self.assertEqual(settings.point_unit_price, 10)


# ─── Patient Insurance Info Tests ────────────────────────────────────────────


class TestPatientInsuranceInfo(FrappeTestCase):
	def setUp(self):
		# Clean up any previous test insurance
		for card_id in ["INS-VAL-001", "INS-VAL-002", "INS-VAL-003", "INS-VAL-004"]:
			if frappe.db.exists("Patient Insurance Info", card_id):
				frappe.delete_doc("Patient Insurance Info", card_id, force=True)
		frappe.db.commit()

	def tearDown(self):
		for card_id in ["INS-VAL-001", "INS-VAL-002", "INS-VAL-003", "INS-VAL-004"]:
			if frappe.db.exists("Patient Insurance Info", card_id):
				frappe.delete_doc("Patient Insurance Info", card_id, force=True)
		frappe.db.commit()

	def test_create_valid_insurance(self):
		"""Can create valid patient insurance info."""
		doc = frappe.get_doc({
			"doctype": "Patient Insurance Info",
			"patient_name": "保険テスト",
			"patient_name_kana": "ホケンテスト",
			"date_of_birth": "1990-05-15",
			"sex": "女",
			"insurance_type": "社保",
			"insurer_number": "87654321",
			"insurance_card_id": "INS-VAL-001",
			"member_type": "本人",
			"copay_rate": "30%",
			"valid_from": "2024-01-01",
		})
		doc.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Patient Insurance Info", "INS-VAL-001"))

	def test_invalid_insurer_number_rejected(self):
		"""Rejects insurer numbers that are not 8 digits."""
		doc = frappe.get_doc({
			"doctype": "Patient Insurance Info",
			"patient_name": "保険テスト",
			"patient_name_kana": "ホケンテスト",
			"date_of_birth": "1990-05-15",
			"sex": "男",
			"insurance_type": "国保",
			"insurer_number": "123",
			"insurance_card_id": "INS-VAL-002",
			"member_type": "本人",
			"valid_from": "2024-01-01",
		})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_date_consistency_check(self):
		"""Rejects valid_to before valid_from."""
		doc = frappe.get_doc({
			"doctype": "Patient Insurance Info",
			"patient_name": "日付テスト",
			"patient_name_kana": "ヒヅケテスト",
			"date_of_birth": "1985-03-20",
			"sex": "男",
			"insurance_type": "社保",
			"insurer_number": "11223344",
			"insurance_card_id": "INS-VAL-003",
			"member_type": "本人",
			"valid_from": "2025-01-01",
			"valid_to": "2024-01-01",
		})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_unique_insurance_card_id(self):
		"""Insurance card ID must be unique."""
		doc1 = frappe.get_doc({
			"doctype": "Patient Insurance Info",
			"patient_name": "ユニークA",
			"patient_name_kana": "ユニークA",
			"date_of_birth": "1990-01-01",
			"sex": "男",
			"insurance_type": "自費",
			"insurance_card_id": "INS-VAL-004",
			"member_type": "本人",
			"valid_from": "2024-01-01",
		})
		doc1.insert(ignore_permissions=True)

		doc2 = frappe.get_doc({
			"doctype": "Patient Insurance Info",
			"patient_name": "ユニークB",
			"patient_name_kana": "ユニークB",
			"date_of_birth": "1991-01-01",
			"sex": "女",
			"insurance_type": "自費",
			"insurance_card_id": "INS-VAL-004",
			"member_type": "家族",
			"valid_from": "2024-01-01",
		})
		self.assertRaises(frappe.exceptions.DuplicateEntryError, doc2.insert)


# ─── Medical Service Master Tests ────────────────────────────────────────────


class TestMedicalServiceMaster(FrappeTestCase):
	def setUp(self):
		for code in ["SVC-NEG-001", "SVC-DATE-001"]:
			if frappe.db.exists("Medical Service Master", code):
				frappe.delete_doc("Medical Service Master", code, force=True)
		frappe.db.commit()

	def tearDown(self):
		for code in ["SVC-NEG-001", "SVC-DATE-001"]:
			if frappe.db.exists("Medical Service Master", code):
				frappe.delete_doc("Medical Service Master", code, force=True)
		frappe.db.commit()

	def test_negative_fee_points_rejected(self):
		"""Rejects negative fee points."""
		doc = frappe.get_doc({
			"doctype": "Medical Service Master",
			"service_code": "SVC-NEG-001",
			"service_name": "無効サービス",
			"service_category": "初再診",
			"fee_points": -10,
			"effective_from": "2024-04-01",
		})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_effective_date_validation(self):
		"""Rejects effective_to before effective_from."""
		doc = frappe.get_doc({
			"doctype": "Medical Service Master",
			"service_code": "SVC-DATE-001",
			"service_name": "日付テストサービス",
			"service_category": "検査",
			"fee_points": 100,
			"effective_from": "2025-01-01",
			"effective_to": "2024-01-01",
		})
		self.assertRaises(frappe.ValidationError, doc.insert)


# ─── Disease Master Tests ────────────────────────────────────────────────────


class TestDiseaseMaster(FrappeTestCase):
	def setUp(self):
		for code in ["DIS-ICD-001", "DIS-ICD-002"]:
			if frappe.db.exists("Disease Master", code):
				frappe.delete_doc("Disease Master", code, force=True)
		frappe.db.commit()

	def tearDown(self):
		for code in ["DIS-ICD-001", "DIS-ICD-002"]:
			if frappe.db.exists("Disease Master", code):
				frappe.delete_doc("Disease Master", code, force=True)
		frappe.db.commit()

	def test_valid_icd10_code(self):
		"""Accepts valid ICD-10 codes."""
		doc = frappe.get_doc({
			"doctype": "Disease Master",
			"disease_code": "DIS-ICD-001",
			"disease_name": "糖尿病",
			"icd10_code": "E11",
			"disease_category": "主病",
		})
		doc.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Disease Master", "DIS-ICD-001"))

	def test_invalid_icd10_code_rejected(self):
		"""Rejects invalid ICD-10 codes."""
		doc = frappe.get_doc({
			"doctype": "Disease Master",
			"disease_code": "DIS-ICD-002",
			"disease_name": "無効傷病",
			"icd10_code": "INVALID",
			"disease_category": "副病",
		})
		self.assertRaises(frappe.ValidationError, doc.insert)


# ─── Patient Encounter Tests ─────────────────────────────────────────────────


class TestPatientEncounter(FrappeTestCase):
	def setUp(self):
		_ensure_settings()
		_cleanup_test_data()
		self.insurance = _create_patient_insurance()
		self.service1 = _create_service("SVC001", "初診料", 288, "初再診")
		self.service2 = _create_service("SVC002", "血液検査", 150, "検査")
		self.disease = _create_disease()

	def tearDown(self):
		_cleanup_test_data()

	def test_single_service_calculation(self):
		"""Calculates points correctly for a single service."""
		doc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient_insurance": self.insurance.name,
			"encounter_date": today(),
			"services": [
				{"medical_service": self.service1.name, "fee_points": 288, "quantity": 1},
			],
		})
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.total_points, 288)
		self.assertEqual(doc.total_amount, 2880)  # 288 * 10
		# 30% copay
		self.assertEqual(doc.copay_amount, 864)  # 2880 * 0.3
		self.assertEqual(doc.insurance_claim_amount, 2016)  # 2880 - 864

	def test_multiple_services_calculation(self):
		"""Calculates points correctly for multiple services."""
		doc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient_insurance": self.insurance.name,
			"encounter_date": today(),
			"services": [
				{"medical_service": self.service1.name, "fee_points": 288, "quantity": 1},
				{"medical_service": self.service2.name, "fee_points": 150, "quantity": 2},
			],
		})
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.total_points, 588)  # 288 + 150*2
		self.assertEqual(doc.total_amount, 5880)

	def test_copay_rate_calculation(self):
		"""Uses correct copay rate from patient insurance."""
		card_id = "INS-10PCT-ENC"
		if frappe.db.exists("Patient Insurance Info", card_id):
			frappe.delete_doc("Patient Insurance Info", card_id, force=True)
		insurance_10 = _create_patient_insurance(card_id, "10%")
		# Create a service with exact points we want to test (fetch_from overrides explicit values)
		svc_100 = _create_service("SVC-COPAY-100", "テスト100点", 100, "初再診")

		doc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient_insurance": insurance_10.name,
			"encounter_date": today(),
			"services": [
				{"medical_service": svc_100.name, "quantity": 1},
			],
		})
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.total_points, 100)
		self.assertEqual(doc.total_amount, 1000)
		self.assertEqual(doc.copay_amount, 100)  # 10%
		self.assertEqual(doc.insurance_claim_amount, 900)

	def test_submit_sets_status(self):
		"""Submitting encounter sets status to Submitted."""
		doc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient_insurance": self.insurance.name,
			"encounter_date": today(),
			"services": [
				{"medical_service": self.service1.name, "fee_points": 288, "quantity": 1},
			],
		})
		doc.insert(ignore_permissions=True)
		doc.submit()

		self.assertEqual(doc.status, "Submitted")
		self.assertEqual(doc.docstatus, 1)

	def test_cancel_sets_status(self):
		"""Cancelling encounter sets status to Cancelled."""
		doc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient_insurance": self.insurance.name,
			"encounter_date": today(),
			"services": [
				{"medical_service": self.service1.name, "fee_points": 288, "quantity": 1},
			],
		})
		doc.insert(ignore_permissions=True)
		doc.submit()
		doc.cancel()

		self.assertEqual(doc.status, "Cancelled")
		self.assertEqual(doc.docstatus, 2)


# ─── Receipt Tests ───────────────────────────────────────────────────────────


class TestReceipt(FrappeTestCase):
	def setUp(self):
		_ensure_settings()
		_cleanup_test_data()
		self.insurance = _create_patient_insurance()
		self.service = _create_service()

	def tearDown(self):
		_cleanup_test_data()

	def test_receipt_totals_calculation(self):
		"""Receipt calculates totals from detail lines."""
		doc = frappe.get_doc({
			"doctype": "Receipt",
			"patient_insurance": self.insurance.name,
			"claim_year": 2026,
			"claim_month": 2,
			"details": [
				{"fee_points": 288, "quantity": 1},
				{"fee_points": 150, "quantity": 2},
			],
		})
		doc.insert(ignore_permissions=True)

		self.assertEqual(doc.total_points, 588)
		self.assertEqual(doc.total_amount, 5880)

	def test_receipt_status_transitions(self):
		"""Receipt status defaults to Draft."""
		doc = frappe.get_doc({
			"doctype": "Receipt",
			"patient_insurance": self.insurance.name,
			"claim_year": 2026,
			"claim_month": 1,
		})
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.status, "Draft")


# ─── Receipt Batch Tests ────────────────────────────────────────────────────


class TestReceiptBatch(FrappeTestCase):
	def setUp(self):
		_cleanup_test_data()

	def tearDown(self):
		_cleanup_test_data()

	def test_valid_month(self):
		"""Batch with valid month is accepted."""
		doc = frappe.get_doc({
			"doctype": "Receipt Batch",
			"batch_year": 2026,
			"batch_month": 6,
		})
		doc.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Receipt Batch", doc.name))

	def test_invalid_month_rejected(self):
		"""Batch with month > 12 is rejected."""
		doc = frappe.get_doc({
			"doctype": "Receipt Batch",
			"batch_year": 2026,
			"batch_month": 13,
		})
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_invalid_month_zero_rejected(self):
		"""Batch with month = 0 is rejected."""
		doc = frappe.get_doc({
			"doctype": "Receipt Batch",
			"batch_year": 2026,
			"batch_month": 0,
		})
		self.assertRaises(frappe.ValidationError, doc.insert)


# ─── Fee Calculation API Tests ───────────────────────────────────────────────


class TestFeeCalculationAPI(FrappeTestCase):
	def setUp(self):
		_ensure_settings()
		_cleanup_test_data()
		self.insurance = _create_patient_insurance()
		self.service = _create_service()

	def tearDown(self):
		_cleanup_test_data()

	def test_calculate_fee_returns_structure(self):
		"""calculate_fee returns dict with expected keys."""
		from lifegence_industry.medical_receipt.api.fee_calculation import calculate_fee

		doc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient_insurance": self.insurance.name,
			"encounter_date": today(),
			"services": [
				{"medical_service": self.service.name, "fee_points": 288, "quantity": 1},
			],
		})
		doc.insert(ignore_permissions=True)

		result = calculate_fee(doc.name)

		self.assertIn("encounter", result)
		self.assertIn("total_points", result)
		self.assertIn("total_amount", result)
		self.assertIn("copay_amount", result)
		self.assertIn("insurance_claim_amount", result)
		self.assertEqual(result["total_points"], 288)

	def test_calculate_fee_updates_encounter(self):
		"""calculate_fee updates the encounter document."""
		from lifegence_industry.medical_receipt.api.fee_calculation import calculate_fee

		# Create a service with exact points (fetch_from overrides explicit values)
		svc_100 = _create_service("SVC-FEE-100", "テスト100点", 100, "初再診")

		doc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient_insurance": self.insurance.name,
			"encounter_date": today(),
			"services": [
				{"medical_service": svc_100.name, "quantity": 3},
			],
		})
		doc.insert(ignore_permissions=True)

		calculate_fee(doc.name)

		doc.reload()
		self.assertEqual(doc.total_points, 300)


# ─── Receipt Generation API Tests ────────────────────────────────────────────


class TestReceiptGenerationAPI(FrappeTestCase):
	def setUp(self):
		_ensure_settings()
		_cleanup_test_data()
		self.insurance = _create_patient_insurance()
		self.service = _create_service()
		self.disease = _create_disease()

	def tearDown(self):
		_cleanup_test_data()

	def test_generate_monthly_receipts_summary(self):
		"""generate_monthly_receipts returns summary with batch info."""
		from lifegence_industry.medical_receipt.api.receipt_generation import generate_monthly_receipts

		# Create and submit an encounter
		doc = frappe.get_doc({
			"doctype": "Patient Encounter",
			"patient_insurance": self.insurance.name,
			"encounter_date": "2026-02-15",
			"services": [
				{"medical_service": self.service.name, "fee_points": 288, "quantity": 1},
			],
			"diagnoses": [
				{"disease": self.disease.name, "diagnosis_type": "主病名"},
			],
		})
		doc.insert(ignore_permissions=True)
		doc.submit()

		result = generate_monthly_receipts(2026, 2)

		self.assertIn("batch", result)
		self.assertEqual(result["receipt_count"], 1)
		self.assertEqual(result["total_points"], 288)

	def test_generate_groups_by_patient(self):
		"""Monthly generation groups encounters by patient insurance."""
		from lifegence_industry.medical_receipt.api.receipt_generation import generate_monthly_receipts

		# Create a service with exact points (fetch_from overrides explicit values)
		svc_100 = _create_service("SVC-GEN-100", "テスト100点", 100, "初再診")

		# Create two encounters for the same patient
		for day in ["2026-02-10", "2026-02-20"]:
			doc = frappe.get_doc({
				"doctype": "Patient Encounter",
				"patient_insurance": self.insurance.name,
				"encounter_date": day,
				"services": [
					{"medical_service": svc_100.name, "quantity": 1},
				],
			})
			doc.insert(ignore_permissions=True)
			doc.submit()

		result = generate_monthly_receipts(2026, 2)

		# Should create only 1 receipt for 1 patient, combining both encounters
		self.assertEqual(result["receipt_count"], 1)
		self.assertEqual(result["total_points"], 200)  # 100 + 100


# ─── Receipt Validation API Tests ────────────────────────────────────────────


class TestReceiptValidationAPI(FrappeTestCase):
	def setUp(self):
		_ensure_settings()
		_cleanup_test_data()
		self.insurance = _create_patient_insurance()
		self.service = _create_service()
		self.disease = _create_disease()

	def tearDown(self):
		_cleanup_test_data()

	def test_validation_detects_no_details(self):
		"""Validation flags receipt with no detail lines."""
		from lifegence_industry.medical_receipt.api.receipt_validation import validate_receipt

		receipt = frappe.get_doc({
			"doctype": "Receipt",
			"patient_insurance": self.insurance.name,
			"claim_year": 2026,
			"claim_month": 2,
		})
		receipt.insert(ignore_permissions=True)

		result = validate_receipt(receipt.name)

		self.assertGreater(result["errors"], 0)
		self.assertEqual(result["status"], "Draft")

	def test_validation_detects_no_diagnoses(self):
		"""Validation flags receipt with no diagnoses."""
		from lifegence_industry.medical_receipt.api.receipt_validation import validate_receipt

		receipt = frappe.get_doc({
			"doctype": "Receipt",
			"patient_insurance": self.insurance.name,
			"claim_year": 2026,
			"claim_month": 2,
			"details": [
				{"fee_points": 288, "quantity": 1},
			],
		})
		receipt.insert(ignore_permissions=True)

		result = validate_receipt(receipt.name)

		# Should have error for missing diagnoses
		self.assertGreater(result["errors"], 0)

	def test_validation_passes_for_complete_receipt(self):
		"""Validation passes for a complete receipt with details and diagnoses."""
		from lifegence_industry.medical_receipt.api.receipt_validation import validate_receipt

		receipt = frappe.get_doc({
			"doctype": "Receipt",
			"patient_insurance": self.insurance.name,
			"claim_year": 2026,
			"claim_month": 2,
			"details": [
				{
					"medical_service": self.service.name,
					"fee_points": 288,
					"quantity": 1,
				},
			],
			"receipt_diagnoses": [
				{
					"disease": self.disease.name,
					"diagnosis_type": "主病名",
				},
			],
		})
		receipt.insert(ignore_permissions=True)

		result = validate_receipt(receipt.name)

		self.assertEqual(result["errors"], 0)
		self.assertEqual(result["status"], "Validated")
