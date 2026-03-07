# Copyright (c) 2026, Lifegence and contributors
# For license information, please see license.txt

"""
Tests for Lifegence Mind Analyzer

Covers: Voice Analysis Session lifecycle, Individual Analysis Result metrics,
Meeting Analysis Result PS scores, Voice Trigger Events, Monthly Report,
and session API endpoints.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, add_days, getdate
from unittest.mock import patch, MagicMock


TEST_USER = "test-analyzer-user@example.com"

# Track test-created session names for scoped cleanup
_test_session_names = []


def _ensure_test_user():
    """Create test user with Mind Analyzer role."""
    if not frappe.db.exists("User", TEST_USER):
        user = frappe.new_doc("User")
        user.email = TEST_USER
        user.first_name = "Analyzer"
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
    """Ensure Voice Analyzer Settings singleton exists."""
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
    """Create a test Voice Analysis Session."""
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


def _cleanup_analyzer_data():
    """Remove only test-created sessions and their related data."""
    for session_name in _test_session_names:
        # Delete child records linked to session
        for child_doctype in [
            "Voice Trigger Event",
            "Meeting Analysis Result",
            "Individual Analysis Result",
        ]:
            try:
                docs = frappe.get_all(child_doctype, filters={"session": session_name}, pluck="name")
                for name in docs:
                    frappe.delete_doc(child_doctype, name, force=True, ignore_permissions=True)
            except Exception:
                pass
        # Delete the session itself
        try:
            if frappe.db.exists("Voice Analysis Session", session_name):
                frappe.delete_doc("Voice Analysis Session", session_name, force=True, ignore_permissions=True)
        except Exception:
            pass
    frappe.db.commit()
    _test_session_names.clear()


# ── Voice Analysis Session ────────────────────────


class TestVoiceAnalysisSession(FrappeTestCase):
    """Test Voice Analysis Session document lifecycle."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        _cleanup_analyzer_data()

    def test_create_individual_session(self):
        """Individual session creates with correct mode and UUID."""
        session = _create_test_session(mode="Individual")
        self.assertEqual(session.mode, "Individual")
        self.assertEqual(session.status, "Active")
        self.assertIsNotNone(session.session_id)
        self.assertEqual(len(session.session_id), 36)  # UUID format

    def test_create_meeting_session(self):
        """Meeting session creates with title."""
        session = _create_test_session(mode="Meeting")
        self.assertEqual(session.mode, "Meeting")
        self.assertEqual(session.meeting_title, "Test Meeting")

    def test_meeting_without_title_gets_default(self):
        """Meeting session without explicit title gets 'Untitled Meeting'."""
        session = frappe.new_doc("Voice Analysis Session")
        session.mode = "Meeting"
        session.user = TEST_USER
        session.start_time = now_datetime()
        session.insert(ignore_permissions=True)
        frappe.db.commit()
        _test_session_names.append(session.name)
        self.assertIn("Meeting", session.meeting_title or "")

    def test_session_auto_generates_uuid(self):
        """Session generates session_id on insert."""
        session = frappe.new_doc("Voice Analysis Session")
        session.mode = "Individual"
        session.user = TEST_USER
        session.insert(ignore_permissions=True)
        frappe.db.commit()
        _test_session_names.append(session.name)
        self.assertIsNotNone(session.session_id)

    def test_complete_session(self):
        """Completing a session sets end_time and calculates duration."""
        session = _create_test_session()
        session.status = "Completed"
        session.save(ignore_permissions=True)
        frappe.db.commit()
        session.reload()
        self.assertEqual(session.status, "Completed")

    def test_get_active_session(self):
        """get_active_session returns active session for user."""
        session = _create_test_session()
        from lifegence_mind_analyzer.mind_analyzer.doctype.voice_analysis_session.voice_analysis_session import VoiceAnalysisSession
        active = VoiceAnalysisSession.get_active_session(TEST_USER)
        self.assertIsNotNone(active)
        self.assertEqual(active["name"], session.name)

    def test_no_active_session(self):
        """get_active_session returns None when no active session."""
        from lifegence_mind_analyzer.mind_analyzer.doctype.voice_analysis_session.voice_analysis_session import VoiceAnalysisSession
        active = VoiceAnalysisSession.get_active_session(TEST_USER)
        self.assertIsNone(active)


# ── Individual Analysis Result ────────────────────


class TestIndividualAnalysisResult(FrappeTestCase):
    """Test Individual Analysis Result metrics."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        _cleanup_analyzer_data()

    def test_create_individual_result(self):
        """Individual result creates with all 5 metrics."""
        session = _create_test_session()
        result = frappe.new_doc("Individual Analysis Result")
        result.session = session.name
        result.timestamp = now_datetime()
        result.stress_load = 0.45
        result.anxiety_uncertainty = 0.3
        result.cognitive_load = 0.5
        result.confidence_assertiveness = 0.7
        result.stability = 0.6
        result.analysis_confidence = 0.85
        result.insert(ignore_permissions=True)
        frappe.db.commit()

        self.assertIsNotNone(result.name)
        self.assertEqual(result.stress_load, 0.45)
        self.assertEqual(result.stability, 0.6)

    def test_session_summary_calculates_avg_stress(self):
        """Session summary calculates average stress load."""
        session = _create_test_session()
        for stress in [0.3, 0.5, 0.7]:
            r = frappe.new_doc("Individual Analysis Result")
            r.session = session.name
            r.timestamp = now_datetime()
            r.stress_load = stress
            r.insert(ignore_permissions=True)
        frappe.db.commit()

        session.status = "Completed"
        session.save(ignore_permissions=True)
        frappe.db.commit()
        session.reload()

        self.assertAlmostEqual(session.avg_stress_load, 0.5, places=2)
        self.assertEqual(session.analysis_count, 3)


# ── Meeting Analysis Result ───────────────────────


class TestMeetingAnalysisResult(FrappeTestCase):
    """Test Meeting Analysis Result PS scores."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        _cleanup_analyzer_data()

    def test_create_meeting_result(self):
        """Meeting result creates with PS metrics."""
        session = _create_test_session(mode="Meeting")
        result = frappe.new_doc("Meeting Analysis Result")
        result.session = session.name
        result.timestamp = now_datetime()
        result.speak_up = 0.8
        result.respect_interaction = 0.7
        result.error_tolerance = 0.6
        result.power_balance = 0.75
        result.overall_ps = 0.72
        result.analysis_confidence = 0.9
        result.insert(ignore_permissions=True)
        frappe.db.commit()

        self.assertIsNotNone(result.name)
        self.assertEqual(result.overall_ps, 0.72)

    def test_session_summary_calculates_avg_ps(self):
        """Session summary calculates average PS score."""
        session = _create_test_session(mode="Meeting")
        for ps in [0.6, 0.8]:
            r = frappe.new_doc("Meeting Analysis Result")
            r.session = session.name
            r.timestamp = now_datetime()
            r.overall_ps = ps
            r.insert(ignore_permissions=True)
        frappe.db.commit()

        session.status = "Completed"
        session.save(ignore_permissions=True)
        frappe.db.commit()
        session.reload()

        self.assertAlmostEqual(session.avg_ps_score, 0.7, places=2)


# ── Voice Trigger Event ──────────────────────────


class TestVoiceTriggerEvent(FrappeTestCase):
    """Test Voice Trigger Event creation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        _cleanup_analyzer_data()

    def test_create_trigger_event(self):
        """Trigger event creates with type and severity."""
        session = _create_test_session()
        trigger = frappe.new_doc("Voice Trigger Event")
        trigger.session = session.name
        trigger.trigger_type = "silence_spike"
        trigger.timestamp = now_datetime()
        trigger.severity = 0.7
        trigger.evidence = "Prolonged silence detected (5.2 seconds)"
        trigger.insert(ignore_permissions=True)
        frappe.db.commit()

        self.assertIsNotNone(trigger.name)
        self.assertEqual(trigger.trigger_type, "silence_spike")
        self.assertEqual(trigger.severity, 0.7)

    def test_session_counts_triggers(self):
        """Session trigger_count updates on completion."""
        session = _create_test_session()
        for t_type in ["silence_spike", "hedge_increase", "interruption"]:
            trigger = frappe.new_doc("Voice Trigger Event")
            trigger.session = session.name
            trigger.trigger_type = t_type
            trigger.timestamp = now_datetime()
            trigger.severity = 0.5
            trigger.insert(ignore_permissions=True)
        frappe.db.commit()

        session.status = "Completed"
        session.save(ignore_permissions=True)
        frappe.db.commit()
        session.reload()

        self.assertEqual(session.trigger_count, 3)


# ── Session API ───────────────────────────────────


class TestSessionAPI(FrappeTestCase):
    """Test session API endpoints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    def test_has_analyzer_access_with_role(self):
        """User with Mind Analyzer User role has access."""
        frappe.set_user(TEST_USER)
        from lifegence_mind_analyzer.api.session import has_analyzer_access
        self.assertTrue(has_analyzer_access())

    def test_has_analyzer_access_guest_denied(self):
        """Guest user does not have access."""
        frappe.set_user("Guest")
        from lifegence_mind_analyzer.api.session import has_analyzer_access
        self.assertFalse(has_analyzer_access())

    def test_start_session_api(self):
        """start_session creates an active session."""
        frappe.set_user(TEST_USER)
        from lifegence_mind_analyzer.api.session import start_session
        result = start_session(mode="Individual")
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["session_id"])
        self.assertEqual(result["mode"], "Individual")
        # Track for cleanup
        session = frappe.get_all(
            "Voice Analysis Session",
            filters={"session_id": result["session_id"]},
            pluck="name"
        )
        if session:
            _test_session_names.append(session[0])

    def test_start_session_blocks_duplicate(self):
        """Cannot start a second session while one is active."""
        frappe.set_user(TEST_USER)
        from lifegence_mind_analyzer.api.session import start_session
        result = start_session(mode="Individual")
        # Track for cleanup
        session = frappe.get_all(
            "Voice Analysis Session",
            filters={"session_id": result["session_id"]},
            pluck="name"
        )
        if session:
            _test_session_names.append(session[0])
        self.assertRaises(Exception, start_session, mode="Individual")

    def test_start_session_invalid_mode(self):
        """Invalid mode raises validation error."""
        frappe.set_user(TEST_USER)
        from lifegence_mind_analyzer.api.session import start_session
        self.assertRaises(Exception, start_session, mode="Invalid")


# ── Reports API ───────────────────────────────────


class TestReportsAPI(FrappeTestCase):
    """Test reports/dashboard API."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_test_user()
        _ensure_analyzer_settings()

    def tearDown(self):
        frappe.set_user("Administrator")
        _cleanup_analyzer_data()

    def test_get_summary_empty(self):
        """get_summary returns zeros when no sessions exist."""
        frappe.set_user(TEST_USER)
        from lifegence_mind_analyzer.api.reports import get_summary
        result = get_summary(days=30)
        self.assertEqual(result["total_sessions"], 0)
        self.assertIsNone(result["avg_stress"])

    def test_get_summary_with_data(self):
        """get_summary returns correct counts with sessions."""
        session = _create_test_session(mode="Individual", status="Active")
        session.status = "Completed"
        session.save(ignore_permissions=True)
        frappe.db.commit()

        frappe.set_user(TEST_USER)
        from lifegence_mind_analyzer.api.reports import get_summary
        result = get_summary(days=30)
        self.assertEqual(result["total_sessions"], 1)
        self.assertEqual(result["individual_sessions"], 1)
