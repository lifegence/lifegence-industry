# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class AcousticStatistics(Document):
    def before_insert(self):
        if not self.timestamp:
            self.timestamp = now_datetime()

    def as_dict_for_api(self):
        """Return statistics as dict for API response"""
        return {
            "speech_ratio": self.speech_ratio,
            "silence_mean_ms": self.silence_mean_ms,
            "silence_max_ms": self.silence_max_ms,
            "speech_rate_relative": self.speech_rate_relative,
            "filler_rate": self.filler_rate,
            "rms_level": self.rms_level,
            "rms_variance": self.rms_variance,
            "timestamp": str(self.timestamp)
        }

    @staticmethod
    def create_from_stats(session_name, stats_data):
        """Create statistics document from computed stats"""
        doc = frappe.new_doc("Acoustic Statistics")
        doc.session = session_name
        doc.timestamp = now_datetime()
        doc.speech_ratio = stats_data.get("speech_ratio", 0)
        doc.silence_mean_ms = stats_data.get("silence_mean_ms", 0)
        doc.silence_max_ms = stats_data.get("silence_max_ms", 0)
        doc.speech_rate_relative = stats_data.get("speech_rate_relative", 1.0)
        doc.filler_rate = stats_data.get("filler_rate", 0)
        doc.rms_level = stats_data.get("rms_level", 0)
        doc.rms_variance = stats_data.get("rms_variance", 0)
        doc.insert(ignore_permissions=True)
        return doc

    @staticmethod
    def get_latest_stats(session_name):
        """Get latest statistics for a session"""
        stats = frappe.get_all(
            "Acoustic Statistics",
            filters={"session": session_name},
            fields=["*"],
            order_by="timestamp desc",
            limit=1
        )
        return stats[0] if stats else None

    @staticmethod
    def get_stats_history(session_name, limit=100):
        """Get statistics history for a session"""
        return frappe.get_all(
            "Acoustic Statistics",
            filters={"session": session_name},
            fields=[
                "timestamp", "speech_ratio", "silence_mean_ms",
                "speech_rate_relative", "rms_level"
            ],
            order_by="timestamp asc",
            limit=limit
        )
