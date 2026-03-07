# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class MeetingAnalysisResult(Document):
    def before_insert(self):
        if not self.timestamp:
            self.timestamp = now_datetime()

    def validate(self):
        self.validate_metrics()
        self.validate_json_fields()

    def validate_metrics(self):
        """Ensure all metrics are within valid range"""
        metrics = [
            "speak_up",
            "respect_interaction",
            "error_tolerance",
            "power_balance",
            "overall_ps",
            "analysis_confidence"
        ]
        for metric in metrics:
            value = getattr(self, metric, None)
            if value is not None:
                if value < 0 or value > 1:
                    frappe.throw(f"{metric} must be between 0 and 1")

    def validate_json_fields(self):
        """Validate JSON fields format"""
        json_fields = ["key_moments", "speaker_stats"]
        for field in json_fields:
            value = getattr(self, field, None)
            if value:
                if isinstance(value, str):
                    try:
                        json.loads(value)
                    except json.JSONDecodeError:
                        frappe.throw(f"{field} must be valid JSON")

    def as_dict_for_api(self):
        """Return result as dict for API response"""
        return {
            "speak_up": self.speak_up,
            "respect_interaction": self.respect_interaction,
            "error_tolerance": self.error_tolerance,
            "power_balance": self.power_balance,
            "overall_ps": self.overall_ps,
            "confidence": self.analysis_confidence,
            "key_moments": json.loads(self.key_moments) if self.key_moments else [],
            "speaker_stats": json.loads(self.speaker_stats) if self.speaker_stats else {},
            "timestamp": str(self.timestamp)
        }

    @staticmethod
    def create_from_analysis(session_name, analysis_result):
        """Create result document from analysis dict"""
        doc = frappe.new_doc("Meeting Analysis Result")
        doc.session = session_name
        doc.timestamp = now_datetime()
        doc.speak_up = analysis_result.get("speak_up", 0)
        doc.respect_interaction = analysis_result.get("respect_interaction", 0)
        doc.error_tolerance = analysis_result.get("error_tolerance", 0)
        doc.power_balance = analysis_result.get("power_balance", 0)
        doc.overall_ps = analysis_result.get("overall_ps", 0)
        doc.analysis_confidence = analysis_result.get("confidence", 0)
        doc.key_moments = json.dumps(analysis_result.get("key_moments", []))
        doc.speaker_stats = json.dumps(analysis_result.get("speaker_stats", {}))
        doc.insert(ignore_permissions=True)
        return doc
