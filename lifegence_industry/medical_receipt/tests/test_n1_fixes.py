"""Tests verifying N+1 query fixes in receipt_generation and receipt_validation.

Uses unittest.mock to verify batch query patterns without a live database.
"""

import unittest
from unittest.mock import patch, MagicMock, call
from datetime import datetime


class TestReceiptGenerationBatchQueries(unittest.TestCase):
	"""Verify receipt_generation uses batch queries for child tables."""

	@patch("lifegence_industry.medical_receipt.api.receipt_generation.frappe")
	def test_no_get_doc_for_encounters(self, mock_frappe):
		"""generate_monthly_receipts should NOT call get_doc('Patient Encounter', ...) per encounter."""
		from lifegence_industry.medical_receipt.api.receipt_generation import generate_monthly_receipts

		# Setup batch doc
		mock_batch = MagicMock()
		mock_batch.name = "BATCH-001"
		mock_frappe.get_doc.return_value = mock_batch

		# Settings
		mock_settings = MagicMock()
		mock_settings.auto_validate_on_generate = False
		mock_frappe.get_single.return_value = mock_settings

		# Encounters
		enc1 = MagicMock()
		enc1.name = "ENC-001"
		enc1.patient_insurance = "INS-001"
		enc1.encounter_date = "2026-02-15"

		enc2 = MagicMock()
		enc2.name = "ENC-002"
		enc2.patient_insurance = "INS-001"
		enc2.encounter_date = "2026-02-20"

		# Insurance
		ins1 = MagicMock()
		ins1.name = "INS-001"
		ins1.insurance_type = "社保"

		# Service lines
		svc_line = MagicMock()
		svc_line.parent = "ENC-001"
		svc_line.medical_service = "SVC001"
		svc_line.service_name = "初診料"
		svc_line.service_code = "SVC001"
		svc_line.fee_points = 288
		svc_line.quantity = 1
		svc_line.line_total_points = 288

		# Diagnoses
		diag = MagicMock()
		diag.parent = "ENC-001"
		diag.disease = "DIS001"
		diag.disease_name = "高血圧症"
		diag.icd10_code = "I10"
		diag.diagnosis_type = "主病名"
		diag.onset_date = None
		diag.outcome = None

		# get_all returns in sequence
		mock_frappe.get_all.side_effect = [
			[enc1, enc2],          # Patient Encounter
			[ins1],                # Patient Insurance Info
			[svc_line],            # Encounter Service Line
			[diag],                # Encounter Diagnosis
		]

		# Mock receipt doc creation
		mock_receipt = MagicMock()
		mock_receipt.total_points = 288
		mock_receipt.total_amount = 2880

		def side_effect_get_doc(arg):
			if isinstance(arg, dict):
				doctype = arg.get("doctype")
				if doctype == "Receipt Batch":
					return mock_batch
				elif doctype == "Receipt":
					return mock_receipt
			return MagicMock()

		mock_frappe.get_doc.side_effect = side_effect_get_doc

		generate_monthly_receipts(2026, 2)

		# Verify: get_doc was NEVER called with ("Patient Encounter", name)
		for c in mock_frappe.get_doc.call_args_list:
			args = c[0]
			if len(args) >= 2:
				self.assertNotEqual(args[0], "Patient Encounter",
					"get_doc should not be called per-encounter (N+1 pattern)")

		# Verify: get_all was called for child tables (batch fetch)
		get_all_calls = [c[0][0] for c in mock_frappe.get_all.call_args_list]
		self.assertIn("Encounter Service Line", get_all_calls,
			"Should batch-fetch Encounter Service Line via get_all")
		self.assertIn("Encounter Diagnosis", get_all_calls,
			"Should batch-fetch Encounter Diagnosis via get_all")


class TestReceiptValidationBatchQueries(unittest.TestCase):
	"""Verify receipt_validation batch-fetches Medical Service Master."""

	@patch("lifegence_industry.medical_receipt.api.receipt_validation.now_datetime")
	@patch("lifegence_industry.medical_receipt.api.receipt_validation.frappe")
	def test_no_get_doc_per_service(self, mock_frappe, mock_now):
		"""validate_receipt should batch-fetch Medical Service Master, not per-line."""
		from lifegence_industry.medical_receipt.api.receipt_validation import validate_receipt

		mock_now.return_value = datetime(2026, 3, 1, 12, 0, 0)

		# Mock receipt with multiple detail lines referencing services
		detail1 = MagicMock()
		detail1.medical_service = "SVC001"
		detail1.fee_points = 288
		detail1.quantity = 1

		detail2 = MagicMock()
		detail2.medical_service = "SVC002"
		detail2.fee_points = 150
		detail2.quantity = 1

		detail3 = MagicMock()
		detail3.medical_service = "SVC001"  # duplicate service
		detail3.fee_points = 288
		detail3.quantity = 1

		mock_receipt = MagicMock()
		mock_receipt.name = "REC-001"
		mock_receipt.patient_insurance = "INS-001"
		mock_receipt.claim_year = 2026
		mock_receipt.claim_month = 2
		mock_receipt.details = [detail1, detail2, detail3]
		mock_receipt.receipt_diagnoses = [MagicMock()]
		mock_receipt.total_points = 726  # 288 + 150 + 288

		# Insurance
		mock_insurance = MagicMock()
		mock_insurance.is_active = True
		mock_insurance.valid_to = None

		# Validation log doc
		mock_log_doc = MagicMock()

		def get_doc_side_effect(*args, **kwargs):
			if len(args) >= 1:
				if args[0] == "Receipt":
					return mock_receipt
				if args[0] == "Patient Insurance Info":
					return mock_insurance
				if isinstance(args[0], dict) and args[0].get("doctype") == "Receipt Validation Log":
					return mock_log_doc
			return MagicMock()

		mock_frappe.get_doc.side_effect = get_doc_side_effect
		mock_frappe.session.user = "test@test.com"

		# Service master batch response
		svc1 = MagicMock()
		svc1.name = "SVC001"
		svc1.is_active = True
		svc1.service_name = "初診料"
		svc1.service_code = "SVC001"

		svc2 = MagicMock()
		svc2.name = "SVC002"
		svc2.is_active = False
		svc2.service_name = "血液検査"
		svc2.service_code = "SVC002"

		mock_frappe.get_all.return_value = [svc1, svc2]

		result = validate_receipt("REC-001")

		# get_doc should NOT be called with ("Medical Service Master", name)
		for c in mock_frappe.get_doc.call_args_list:
			args = c[0]
			if len(args) >= 2:
				self.assertNotEqual(args[0], "Medical Service Master",
					"get_doc should not be called per-service (N+1 pattern)")

		# get_all should be called for Medical Service Master
		get_all_calls = [c[0][0] for c in mock_frappe.get_all.call_args_list]
		self.assertIn("Medical Service Master", get_all_calls,
			"Should batch-fetch Medical Service Master via get_all")

		# Inactive service (SVC002) should generate a warning
		self.assertGreater(result["warnings"], 0)

	@patch("lifegence_industry.medical_receipt.api.receipt_validation.now_datetime")
	@patch("lifegence_industry.medical_receipt.api.receipt_validation.frappe")
	def test_no_service_lines_skips_batch_fetch(self, mock_frappe, mock_now):
		"""When no detail lines have medical_service, skip the batch query."""
		from lifegence_industry.medical_receipt.api.receipt_validation import validate_receipt

		mock_now.return_value = datetime(2026, 3, 1, 12, 0, 0)

		detail1 = MagicMock()
		detail1.medical_service = None
		detail1.fee_points = 100
		detail1.quantity = 1

		mock_receipt = MagicMock()
		mock_receipt.name = "REC-002"
		mock_receipt.patient_insurance = "INS-001"
		mock_receipt.claim_year = 2026
		mock_receipt.claim_month = 2
		mock_receipt.details = [detail1]
		mock_receipt.receipt_diagnoses = [MagicMock()]
		mock_receipt.total_points = 100

		mock_insurance = MagicMock()
		mock_insurance.is_active = True
		mock_insurance.valid_to = None

		mock_log_doc = MagicMock()

		def get_doc_side_effect(*args, **kwargs):
			if len(args) >= 1:
				if args[0] == "Receipt":
					return mock_receipt
				if args[0] == "Patient Insurance Info":
					return mock_insurance
				if isinstance(args[0], dict):
					return mock_log_doc
			return MagicMock()

		mock_frappe.get_doc.side_effect = get_doc_side_effect
		mock_frappe.session.user = "test@test.com"

		result = validate_receipt("REC-002")

		# get_all should NOT be called (no services to batch-fetch)
		mock_frappe.get_all.assert_not_called()
