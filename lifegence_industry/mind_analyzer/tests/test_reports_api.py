# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

"""
Tests for Report APIs and remaining Session APIs.

Covers: end_session, get_active_session, get_session_history, get_session_detail,
cancel_session, get_recent_triggers, get_department_summary,
get_department_timeseries, get_department_comparison, get_team_analysis,
get_organization_team_analysis, get_trigger_analysis, export_session_data,
get_my_monthly_reports, get_available_report_months, get_latest_monthly_report,
compare_monthly_reports, _calc_percent_change, get_session_results,
get_trend_data, get_latest_result.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime


TEST_USER = "test-reports-api-user@example.com"

# Track test-created session names for scoped cleanup
_test_session_names: list[str] = []


def _ensure_test_user():
    """Create test user with Mind Analyzer User role."""
    if not frappe.db.exists("User", TEST_USER):
        user = frappe.new_doc("User")
        user.email = TEST_USER
        user.first_name = "Reports"
        user.last_name = "Tester"
        user.send_welcome_email = 0
        user.insert(ignore_permissions=True)
    # Ensure role
    user_doc = frappe.get_doc("User", TEST_USER)
    if not any(r.role == "Mind Analyzer User" for r in user_doc.roles):
        user_doc.append("roles", {"role": "Mind Analyzer User"})
        user_doc.save(ignore_permissions=True)
    frappe.db.commit()


def _ensure_analyzer_settings():
    """Ensure Voice Analyzer Settings singleton exists with defaults."""
    try:
        settings = frappe.get_single("Voice Analyzer Settings")
        if not settings.analysis_interval_sec:
            settings.db_set("analysis_interval_sec", 10, update_modified=False)
            settings.db_set("trigger_threshold", 0.3, update_modified=False)
            settings.db_set("data_retention_days", 90, update_modified=False)
            frappe.db.commit()
    except Exception:
        pass


def _create_test_session(mode="Individual", user=None, status="Active"):
    """Create a test Voice Analysis Session and track it for cleanup."""
    session = frappe.new_doc("Voice Analysis Session")
    session.mode = mode
    session.user = user or TEST_USER
    session.status = status
    session.start_time = now_datetime()
    if mode == "Meeting":
        session.meeting_title = "Test Meeting"
    session.insert(ignore_permissions=True)
    frappe.db.commit()
    _test_session_names.append(session.name)
    return session


def _complete_session(session):
    """Mark a session as Completed and persist."""
    session.status = "Completed"
    session.end_time = now_datetime()
    session.save(ignore_permissions=True)
    frappe.db.commit()
    session.reload()
    return session


def _cleanup_analyzer_data():
    """Remove only test-created sessions and their related data."""
    for session_name in _test_session_names:
        for child_doctype in [
            "Voice Trigger Event",
            "Meeting Analysis Result",
            "Individual Analysis Result",
            "Acoustic Statistics",
        ]:
            try:
                docs = frappe.get_all(
                    child_doctype,
                    filters={"session": session_name},
                    pluck="name",
                )
                for name in docs:
                    frappe.delete_doc(
                        child_doctype, name, force=True, ignore_permissions=True
                    )
            except Exception:
                pass
        try:
            if frappe.db.exists("Voice Analysis Session", session_name):
                frappe.delete_doc(
                    "Voice Analysis Session",
                    session_name,
                    force=True,
                    ignore_permissions=True,
                )
        except Exception:
            pass
    frappe.db.commit()
    _test_session_names.clear()


# ---------------------------------------------------------------------------
# Session API gaps
# ---------------------------------------------------------------------------


class TestSessionEndAPI(FrappeTestCase):
    """Tests for end_session, get_active_session, get_session_history,
    get_session_detail, and cancel_session."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    # -- end_session --------------------------------------------------------

    def test_end_session_by_name(self):
        """end_session sets status to Completed and returns success."""
        session = _create_test_session()
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import end_session

        result = end_session(name=session.name)

        self.assertTrue(result["success"])
        session.reload()
        self.assertEqual(session.status, "Completed")

    def test_end_session_by_session_id(self):
        """end_session accepts session_id UUID and completes the session."""
        session = _create_test_session()
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import end_session

        result = end_session(session_id=session.session_id)

        self.assertTrue(result["success"])
        self.assertEqual(result["session_id"], session.session_id)
        session.reload()
        self.assertEqual(session.status, "Completed")

    def test_end_session_no_active_raises(self):
        """end_session throws when no active session exists."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import end_session

        self.assertRaises(Exception, end_session)

    # -- get_active_session -------------------------------------------------

    def test_get_active_session_returns_false_when_none(self):
        """get_active_session returns active=False when no session exists."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import get_active_session

        result = get_active_session()

        self.assertFalse(result["active"])

    def test_get_active_session_returns_true_when_active(self):
        """get_active_session returns active=True with session details."""
        session = _create_test_session()
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import get_active_session

        result = get_active_session()

        self.assertTrue(result["active"])
        self.assertEqual(result["name"], session.name)
        self.assertEqual(result["session_id"], session.session_id)

    # -- get_session_history ------------------------------------------------

    def test_get_session_history_returns_completed_sessions(self):
        """get_session_history returns list of completed sessions."""
        s1 = _create_test_session()
        _complete_session(s1)
        s2 = _create_test_session()
        _complete_session(s2)

        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import get_session_history

        result = get_session_history()

        self.assertIn("sessions", result)
        self.assertIn("total", result)
        self.assertGreaterEqual(result["total"], 2)
        self.assertGreaterEqual(len(result["sessions"]), 2)

    def test_get_session_history_empty(self):
        """get_session_history returns empty list when no completed sessions."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import get_session_history

        result = get_session_history()

        self.assertEqual(result["total"], 0)
        self.assertEqual(len(result["sessions"]), 0)

    # -- get_session_detail -------------------------------------------------

    def test_get_session_detail_individual(self):
        """get_session_detail returns structured detail for Individual session."""
        session = _create_test_session(mode="Individual")
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import get_session_detail

        result = get_session_detail(session_name=session.name)

        self.assertEqual(result["name"], session.name)
        self.assertEqual(result["mode"], "Individual")
        self.assertIn("triggers", result)
        self.assertIn("results", result)

    def test_get_session_detail_meeting(self):
        """get_session_detail returns structured detail for Meeting session."""
        session = _create_test_session(mode="Meeting")
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import get_session_detail

        result = get_session_detail(session_name=session.name)

        self.assertEqual(result["mode"], "Meeting")
        self.assertEqual(result["meeting_title"], "Test Meeting")
        self.assertIn("results", result)

    # -- cancel_session -----------------------------------------------------

    def test_cancel_session_sets_cancelled(self):
        """cancel_session sets status to Cancelled."""
        session = _create_test_session()
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import cancel_session

        result = cancel_session(name=session.name)

        self.assertTrue(result["success"])
        session.reload()
        self.assertEqual(session.status, "Cancelled")

    def test_cancel_session_no_active_raises(self):
        """cancel_session throws when no active session is found."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.session import cancel_session

        self.assertRaises(Exception, cancel_session)


# ---------------------------------------------------------------------------
# Reports Summary
# ---------------------------------------------------------------------------


class TestReportsSummaryAPI(FrappeTestCase):
    """Tests for get_recent_triggers from reports_summary module."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    def test_get_recent_triggers_empty(self):
        """get_recent_triggers returns empty list when no triggers exist."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.reports_summary import get_recent_triggers

        result = get_recent_triggers()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_recent_triggers_with_data(self):
        """get_recent_triggers returns triggers when they exist."""
        session = _create_test_session()
        trigger = frappe.new_doc("Voice Trigger Event")
        trigger.session = session.name
        trigger.trigger_type = "silence_spike"
        trigger.timestamp = now_datetime()
        trigger.severity = 0.6
        trigger.evidence = "Prolonged silence detected"
        trigger.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.reports_summary import get_recent_triggers

        result = get_recent_triggers()

        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        self.assertEqual(result[0]["trigger_type"], "silence_spike")


# ---------------------------------------------------------------------------
# Reports Department
# ---------------------------------------------------------------------------


class TestReportsDepartmentAPI(FrappeTestCase):
    """Tests for department-level report APIs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    def test_get_department_summary_nonexistent_dept(self):
        """get_department_summary returns employee_count=0 for missing department."""
        if not frappe.db.exists("DocType", "Employee"):
            self.skipTest("Employee DocType not available (HRMS not installed)")

        frappe.set_user("Administrator")

        from lifegence_industry.mind_analyzer.api.reports_department import (
            get_department_summary,
        )

        result = get_department_summary(
            department="Nonexistent Department XYZ", period="month"
        )

        self.assertEqual(result["employee_count"], 0)
        self.assertEqual(result["department"], "Nonexistent Department XYZ")

    def test_get_department_timeseries_structure(self):
        """get_department_timeseries returns correct structure."""
        if not frappe.db.exists("DocType", "Department"):
            self.skipTest("Department DocType not available (HRMS not installed)")

        frappe.set_user("Administrator")

        from lifegence_industry.mind_analyzer.api.reports_department import (
            get_department_timeseries,
        )

        result = get_department_timeseries(period="month")

        self.assertIn("departments", result)
        self.assertIn("dates", result)
        self.assertIn("series", result)
        self.assertIsInstance(result["departments"], list)
        self.assertIsInstance(result["dates"], list)
        self.assertIsInstance(result["series"], dict)

    def test_get_department_comparison_structure(self):
        """get_department_comparison returns departments list and period_days."""
        if not frappe.db.exists("DocType", "Department"):
            self.skipTest("Department DocType not available (HRMS not installed)")

        frappe.set_user("Administrator")

        from lifegence_industry.mind_analyzer.api.reports_department import (
            get_department_comparison,
        )

        result = get_department_comparison()

        self.assertIn("departments", result)
        self.assertIn("period_days", result)
        self.assertEqual(result["period_days"], 30)
        self.assertIsInstance(result["departments"], list)


# ---------------------------------------------------------------------------
# Reports Team
# ---------------------------------------------------------------------------


class TestReportsTeamAPI(FrappeTestCase):
    """Tests for team-level report APIs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    def test_get_team_analysis_no_employee_raises(self):
        """get_team_analysis throws 'Employee record not found' for Administrator
        when no Employee record is linked to the Administrator user."""
        if not frappe.db.exists("DocType", "Employee"):
            self.skipTest("Employee DocType not available (HRMS not installed)")

        frappe.set_user("Administrator")

        from lifegence_industry.mind_analyzer.api.reports_team import get_team_analysis

        # Administrator typically has no Employee record in test environments.
        # If one exists, this test verifies the flow still works without error.
        admin_employee = frappe.db.get_value(
            "Employee", {"user_id": "Administrator"}, "name"
        )
        if admin_employee:
            # Employee exists -- the call should succeed, not raise
            result = get_team_analysis()
            self.assertIn("team_size", result)
        else:
            self.assertRaises(Exception, get_team_analysis)

    def test_get_organization_team_analysis_structure(self):
        """get_organization_team_analysis returns expected structure."""
        if not frappe.db.exists("DocType", "Employee"):
            self.skipTest("Employee DocType not available (HRMS not installed)")

        frappe.set_user("Administrator")

        from lifegence_industry.mind_analyzer.api.reports_team import (
            get_organization_team_analysis,
        )

        result = get_organization_team_analysis(period="month")

        self.assertIn("team_size", result)
        self.assertIn("members", result)
        self.assertIn("active_members", result)
        self.assertIn("period", result)
        self.assertEqual(result["period"], "month")
        self.assertIsInstance(result["members"], list)


# ---------------------------------------------------------------------------
# Reports Triggers
# ---------------------------------------------------------------------------


class TestReportsTriggersAPI(FrappeTestCase):
    """Tests for trigger analysis report API."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    def test_get_trigger_analysis_structure(self):
        """get_trigger_analysis returns dict with expected keys."""
        frappe.set_user("Administrator")

        from lifegence_industry.mind_analyzer.api.reports_triggers import get_trigger_analysis

        result = get_trigger_analysis(period="month")

        self.assertIsInstance(result, dict)
        self.assertIn("total_triggers", result)
        self.assertIn("by_type", result)
        self.assertIn("period", result)
        self.assertEqual(result["period"], "month")
        self.assertIsInstance(result["total_triggers"], int)
        self.assertIsInstance(result["by_type"], dict)


# ---------------------------------------------------------------------------
# Reports Export
# ---------------------------------------------------------------------------


class TestReportsExportAPI(FrappeTestCase):
    """Tests for session data export API."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    def test_export_session_data_json(self):
        """export_session_data returns json format with session data."""
        session = _create_test_session()
        _complete_session(session)

        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.reports_export import export_session_data

        result = export_session_data(
            session_id=session.session_id, format="json"
        )

        self.assertEqual(result["format"], "json")
        self.assertIn("data", result)

    def test_export_session_data_csv(self):
        """export_session_data returns csv format."""
        session = _create_test_session()
        _complete_session(session)

        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.reports_export import export_session_data

        result = export_session_data(
            session_id=session.session_id, format="csv"
        )

        self.assertEqual(result["format"], "csv")
        self.assertIn("data", result)


# ---------------------------------------------------------------------------
# Reports Monthly
# ---------------------------------------------------------------------------


class TestReportsMonthlyAPI(FrappeTestCase):
    """Tests for monthly report APIs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    def test_get_my_monthly_reports_empty(self):
        """get_my_monthly_reports returns empty list when no reports exist."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.reports_monthly import (
            get_my_monthly_reports,
        )

        result = get_my_monthly_reports()

        self.assertTrue(result["success"])
        self.assertIsInstance(result["reports"], list)
        self.assertEqual(len(result["reports"]), 0)

    def test_get_available_report_months_empty(self):
        """get_available_report_months returns empty months when no sessions."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.reports_monthly import (
            get_available_report_months,
        )

        result = get_available_report_months()

        self.assertTrue(result["success"])
        self.assertIsInstance(result["months"], list)
        self.assertEqual(len(result["months"]), 0)

    def test_get_latest_monthly_report_none(self):
        """get_latest_monthly_report returns success=False when no reports."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.reports_monthly import (
            get_latest_monthly_report,
        )

        result = get_latest_monthly_report()

        self.assertFalse(result["success"])

    def test_compare_monthly_reports_too_few_raises(self):
        """compare_monthly_reports throws when fewer than 2 reports given."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.reports_monthly import (
            compare_monthly_reports,
        )

        self.assertRaises(
            Exception, compare_monthly_reports, report_names=json.dumps(["one"])
        )

    def test_calc_percent_change_normal(self):
        """_calc_percent_change(100, 120) returns 20.0."""
        from lifegence_industry.mind_analyzer.api.reports_monthly import (
            _calc_percent_change,
        )

        self.assertEqual(_calc_percent_change(100, 120), 20.0)

    def test_calc_percent_change_zero_old(self):
        """_calc_percent_change(0, 100) returns None (avoid division by zero)."""
        from lifegence_industry.mind_analyzer.api.reports_monthly import (
            _calc_percent_change,
        )

        self.assertIsNone(_calc_percent_change(0, 100))

    def test_calc_percent_change_none_old(self):
        """_calc_percent_change(None, 100) returns None."""
        from lifegence_industry.mind_analyzer.api.reports_monthly import (
            _calc_percent_change,
        )

        self.assertIsNone(_calc_percent_change(None, 100))

    def test_calc_percent_change_none_new(self):
        """_calc_percent_change(100, None) returns None."""
        from lifegence_industry.mind_analyzer.api.reports_monthly import (
            _calc_percent_change,
        )

        self.assertIsNone(_calc_percent_change(100, None))

    def test_calc_percent_change_decrease(self):
        """_calc_percent_change(200, 150) returns -25.0."""
        from lifegence_industry.mind_analyzer.api.reports_monthly import (
            _calc_percent_change,
        )

        self.assertEqual(_calc_percent_change(200, 150), -25.0)


# ---------------------------------------------------------------------------
# Analysis API
# ---------------------------------------------------------------------------


class TestAnalysisAPI(FrappeTestCase):
    """Tests for analysis API endpoints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    def test_get_session_results_structure(self):
        """get_session_results returns session, results, triggers, statistics."""
        session = _create_test_session()
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.analysis import get_session_results

        result = get_session_results(name=session.name)

        self.assertIn("session", result)
        self.assertIn("results", result)
        self.assertIn("triggers", result)
        self.assertIn("statistics", result)
        self.assertEqual(result["session"]["name"], session.name)

    def test_get_session_results_by_session_id(self):
        """get_session_results works with session_id parameter."""
        session = _create_test_session()
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.analysis import get_session_results

        result = get_session_results(session_id=session.session_id)

        self.assertEqual(result["session"]["name"], session.name)

    def test_get_session_results_not_found_raises(self):
        """get_session_results throws when session does not exist."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.analysis import get_session_results

        self.assertRaises(
            Exception, get_session_results, session_id="nonexistent-uuid-1234"
        )

    def test_get_trend_data_empty(self):
        """get_trend_data returns total_sessions=0 when no sessions exist."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.analysis import get_trend_data

        result = get_trend_data(days=30)

        self.assertEqual(result["total_sessions"], 0)
        self.assertIsInstance(result["trend"], list)
        self.assertEqual(len(result["trend"]), 0)

    def test_get_trend_data_with_sessions(self):
        """get_trend_data returns trend entries for completed sessions."""
        session = _create_test_session()
        _complete_session(session)

        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.analysis import get_trend_data

        result = get_trend_data(days=30)

        self.assertGreaterEqual(result["total_sessions"], 1)

    def test_get_latest_result_no_analysis(self):
        """get_latest_result returns None result when no analysis performed."""
        session = _create_test_session()
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.analysis import get_latest_result

        result = get_latest_result(session_id=session.session_id)

        self.assertIsNone(result["result"])
        self.assertIsNone(result["statistics"])
        self.assertIsInstance(result["recent_triggers"], list)

    def test_get_latest_result_not_found_raises(self):
        """get_latest_result throws when session UUID does not exist."""
        frappe.set_user(TEST_USER)

        from lifegence_industry.mind_analyzer.api.analysis import get_latest_result

        self.assertRaises(
            Exception, get_latest_result, session_id="nonexistent-uuid-5678"
        )


# ---------------------------------------------------------------------------
# Reports shim re-export integrity
# ---------------------------------------------------------------------------


class TestReportsShimIntegrity(FrappeTestCase):
    """Verify that reports.py re-export shim exposes all functions."""

    def test_summary_exports(self):
        """Summary functions are importable from the reports shim."""
        from lifegence_industry.mind_analyzer.api.reports import (
            get_summary,
            get_recent_triggers,
        )

        self.assertTrue(callable(get_summary))
        self.assertTrue(callable(get_recent_triggers))

    def test_department_exports(self):
        """Department functions are importable from the reports shim."""
        from lifegence_industry.mind_analyzer.api.reports import (
            get_department_summary,
            get_department_timeseries,
            get_department_comparison,
        )

        self.assertTrue(callable(get_department_summary))
        self.assertTrue(callable(get_department_timeseries))
        self.assertTrue(callable(get_department_comparison))

    def test_team_exports(self):
        """Team functions are importable from the reports shim."""
        from lifegence_industry.mind_analyzer.api.reports import (
            get_team_analysis,
            get_organization_team_analysis,
        )

        self.assertTrue(callable(get_team_analysis))
        self.assertTrue(callable(get_organization_team_analysis))

    def test_triggers_export(self):
        """Trigger analysis function is importable from the reports shim."""
        from lifegence_industry.mind_analyzer.api.reports import get_trigger_analysis

        self.assertTrue(callable(get_trigger_analysis))

    def test_export_exports(self):
        """Export function is importable from the reports shim."""
        from lifegence_industry.mind_analyzer.api.reports import export_session_data

        self.assertTrue(callable(export_session_data))

    def test_monthly_exports(self):
        """Monthly report functions are importable from the reports shim."""
        from lifegence_industry.mind_analyzer.api.reports import (
            get_my_monthly_reports,
            get_monthly_report_detail,
            get_latest_monthly_report,
            generate_monthly_report,
            get_available_report_months,
            compare_monthly_reports,
            _calc_percent_change,
        )

        for func in (
            get_my_monthly_reports,
            get_monthly_report_detail,
            get_latest_monthly_report,
            generate_monthly_report,
            get_available_report_months,
            compare_monthly_reports,
            _calc_percent_change,
        ):
            self.assertTrue(callable(func), f"{func.__name__} is not callable")
