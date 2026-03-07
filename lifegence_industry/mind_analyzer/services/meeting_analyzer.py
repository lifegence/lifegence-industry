# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Meeting Analyzer Service
Analyzes meeting psychological safety from voice data
"""

from typing import Dict, List, Optional

import frappe

from lifegence_industry.mind_analyzer.services.gemini_service import GeminiService


class MeetingAnalyzer:
    """
    Meeting psychological safety analyzer.
    Analyzes team dynamics and psychological safety indicators.
    """

    def __init__(self):
        self.gemini_service = GeminiService()

        # Speaker tracking
        self.speaker_stats: Dict[str, dict] = {}
        self.interaction_patterns: List[dict] = []
        self.key_moments: List[dict] = []

        # Meeting metrics tracking
        self.total_speaking_time = 0
        self.interruption_count = 0
        self.overlap_count = 0

    def analyze(
        self,
        statistics: dict,
        triggers: List[dict],
        speaker_id: str = None
    ) -> dict:
        """
        Analyze meeting psychological safety

        Args:
            statistics: Acoustic statistics from AudioProcessor
            triggers: Detected triggers from TriggerDetector
            speaker_id: Optional speaker identifier

        Returns:
            dict: Analysis result with PS metrics
        """
        # Update speaker stats if speaker identified
        if speaker_id:
            self._update_speaker_stats(speaker_id, statistics)

        # Update interaction patterns
        self._update_interaction_patterns(triggers)

        # Calculate PS metrics from patterns
        pattern_metrics = self._calculate_ps_metrics(statistics, triggers)

        # Get LLM analysis
        llm_result = self.gemini_service.analyze_meeting(
            statistics, triggers, self.speaker_stats
        )

        # Combine analyses
        result = self._combine_analysis(pattern_metrics, llm_result)

        # Add key moments
        result["key_moments"] = self._get_recent_key_moments()
        result["speaker_stats"] = self._get_speaker_summary()

        return result

    def _update_speaker_stats(self, speaker_id: str, statistics: dict):
        """Update statistics for a specific speaker"""
        if speaker_id not in self.speaker_stats:
            self.speaker_stats[speaker_id] = {
                "speaking_time": 0,
                "utterance_count": 0,
                "interruptions_made": 0,
                "interruptions_received": 0,
                "avg_silence_after": 0,
                "silence_samples": [],
            }

        stats = self.speaker_stats[speaker_id]
        stats["utterance_count"] += 1
        stats["speaking_time"] += statistics.get("speech_ratio", 0) * 10  # Assume 10s window

        # Track silence after this speaker
        silence_ms = statistics.get("silence_mean_ms", 0)
        stats["silence_samples"].append(silence_ms)
        if len(stats["silence_samples"]) > 20:
            stats["silence_samples"].pop(0)
        stats["avg_silence_after"] = sum(stats["silence_samples"]) / len(stats["silence_samples"])

    def _update_interaction_patterns(self, triggers: List[dict]):
        """Update interaction patterns from triggers"""
        import time

        for trigger in triggers:
            trigger_type = trigger.get("type", "")

            # Track interruptions
            if trigger_type == "interruption":
                self.interruption_count += 1
                self._add_key_moment(
                    "interruption",
                    trigger.get("evidence", "遮断が発生"),
                    -0.5
                )

            # Track overlaps
            elif trigger_type == "overlap":
                self.overlap_count += 1
                self._add_key_moment(
                    "overlap",
                    trigger.get("evidence", "発言の重複"),
                    -0.3
                )

            # Track power imbalance
            elif trigger_type == "power_imbalance":
                self._add_key_moment(
                    "power_imbalance",
                    trigger.get("evidence", "発言機会の偏り"),
                    -0.7
                )

            # Track apology patterns (error tolerance indicator)
            elif trigger_type == "apology_phrase":
                self._add_key_moment(
                    "excessive_apology",
                    trigger.get("evidence", "過度な謝罪"),
                    -0.4
                )

    def _add_key_moment(self, event_type: str, description: str, impact: float):
        """Add a key moment to the list"""
        import time

        self.key_moments.append({
            "timestamp_sec": int(time.time()),
            "event": f"{event_type}: {description}",
            "impact": impact
        })

        # Keep only last 20 moments
        if len(self.key_moments) > 20:
            self.key_moments.pop(0)

    def _calculate_ps_metrics(self, statistics: dict, triggers: List[dict]) -> dict:
        """Calculate psychological safety metrics from patterns"""
        # Speak Up: Based on speech ratio and participation
        speech_ratio = statistics.get("speech_ratio", 0.5)
        speak_up = min(1.0, speech_ratio * 1.5)

        # Respect Interaction: Based on interruptions
        interruption_triggers = [t for t in triggers if t.get("type") == "interruption"]
        respect = max(0.0, 1.0 - len(interruption_triggers) * 0.2 - self.interruption_count * 0.05)

        # Error Tolerance: Based on apology patterns
        apology_triggers = [t for t in triggers if t.get("type") == "apology_phrase"]
        error_tolerance = max(0.0, 1.0 - len(apology_triggers) * 0.15)

        # Power Balance: Based on speaking time distribution
        power_balance = self._calculate_power_balance()

        # Overall PS score
        overall_ps = (speak_up + respect + error_tolerance + power_balance) / 4

        return {
            "speak_up": round(speak_up, 3),
            "respect_interaction": round(respect, 3),
            "error_tolerance": round(error_tolerance, 3),
            "power_balance": round(power_balance, 3),
            "overall_ps": round(overall_ps, 3),
        }

    def _calculate_power_balance(self) -> float:
        """Calculate power balance from speaker statistics"""
        if not self.speaker_stats:
            return 0.7  # Default moderate score

        speaking_times = [
            stats.get("speaking_time", 0)
            for stats in self.speaker_stats.values()
        ]

        if not speaking_times or sum(speaking_times) == 0:
            return 0.7

        # Calculate Gini coefficient for speaking time distribution
        # Lower Gini = more equal distribution = higher power balance
        n = len(speaking_times)
        if n == 1:
            return 0.5  # Single speaker, neutral

        speaking_times.sort()
        total = sum(speaking_times)

        # Calculate Gini coefficient
        cumulative = 0
        gini_sum = 0
        for i, time in enumerate(speaking_times):
            cumulative += time
            gini_sum += (2 * (i + 1) - n - 1) * time

        gini = gini_sum / (n * total) if total > 0 else 0

        # Convert Gini to power balance (0 Gini = 1.0 balance, 1 Gini = 0 balance)
        return max(0.0, 1.0 - gini)

    def _combine_analysis(self, pattern_metrics: dict, llm_result: dict) -> dict:
        """Combine pattern-based and LLM-based analysis"""
        llm_confidence = llm_result.get("confidence", 0.5)

        # Weight based on LLM confidence
        llm_weight = 0.3 + (llm_confidence * 0.4)
        pattern_weight = 1.0 - llm_weight

        combined = {}
        metrics = [
            "speak_up",
            "respect_interaction",
            "error_tolerance",
            "power_balance",
            "overall_ps"
        ]

        for metric in metrics:
            pattern_value = pattern_metrics.get(metric, 0.5)
            llm_value = llm_result.get(metric, 0.5)
            combined[metric] = round(
                pattern_value * pattern_weight + llm_value * llm_weight,
                3
            )

        combined["confidence"] = llm_result.get("confidence", 0.5)

        return combined

    def _get_recent_key_moments(self) -> List[dict]:
        """Get recent key moments"""
        return self.key_moments[-10:]

    def _get_speaker_summary(self) -> dict:
        """Get summary of speaker statistics"""
        summary = {}
        total_time = sum(
            stats.get("speaking_time", 0)
            for stats in self.speaker_stats.values()
        )

        for speaker_id, stats in self.speaker_stats.items():
            speaking_time = stats.get("speaking_time", 0)
            summary[speaker_id] = {
                "speaking_time": round(speaking_time, 1),
                "speaking_ratio": round(speaking_time / total_time, 3) if total_time > 0 else 0,
                "utterance_count": stats.get("utterance_count", 0),
                "avg_silence_after": round(stats.get("avg_silence_after", 0), 0),
            }

        return summary

    def add_positive_moment(self, event_type: str, description: str):
        """Add a positive key moment (for external use)"""
        self._add_key_moment(event_type, description, 0.5)

    def reset(self):
        """Reset analyzer state"""
        self.speaker_stats = {}
        self.interaction_patterns = []
        self.key_moments = []
        self.total_speaking_time = 0
        self.interruption_count = 0
        self.overlap_count = 0
