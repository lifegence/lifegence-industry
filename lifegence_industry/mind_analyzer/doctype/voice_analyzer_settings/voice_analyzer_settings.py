# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VoiceAnalyzerSettings(Document):
    def validate(self):
        self.validate_thresholds()

    def validate_thresholds(self):
        if self.trigger_threshold < 0 or self.trigger_threshold > 1:
            frappe.throw("Trigger threshold must be between 0 and 1")

        if self.analysis_interval_sec < 5:
            frappe.throw("Analysis interval must be at least 5 seconds")

        if self.data_retention_days < 1:
            frappe.throw("Data retention days must be at least 1")

    @staticmethod
    def get_settings():
        """Get voice analyzer settings singleton"""
        return frappe.get_single("Voice Analyzer Settings")

    @staticmethod
    def get_gemini_api_key():
        """Get decrypted Gemini API key. Falls back to Company OS AI Settings."""
        settings = VoiceAnalyzerSettings.get_settings()
        key = settings.get_password("gemini_api_key")
        if key:
            return key
        try:
            cos = frappe.get_single("Company OS AI Settings")
            return cos.get_password("gemini_api_key")
        except Exception:
            return None

    @staticmethod
    def get_trigger_config():
        """Get trigger configuration as dict"""
        settings = VoiceAnalyzerSettings.get_settings()
        return {
            "silence_spike_threshold_ms": settings.silence_spike_threshold_ms or 3000,
            "silence_spike_count_per_min": settings.silence_spike_count_per_min or 3,
            "hedge_count_per_min": settings.hedge_count_per_min or 5,
            "speech_rate_change_percent": settings.speech_rate_change_percent or 30,
            "restart_count_per_min": settings.restart_count_per_min or 4,
        }
