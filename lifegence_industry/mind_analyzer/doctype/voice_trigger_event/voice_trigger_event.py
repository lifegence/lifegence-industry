# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class VoiceTriggerEvent(Document):
    def before_insert(self):
        if not self.timestamp:
            self.timestamp = now_datetime()

    def validate(self):
        self.validate_severity()
        self.validate_metadata()

    def validate_severity(self):
        """Ensure severity is within valid range"""
        if self.severity is not None:
            if self.severity < 0 or self.severity > 1:
                frappe.throw("Severity must be between 0 and 1")

    def validate_metadata(self):
        """Validate metadata JSON format"""
        if self.metadata:
            if isinstance(self.metadata, str):
                try:
                    json.loads(self.metadata)
                except json.JSONDecodeError:
                    frappe.throw("Metadata must be valid JSON")

    def as_dict_for_api(self):
        """Return trigger as dict for API response"""
        return {
            "type": self.trigger_type,
            "timestamp": str(self.timestamp),
            "severity": self.severity,
            "evidence": self.evidence,
            "metadata": json.loads(self.metadata) if self.metadata else {}
        }

    @staticmethod
    def create_trigger(session_name, trigger_data):
        """Create trigger event from detected trigger"""
        doc = frappe.new_doc("Voice Trigger Event")
        doc.session = session_name
        doc.trigger_type = trigger_data.get("type")
        doc.timestamp = now_datetime()
        doc.severity = trigger_data.get("severity", 0.5)
        doc.evidence = trigger_data.get("evidence", "")
        doc.metadata = json.dumps(trigger_data.get("metadata", {}))
        doc.insert(ignore_permissions=True)
        return doc

    @staticmethod
    def get_recent_triggers(session_name, limit=10):
        """Get recent triggers for a session"""
        triggers = frappe.get_all(
            "Voice Trigger Event",
            filters={"session": session_name},
            fields=["trigger_type", "timestamp", "severity", "evidence", "metadata"],
            order_by="timestamp desc",
            limit=limit
        )
        return triggers
