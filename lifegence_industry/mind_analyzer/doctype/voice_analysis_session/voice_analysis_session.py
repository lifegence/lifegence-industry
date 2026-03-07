# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

import uuid
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, time_diff_in_seconds


class VoiceAnalysisSession(Document):
    def before_insert(self):
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        if not self.start_time:
            self.start_time = now_datetime()
        if not self.user:
            self.user = frappe.session.user

    def validate(self):
        self.validate_mode()
        self.link_employee()

    def validate_mode(self):
        if self.mode == "Meeting" and not self.meeting_title:
            self.meeting_title = _("Untitled Meeting")

    def link_employee(self):
        """Auto-link employee if not set"""
        if not self.employee and self.user and frappe.db.exists("DocType", "Employee"):
            employee = frappe.db.get_value(
                "Employee",
                {"user_id": self.user},
                "name"
            )
            if employee:
                self.employee = employee

    def on_update(self):
        if self.status == "Completed" and not self.end_time:
            self.db_set("end_time", now_datetime())
            self.calculate_duration()
            self.calculate_summary()

    def calculate_duration(self):
        """Calculate session duration in seconds"""
        if self.start_time and self.end_time:
            duration = time_diff_in_seconds(self.end_time, self.start_time)
            self.db_set("duration_seconds", int(duration))

    def calculate_summary(self):
        """Calculate summary statistics for the session"""
        if self.mode == "Individual":
            self._calculate_individual_summary()
        else:
            self._calculate_meeting_summary()

        # Count triggers
        trigger_count = frappe.db.count(
            "Voice Trigger Event",
            {"session": self.name}
        )
        self.db_set("trigger_count", trigger_count)

    def _calculate_individual_summary(self):
        """Calculate average stress load for individual sessions"""
        results = frappe.get_all(
            "Individual Analysis Result",
            filters={"session": self.name},
            fields=["stress_load"]
        )
        if results:
            avg_stress = sum(r.stress_load for r in results) / len(results)
            self.db_set("avg_stress_load", round(avg_stress, 3))
            self.db_set("analysis_count", len(results))

    def _calculate_meeting_summary(self):
        """Calculate average PS score for meeting sessions"""
        results = frappe.get_all(
            "Meeting Analysis Result",
            filters={"session": self.name},
            fields=["overall_ps"]
        )
        if results:
            avg_ps = sum(r.overall_ps for r in results) / len(results)
            self.db_set("avg_ps_score", round(avg_ps, 3))
            self.db_set("analysis_count", len(results))

    @staticmethod
    def get_active_session(user=None):
        """Get active session for user"""
        user = user or frappe.session.user
        session = frappe.db.get_value(
            "Voice Analysis Session",
            {"user": user, "status": "Active"},
            ["name", "session_id", "mode", "start_time"],
            as_dict=True
        )
        return session

    @staticmethod
    def end_session(session_name):
        """End a session and calculate summary"""
        session = frappe.get_doc("Voice Analysis Session", session_name)
        session.status = "Completed"
        session.end_time = now_datetime()
        session.save()
        return session
