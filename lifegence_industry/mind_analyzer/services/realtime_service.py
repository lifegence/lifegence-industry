# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Realtime Service
Handles realtime notifications via frappe.publish_realtime
"""

import frappe
from frappe import _


def on_session_created(doc, method):
    """
    Hook: Called when a Voice Analysis Session is created
    Publishes realtime notification to the user
    """
    frappe.publish_realtime(
        "mind_analyzer_session_created",
        {
            "name": doc.name,
            "session_id": doc.session_id,
            "mode": doc.mode,
            "start_time": str(doc.start_time),
        },
        user=doc.user,
        after_commit=True
    )


def on_session_updated(doc, method):
    """
    Hook: Called when a Voice Analysis Session is updated
    Publishes realtime notification on status changes
    """
    if doc.has_value_changed("status"):
        frappe.publish_realtime(
            "mind_analyzer_session_status",
            {
                "name": doc.name,
                "session_id": doc.session_id,
                "status": doc.status,
                "end_time": str(doc.end_time) if doc.end_time else None,
                "duration_seconds": doc.duration_seconds,
                "avg_stress_load": doc.avg_stress_load,
                "avg_ps_score": doc.avg_ps_score,
            },
            user=doc.user,
            after_commit=True
        )


def publish_analysis_result(session_id: str, user: str, result_type: str, result: dict):
    """
    Publish analysis result to user via realtime

    Args:
        session_id: Session UUID
        user: Target user
        result_type: "individual" or "meeting"
        result: Analysis result dict
    """
    frappe.publish_realtime(
        "mind_analyzer_analysis",
        {
            "session_id": session_id,
            "type": result_type,
            "result": result,
        },
        user=user
    )


def publish_trigger_event(session_id: str, user: str, trigger: dict):
    """
    Publish trigger event to user via realtime

    Args:
        session_id: Session UUID
        user: Target user
        trigger: Trigger event dict
    """
    frappe.publish_realtime(
        "mind_analyzer_trigger",
        {
            "session_id": session_id,
            "trigger": trigger,
        },
        user=user
    )


def publish_statistics_update(session_id: str, user: str, statistics: dict):
    """
    Publish statistics update to user via realtime

    Args:
        session_id: Session UUID
        user: Target user
        statistics: Acoustic statistics dict
    """
    frappe.publish_realtime(
        "mind_analyzer_statistics",
        {
            "session_id": session_id,
            "statistics": statistics,
        },
        user=user
    )


def publish_error(session_id: str, user: str, error_message: str):
    """
    Publish error message to user via realtime

    Args:
        session_id: Session UUID
        user: Target user
        error_message: Error description
    """
    frappe.publish_realtime(
        "mind_analyzer_error",
        {
            "session_id": session_id,
            "error": error_message,
        },
        user=user
    )


def broadcast_to_meeting(session_name: str, event_type: str, data: dict):
    """
    Broadcast event to all participants in a meeting session

    Args:
        session_name: Session document name
        event_type: Event type identifier
        data: Event data
    """
    # For meeting mode, we might want to broadcast to multiple users
    # This is a placeholder for future multi-participant support
    session = frappe.get_doc("Voice Analysis Session", session_name)

    frappe.publish_realtime(
        f"mind_analyzer_meeting_{event_type}",
        {
            "session_id": session.session_id,
            "data": data,
        },
        user=session.user
    )


class RealtimeNotifier:
    """
    Helper class for managing realtime notifications in a session
    """

    def __init__(self, session_id: str, user: str):
        self.session_id = session_id
        self.user = user

    def notify_analysis(self, result_type: str, result: dict):
        """Send analysis result notification"""
        publish_analysis_result(self.session_id, self.user, result_type, result)

    def notify_trigger(self, trigger: dict):
        """Send trigger event notification"""
        publish_trigger_event(self.session_id, self.user, trigger)

    def notify_statistics(self, statistics: dict):
        """Send statistics update notification"""
        publish_statistics_update(self.session_id, self.user, statistics)

    def notify_error(self, error_message: str):
        """Send error notification"""
        publish_error(self.session_id, self.user, error_message)

    def notify_session_end(self, summary: dict):
        """Send session end notification with summary"""
        frappe.publish_realtime(
            "mind_analyzer_session_end",
            {
                "session_id": self.session_id,
                "summary": summary,
            },
            user=self.user
        )
