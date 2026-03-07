# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class IndividualAnalysisResult(Document):
    def before_insert(self):
        if not self.timestamp:
            self.timestamp = now_datetime()

    def validate(self):
        self.validate_metrics()
        self.validate_evidence()

    def validate_metrics(self):
        """Ensure all metrics are within valid range"""
        metrics = [
            "stress_load",
            "anxiety_uncertainty",
            "cognitive_load",
            "confidence_assertiveness",
            "stability",
            "analysis_confidence"
        ]
        for metric in metrics:
            value = getattr(self, metric, None)
            if value is not None:
                if value < 0 or value > 1:
                    frappe.throw(f"{metric} must be between 0 and 1")

    def validate_evidence(self):
        """Validate evidence JSON format"""
        if self.evidence:
            if isinstance(self.evidence, str):
                try:
                    json.loads(self.evidence)
                except json.JSONDecodeError:
                    frappe.throw("Evidence must be valid JSON")

    def as_dict_for_api(self):
        """Return result as dict for API response"""
        return {
            "stress_load": self.stress_load,
            "anxiety_uncertainty": self.anxiety_uncertainty,
            "cognitive_load": self.cognitive_load,
            "confidence_assertiveness": self.confidence_assertiveness,
            "stability": self.stability,
            "confidence": self.analysis_confidence,
            "evidence": json.loads(self.evidence) if self.evidence else [],
            "suggestion": self.suggestion,
            "timestamp": str(self.timestamp)
        }

    @staticmethod
    def create_from_analysis(session_name, analysis_result):
        """Create result document from analysis dict"""
        doc = frappe.new_doc("Individual Analysis Result")
        doc.session = session_name
        doc.timestamp = now_datetime()
        doc.stress_load = analysis_result.get("stress_load", 0)
        doc.anxiety_uncertainty = analysis_result.get("anxiety_uncertainty", 0)
        doc.cognitive_load = analysis_result.get("cognitive_load", 0)
        doc.confidence_assertiveness = analysis_result.get("confidence_assertiveness", 0)
        doc.stability = analysis_result.get("stability", 0)
        doc.analysis_confidence = analysis_result.get("confidence", 0)
        doc.evidence = json.dumps(analysis_result.get("evidence", []))
        doc.suggestion = analysis_result.get("suggestion", "")
        doc.insert(ignore_permissions=True)
        return doc
