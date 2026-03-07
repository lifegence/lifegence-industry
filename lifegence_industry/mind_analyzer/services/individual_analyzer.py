# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Individual Analyzer Service
Analyzes individual psychological state from voice data
"""

from typing import Dict, List, Optional

import frappe

from lifegence_industry.mind_analyzer.services.gemini_service import GeminiService


class IndividualAnalyzer:
    """
    Individual psychological state analyzer.
    Combines statistics, triggers, and LLM analysis.
    """

    def __init__(self):
        self.gemini_service = GeminiService()

        # Tracking for patterns
        self.stress_patterns = {
            "voice_variance": [],
            "silence_frequency": [],
        }
        self.anxiety_patterns = {
            "filler_rate": [],
            "hedge_count": [],
        }

    def analyze(
        self,
        statistics: dict,
        triggers: List[dict],
        transcript: str = None
    ) -> dict:
        """
        Analyze individual psychological state

        Args:
            statistics: Acoustic statistics from AudioProcessor
            triggers: Detected triggers from TriggerDetector
            transcript: Optional transcript text

        Returns:
            dict: Analysis result with psychological metrics
        """
        # Update internal patterns
        self._update_patterns(statistics, triggers)

        # Calculate indicator levels from patterns
        pattern_indicators = self._calculate_indicators(statistics, triggers)

        # Get LLM analysis
        llm_result = self.gemini_service.analyze_individual(
            statistics, triggers, transcript
        )

        # Combine pattern analysis with LLM analysis
        result = self._combine_analysis(pattern_indicators, llm_result)

        # Generate suggestion if needed
        if not result.get("suggestion"):
            result["suggestion"] = self._generate_suggestion(result)

        return result

    def _update_patterns(self, statistics: dict, triggers: List[dict]):
        """Update internal pattern tracking"""
        import time

        # Voice variance tracking
        self.stress_patterns["voice_variance"].append(
            statistics.get("rms_variance", 0)
        )
        if len(self.stress_patterns["voice_variance"]) > 100:
            self.stress_patterns["voice_variance"].pop(0)

        # Silence frequency tracking
        if statistics.get("silence_max_ms", 0) > 1000:
            self.stress_patterns["silence_frequency"].append(time.time())

        # Keep only last minute
        one_minute_ago = time.time() - 60
        self.stress_patterns["silence_frequency"] = [
            t for t in self.stress_patterns["silence_frequency"]
            if t > one_minute_ago
        ]

        # Filler rate tracking
        self.anxiety_patterns["filler_rate"].append(
            statistics.get("filler_rate", 0)
        )
        if len(self.anxiety_patterns["filler_rate"]) > 50:
            self.anxiety_patterns["filler_rate"].pop(0)

        # Hedge count tracking (from triggers)
        hedge_triggers = [t for t in triggers if t.get("type") == "hedge_increase"]
        self.anxiety_patterns["hedge_count"].append(len(hedge_triggers))
        if len(self.anxiety_patterns["hedge_count"]) > 30:
            self.anxiety_patterns["hedge_count"].pop(0)

    def _calculate_indicators(self, statistics: dict, triggers: List[dict]) -> dict:
        """Calculate indicator levels from patterns"""

        def mean(values):
            return sum(values) / len(values) if values else 0

        # Stress level
        voice_variance_mean = mean(self.stress_patterns["voice_variance"])
        silence_freq = len(self.stress_patterns["silence_frequency"])
        stress_level = min(1.0, (voice_variance_mean / 0.3) * 0.5 + (silence_freq / 5) * 0.5)

        # Anxiety level
        filler_rate_mean = mean(self.anxiety_patterns["filler_rate"])
        hedge_count_sum = sum(self.anxiety_patterns["hedge_count"])
        anxiety_level = min(1.0, (filler_rate_mean / 0.15) * 0.4 + (hedge_count_sum / 15) * 0.6)

        # Cognitive load
        speech_rate = statistics.get("speech_rate_relative", 1.0)
        speech_rate_deviation = abs(1.0 - speech_rate)
        restart_triggers = [t for t in triggers if t.get("type") == "restart_increase"]
        cognitive_level = min(1.0, len(restart_triggers) / 3 + speech_rate_deviation * 0.3)

        # Confidence (inverse of hedge patterns)
        confidence_level = max(0.0, 1.0 - hedge_count_sum / 10 - filler_rate_mean * 2)

        # Stability
        stability_level = max(0.0, 1.0 - stress_level * 0.4 - anxiety_level * 0.3 - cognitive_level * 0.3)

        return {
            "stress_load": round(stress_level, 3),
            "anxiety_uncertainty": round(anxiety_level, 3),
            "cognitive_load": round(cognitive_level, 3),
            "confidence_assertiveness": round(confidence_level, 3),
            "stability": round(stability_level, 3),
        }

    def _combine_analysis(self, pattern_indicators: dict, llm_result: dict) -> dict:
        """
        Combine pattern-based and LLM-based analysis.
        Weight LLM result more heavily when confidence is high.
        """
        llm_confidence = llm_result.get("confidence", 0.5)

        # Weight: higher LLM confidence = more weight on LLM result
        llm_weight = 0.3 + (llm_confidence * 0.4)  # 0.3 to 0.7
        pattern_weight = 1.0 - llm_weight

        combined = {}
        metrics = [
            "stress_load",
            "anxiety_uncertainty",
            "cognitive_load",
            "confidence_assertiveness",
            "stability"
        ]

        for metric in metrics:
            pattern_value = pattern_indicators.get(metric, 0.5)
            llm_value = llm_result.get(metric, 0.5)
            combined[metric] = round(
                pattern_value * pattern_weight + llm_value * llm_weight,
                3
            )

        # Use LLM evidence and suggestion
        combined["confidence"] = llm_result.get("confidence", 0.5)
        combined["evidence"] = llm_result.get("evidence", [])
        combined["suggestion"] = llm_result.get("suggestion")

        return combined

    def _generate_suggestion(self, result: dict) -> Optional[str]:
        """Generate improvement suggestion based on analysis"""
        suggestions = []

        if result.get("stress_load", 0) > 0.7:
            suggestions.append("深呼吸を意識し、一度ゆっくり話してみてください")

        if result.get("anxiety_uncertainty", 0) > 0.7:
            suggestions.append("自分の意見を「〜と考えます」と明確に述べてみてください")

        if result.get("cognitive_load", 0) > 0.7:
            suggestions.append("情報を整理してから話すと、より伝わりやすくなります")

        if result.get("confidence_assertiveness", 0) < 0.3:
            suggestions.append("自信を持って発言してください。あなたの意見には価値があります")

        if suggestions:
            return "。".join(suggestions)

        if result.get("stability", 0) > 0.7:
            return "安定した状態で会話できています"

        return None

    def get_patterns_summary(self) -> dict:
        """Get summary of tracked patterns"""

        def mean(values):
            return sum(values) / len(values) if values else 0

        return {
            "stress_patterns": {
                "variance": mean(self.stress_patterns["voice_variance"]),
                "frequency": len(self.stress_patterns["silence_frequency"]),
            },
            "anxiety_patterns": {
                "filler_rate": mean(self.anxiety_patterns["filler_rate"]),
                "hedge_count": sum(self.anxiety_patterns["hedge_count"]),
            }
        }

    def reset(self):
        """Reset analyzer state"""
        self.stress_patterns = {"voice_variance": [], "silence_frequency": []}
        self.anxiety_patterns = {"filler_rate": [], "hedge_count": []}
