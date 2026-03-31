"""Tests for sanctions_screening.py — security-critical sanctions checks."""

import unittest
from unittest.mock import patch, MagicMock
import frappe


MODULE = "lifegence_industry.trade_management.services.sanctions_screening"


def _d(d):
    """Wrap a dict as frappe._dict so it supports both dot and dict access."""
    return frappe._dict(d)


class TestSearchSanctionsList(unittest.TestCase):
    """Tests for _search_sanctions_list internal function."""

    @patch(f"{MODULE}.frappe")
    def test_exact_match_returns_hit(self, mock_frappe):
        """Exact match should return match_type=Exact with score 100."""
        mock_frappe.get_all.side_effect = [
            # Exact match found
            [_d({"entity_name": "Bad Corp", "entity_type": "Organization",
                 "list_source": "OFAC SDN", "program": "SDGT"})],
        ]

        from lifegence_industry.trade_management.services.sanctions_screening import _search_sanctions_list
        results = _search_sanctions_list("Bad Corp")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["match_type"], "Exact")
        self.assertEqual(results[0]["score"], 100)

    @patch(f"{MODULE}.frappe")
    def test_no_match_returns_empty(self, mock_frappe):
        """Clean entity should return empty list."""
        mock_frappe.get_all.side_effect = [
            [],  # No exact match
            [],  # No partial match
            [],  # No alias match
        ]

        from lifegence_industry.trade_management.services.sanctions_screening import _search_sanctions_list
        results = _search_sanctions_list("Clean Corp")

        self.assertEqual(results, [])

    @patch(f"{MODULE}.frappe")
    def test_partial_match_returns_partial(self, mock_frappe):
        """Partial LIKE match should return match_type=Partial with score 70."""
        mock_frappe.get_all.side_effect = [
            [],  # No exact match
            [_d({"entity_name": "Bad Corp International", "entity_type": "Organization",
                 "list_source": "UN SC", "program": "DPRK"})],  # Partial match
            [],  # No alias match
        ]

        from lifegence_industry.trade_management.services.sanctions_screening import _search_sanctions_list
        results = _search_sanctions_list("Bad Corp")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["match_type"], "Partial")
        self.assertEqual(results[0]["score"], 70)

    @patch(f"{MODULE}.frappe")
    def test_alias_match(self, mock_frappe):
        """Match via aliases field should also return results."""
        mock_frappe.get_all.side_effect = [
            [],  # No exact match
            [],  # No partial match on entity_name
            [_d({"entity_name": "Secret Entity", "entity_type": "Individual",
                 "list_source": "EU", "program": "Terrorism"})],  # Alias match
        ]

        from lifegence_industry.trade_management.services.sanctions_screening import _search_sanctions_list
        results = _search_sanctions_list("alias name")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["entity_name"], "Secret Entity")

    @patch(f"{MODULE}.frappe")
    def test_deduplication(self, mock_frappe):
        """Same entity in both partial and alias results should appear once."""
        entry_data = {"entity_name": "Duplicate Corp", "entity_type": "Organization",
                      "list_source": "OFAC SDN", "program": "SDGT"}
        mock_frappe.get_all.side_effect = [
            [],  # No exact
            [_d(entry_data)],  # Partial
            [_d(entry_data)],  # Alias (same entity)
        ]

        from lifegence_industry.trade_management.services.sanctions_screening import _search_sanctions_list
        results = _search_sanctions_list("Duplicate")

        self.assertEqual(len(results), 1)


class TestScreenEntity(unittest.TestCase):
    """Tests for screen_entity whitelisted function."""

    @patch(f"{MODULE}._search_sanctions_list")
    @patch(f"{MODULE}.frappe")
    def test_clear_result(self, mock_frappe, mock_search):
        """No matches should return result=Clear."""
        mock_search.return_value = []
        mock_doc = MagicMock()
        mock_doc.name = "TCC-001"
        mock_frappe.get_doc.return_value = mock_doc

        from lifegence_industry.trade_management.services.sanctions_screening import screen_entity
        result = screen_entity("Clean Corp")

        self.assertEqual(result["result"], "Clear")
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["check_name"], "TCC-001")

    @patch(f"{MODULE}._search_sanctions_list")
    @patch(f"{MODULE}.frappe")
    def test_hit_result_on_exact_match(self, mock_frappe, mock_search):
        """Exact match should return result=Hit."""
        mock_search.return_value = [
            {"entity_name": "Bad Corp", "list_source": "OFAC", "match_type": "Exact", "score": 100},
        ]
        mock_doc = MagicMock()
        mock_doc.name = "TCC-002"
        mock_frappe.get_doc.return_value = mock_doc

        from lifegence_industry.trade_management.services.sanctions_screening import screen_entity
        result = screen_entity("Bad Corp")

        self.assertEqual(result["result"], "Hit")
        self.assertEqual(len(result["matches"]), 1)

    @patch(f"{MODULE}._search_sanctions_list")
    @patch(f"{MODULE}.frappe")
    def test_possible_match_on_partial(self, mock_frappe, mock_search):
        """Partial match (no Exact) should return result=Possible Match."""
        mock_search.return_value = [
            {"entity_name": "Bad Corp Int'l", "list_source": "UN", "match_type": "Partial", "score": 70},
        ]
        mock_doc = MagicMock()
        mock_doc.name = "TCC-003"
        mock_frappe.get_doc.return_value = mock_doc

        from lifegence_industry.trade_management.services.sanctions_screening import screen_entity
        result = screen_entity("Bad Corp")

        self.assertEqual(result["result"], "Possible Match")

    @patch(f"{MODULE}._search_sanctions_list")
    @patch(f"{MODULE}.frappe")
    def test_creates_compliance_check_record(self, mock_frappe, mock_search):
        """Should create a Trade Compliance Check document."""
        mock_search.return_value = []
        mock_doc = MagicMock()
        mock_doc.name = "TCC-004"
        mock_frappe.get_doc.return_value = mock_doc

        from lifegence_industry.trade_management.services.sanctions_screening import screen_entity
        screen_entity("Test Corp", trade_shipment="TS-001")

        mock_frappe.get_doc.assert_called_once()
        call_args = mock_frappe.get_doc.call_args[0][0]
        self.assertEqual(call_args["doctype"], "Trade Compliance Check")
        self.assertEqual(call_args["check_type"], "Sanctions Screening")
        self.assertEqual(call_args["trade_shipment"], "TS-001")
        self.assertEqual(call_args["checked_entity"], "Test Corp")
        mock_doc.insert.assert_called_once_with(ignore_permissions=True)

    @patch(f"{MODULE}._search_sanctions_list")
    @patch(f"{MODULE}.frappe")
    def test_matched_entries_in_check_record(self, mock_frappe, mock_search):
        """Matched entries should be included in the compliance check record."""
        mock_search.return_value = [
            {"entity_name": "Bad Corp", "list_source": "OFAC", "match_type": "Exact", "score": 100},
            {"entity_name": "Bad Corp Ltd", "list_source": "EU", "match_type": "Partial", "score": 70},
        ]
        mock_doc = MagicMock()
        mock_doc.name = "TCC-005"
        mock_frappe.get_doc.return_value = mock_doc

        from lifegence_industry.trade_management.services.sanctions_screening import screen_entity
        screen_entity("Bad Corp")

        call_args = mock_frappe.get_doc.call_args[0][0]
        self.assertEqual(len(call_args["matched_entries"]), 2)
        self.assertEqual(call_args["matched_entries"][0]["list_name"], "OFAC")
        self.assertEqual(call_args["matched_entries"][1]["match_type"], "Partial")


class TestScreenShipment(unittest.TestCase):
    """Tests for screen_shipment function."""

    @patch(f"{MODULE}.screen_entity")
    @patch(f"{MODULE}.frappe")
    def test_screens_shipper_and_consignee(self, mock_frappe, mock_screen_entity):
        """Should screen both shipper and consignee."""
        mock_ts = MagicMock()
        mock_ts.shipper = "COMP-001"
        mock_ts.shipper_type = "Company"
        mock_ts.consignee = "COMP-002"
        mock_ts.consignee_type = "Company"
        mock_frappe.get_doc.return_value = mock_ts
        mock_frappe.db.get_value.side_effect = ["Shipper Corp", "Consignee Corp"]
        mock_screen_entity.side_effect = [
            {"result": "Clear", "matches": [], "check_name": "TCC-001"},
            {"result": "Clear", "matches": [], "check_name": "TCC-002"},
        ]

        from lifegence_industry.trade_management.services.sanctions_screening import screen_shipment
        results = screen_shipment("TS-001")

        self.assertEqual(len(results), 2)
        self.assertEqual(mock_screen_entity.call_count, 2)

    @patch(f"{MODULE}.screen_entity")
    @patch(f"{MODULE}.frappe")
    def test_no_shipper_skipped(self, mock_frappe, mock_screen_entity):
        """When shipper is empty, only consignee is screened."""
        mock_ts = MagicMock()
        mock_ts.shipper = None
        mock_ts.consignee = "COMP-002"
        mock_ts.consignee_type = "Company"
        mock_frappe.get_doc.return_value = mock_ts
        mock_frappe.db.get_value.return_value = "Consignee Corp"
        mock_screen_entity.return_value = {"result": "Clear", "matches": [], "check_name": "TCC-001"}

        from lifegence_industry.trade_management.services.sanctions_screening import screen_shipment
        results = screen_shipment("TS-001")

        self.assertEqual(len(results), 1)
        self.assertEqual(mock_screen_entity.call_count, 1)

    @patch(f"{MODULE}.screen_entity")
    @patch(f"{MODULE}.frappe")
    def test_no_parties_returns_empty(self, mock_frappe, mock_screen_entity):
        """When no shipper and no consignee, return empty."""
        mock_ts = MagicMock()
        mock_ts.shipper = None
        mock_ts.consignee = None
        mock_frappe.get_doc.return_value = mock_ts

        from lifegence_industry.trade_management.services.sanctions_screening import screen_shipment
        results = screen_shipment("TS-001")

        self.assertEqual(results, [])
        mock_screen_entity.assert_not_called()


if __name__ == "__main__":
    unittest.main()
