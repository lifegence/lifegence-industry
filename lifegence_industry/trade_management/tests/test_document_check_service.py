"""Tests for document_check.py — trade document consistency checks.

Supplements the integration tests in test_trade_documents.py with
unit tests using mocked dependencies.
"""

import unittest
from unittest.mock import patch, MagicMock


MODULE = "lifegence_industry.trade_management.services.document_check"


class TestCheckDocumentConsistency(unittest.TestCase):
    """Unit tests for check_document_consistency."""

    def _setup_mocks(self, mock_frappe, ci_list=None, pl_list=None, bl_list=None, awb_list=None):
        """Helper to set up common mock return values."""
        mock_settings = MagicMock()
        mock_settings.enable_ai_document_check = False
        mock_frappe.get_single.return_value = mock_settings

        mock_ts = MagicMock()
        mock_frappe.get_doc.return_value = mock_ts

        # Default: get_all returns in order: CI, PL, BL, then AWB check
        side_effects = [
            ci_list or [],
            pl_list or [],
            bl_list or [],
        ]
        if not bl_list:
            side_effects.append(awb_list or [])  # AWB fallback check
        mock_frappe.get_all.side_effect = side_effects

        return mock_ts

    @patch(f"{MODULE}.frappe")
    def test_all_docs_missing(self, mock_frappe):
        """No documents linked should return Missing status for all."""
        self._setup_mocks(mock_frappe)

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        missing = [r for r in results if r["status"] == "Missing"]
        self.assertTrue(len(missing) >= 2)  # At least CI and PL/BL missing

    @patch(f"{MODULE}.frappe")
    def test_package_count_match(self, mock_frappe):
        """PL and BL with same package count should be OK."""
        self._setup_mocks(
            mock_frappe,
            pl_list=[MagicMock(name="PL-001", total_packages=10, total_gross_weight=500)],
            bl_list=[MagicMock(name="BL-001", total_packages=10, gross_weight=500)],
        )

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        pkg_check = [r for r in results if "Package Count" in r["check_item"]]
        self.assertEqual(len(pkg_check), 1)
        self.assertEqual(pkg_check[0]["status"], "OK")

    @patch(f"{MODULE}.frappe")
    def test_package_count_mismatch(self, mock_frappe):
        """PL and BL with different package counts should be Mismatch."""
        self._setup_mocks(
            mock_frappe,
            pl_list=[MagicMock(name="PL-001", total_packages=10, total_gross_weight=500)],
            bl_list=[MagicMock(name="BL-001", total_packages=12, gross_weight=500)],
        )

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        pkg_check = [r for r in results if "Package Count" in r["check_item"]]
        self.assertEqual(pkg_check[0]["status"], "Mismatch")
        self.assertIn("10", pkg_check[0]["details"])
        self.assertIn("12", pkg_check[0]["details"])

    @patch(f"{MODULE}.frappe")
    def test_weight_match_within_tolerance(self, mock_frappe):
        """Weight difference <= 0.5 kg should be OK."""
        self._setup_mocks(
            mock_frappe,
            pl_list=[MagicMock(name="PL-001", total_packages=10, total_gross_weight=500.2)],
            bl_list=[MagicMock(name="BL-001", total_packages=10, gross_weight=500.5)],
        )

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        weight_check = [r for r in results if "Gross Weight" in r["check_item"]]
        self.assertEqual(weight_check[0]["status"], "OK")

    @patch(f"{MODULE}.frappe")
    def test_weight_mismatch(self, mock_frappe):
        """Weight difference > 0.5 kg should be Mismatch."""
        self._setup_mocks(
            mock_frappe,
            pl_list=[MagicMock(name="PL-001", total_packages=10, total_gross_weight=500)],
            bl_list=[MagicMock(name="BL-001", total_packages=10, gross_weight=510)],
        )

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        weight_check = [r for r in results if "Gross Weight" in r["check_item"]]
        self.assertEqual(weight_check[0]["status"], "Mismatch")

    @patch(f"{MODULE}.frappe")
    def test_ci_present_shows_ok(self, mock_frappe):
        """Commercial Invoice present should show Document: OK."""
        self._setup_mocks(
            mock_frappe,
            ci_list=[MagicMock(name="CI-001", total_amount=100000, currency="USD")],
        )

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        ci_check = [r for r in results if "Commercial Invoice" in r["check_item"]]
        self.assertEqual(ci_check[0]["status"], "OK")

    @patch(f"{MODULE}.frappe")
    def test_awb_satisfies_bl_requirement(self, mock_frappe):
        """Air Waybill should satisfy the B/L or AWB document requirement."""
        self._setup_mocks(
            mock_frappe,
            bl_list=[],  # No B/L
            awb_list=[MagicMock()],  # Has AWB
        )

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        bl_check = [r for r in results if "Bill of Lading" in r["check_item"]]
        self.assertEqual(bl_check[0]["status"], "OK")

    @patch(f"{MODULE}.frappe")
    def test_ai_check_not_called_when_disabled(self, mock_frappe):
        """AI document check should not run when setting is disabled."""
        self._setup_mocks(
            mock_frappe,
            ci_list=[MagicMock(name="CI-001", total_amount=100000, currency="USD")],
        )

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        # No AI-related results should appear
        ai_results = [r for r in results if "AI" in r.get("check_item", "")]
        self.assertEqual(len(ai_results), 0)

    @patch(f"{MODULE}._ai_document_check", return_value=[{"check_item": "AI Check", "status": "OK", "details": "Passed"}])
    @patch(f"{MODULE}.frappe")
    def test_ai_check_called_when_enabled(self, mock_frappe, mock_ai_check):
        """AI document check should run when setting is enabled and CI exists."""
        mock_settings = MagicMock()
        mock_settings.enable_ai_document_check = True
        mock_frappe.get_single.return_value = mock_settings
        mock_frappe.get_doc.return_value = MagicMock()

        ci = [MagicMock(name="CI-001", total_amount=100000, currency="USD")]
        mock_frappe.get_all.side_effect = [
            ci,
            [],  # PL
            [],  # BL
            [],  # AWB
        ]

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        mock_ai_check.assert_called_once()
        ai_results = [r for r in results if r["check_item"] == "AI Check"]
        self.assertEqual(len(ai_results), 1)

    @patch(f"{MODULE}.frappe")
    def test_multiple_pl_bl_aggregated(self, mock_frappe):
        """Multiple PL and BL documents should have their totals summed."""
        self._setup_mocks(
            mock_frappe,
            pl_list=[
                MagicMock(name="PL-001", total_packages=10, total_gross_weight=500),
                MagicMock(name="PL-002", total_packages=5, total_gross_weight=250),
            ],
            bl_list=[
                MagicMock(name="BL-001", total_packages=15, gross_weight=750),
            ],
        )

        from lifegence_industry.trade_management.services.document_check import check_document_consistency
        results = check_document_consistency("TS-001")

        pkg_check = [r for r in results if "Package Count" in r["check_item"]]
        self.assertEqual(pkg_check[0]["status"], "OK")
        self.assertIn("15", pkg_check[0]["details"])


class TestAiDocumentCheck(unittest.TestCase):
    """Tests for _ai_document_check stub."""

    def test_stub_returns_empty_list(self):
        """Current stub should return empty list."""
        from lifegence_industry.trade_management.services.document_check import _ai_document_check
        result = _ai_document_check(
            MagicMock(), [], [], [], MagicMock()
        )
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
