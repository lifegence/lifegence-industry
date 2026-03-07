# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Trigger Detection Service
Detects psychological state triggers from audio statistics and transcripts
"""

import re
import time
from typing import Dict, List, Optional

import frappe


# Japanese patterns for detection
TRIGGER_PATTERNS = {
    # Apology/shrinking phrases
    "apology": re.compile(r'すみません|申し訳|ごめんなさい|私が悪い|私のせい'),

    # Hedge words
    "hedge": re.compile(r'多分|一応|かもしれない|たぶん|おそらく|ちょっと|少し|まあ|なんか'),

    # Restart/correction patterns
    "restart": re.compile(r'いや、|じゃなくて|というか|ではなく|つまり|要するに'),

    # Filler words
    "filler": re.compile(r'えー|あー|えーと|あのー|えっと|まあ|うーん'),

    # Dissent/questions (positive signal)
    "dissent": re.compile(r'でも|しかし|ただ|一方で|懸念|心配|疑問|なぜ|どうして'),

    # Acknowledgment (positive signal)
    "acknowledgment": re.compile(r'なるほど|そうですね|確かに|おっしゃる通り|いいですね|賛成'),
}


class TriggerDetector:
    """
    Trigger detector for psychological state analysis.
    Ported from voice-analizer TypeScript implementation.
    """

    def __init__(self, config: dict = None):
        self.config = self._get_default_config()
        if config:
            self.config.update(config)

        self.recent_triggers: List[dict] = []
        self.trigger_counts: Dict[str, List[int]] = {
            "silence_spike": [],
            "apology_phrase": [],
            "hedge_increase": [],
            "speech_rate_change": [],
            "restart_increase": [],
            "interruption": [],
            "overlap": [],
            "power_imbalance": [],
        }
        self.baseline_speech_rate = 1.0
        self.speech_rate_history: List[float] = []

    def _get_default_config(self) -> dict:
        """Get default configuration, optionally from settings"""
        try:
            from lifegence_mind_analyzer.mind_analyzer.doctype.mind_analyzer_settings.mind_analyzer_settings import VoiceAnalyzerSettings
            return VoiceAnalyzerSettings.get_trigger_config()
        except Exception:
            return {
                "silence_spike_threshold_ms": 3000,
                "silence_spike_count_per_min": 2,
                "hedge_count_per_min": 5,
                "speech_rate_change_percent": 30,
                "restart_count_per_min": 4,
            }

    def detect(self, statistics: dict, session_name: str = None, transcript: str = None) -> List[dict]:
        """
        Detect triggers from statistics and transcript

        Args:
            statistics: Acoustic statistics dict
            session_name: Session document name (for context)
            transcript: Optional transcript text

        Returns:
            list: List of detected triggers
        """
        now = int(time.time() * 1000)
        triggers = []

        # 1. Check silence spike
        silence_trigger = self._check_silence_spike(statistics, now)
        if silence_trigger:
            triggers.append(silence_trigger)

        # 2. Check speech rate change
        rate_trigger = self._check_speech_rate_change(statistics, now)
        if rate_trigger:
            triggers.append(rate_trigger)

        # 3. Analyze transcript if available
        if transcript:
            transcript_triggers = self._analyze_transcript(transcript, now)
            triggers.extend(transcript_triggers)

        # Prune old trigger counts
        self._prune_old_counts(now)

        # Store recent triggers
        for trigger in triggers:
            self.recent_triggers.append(trigger)
            if len(self.recent_triggers) > 10:
                self.recent_triggers.pop(0)

        return triggers

    def _check_silence_spike(self, statistics: dict, timestamp: int) -> Optional[dict]:
        """Check for silence spike trigger"""
        silence_ms = statistics.get("silence_max_ms", 0)
        threshold = self.config.get("silence_spike_threshold_ms", 3000)

        if silence_ms >= threshold:
            self.trigger_counts["silence_spike"].append(timestamp)

            recent_count = self._get_recent_count("silence_spike", timestamp)
            count_threshold = self.config.get("silence_spike_count_per_min", 2)

            if recent_count >= count_threshold:
                severity = min(1.0, silence_ms / 10000)
                return {
                    "type": "silence_spike",
                    "timestamp": timestamp,
                    "severity": round(severity, 3),
                    "evidence": f"{silence_ms / 1000:.1f}秒の沈黙（{recent_count}回/分）",
                    "metadata": {
                        "silence_ms": silence_ms,
                        "count_per_min": recent_count,
                    }
                }

        return None

    def _check_speech_rate_change(self, statistics: dict, timestamp: int) -> Optional[dict]:
        """Check for speech rate change trigger"""
        current_rate = statistics.get("speech_rate_relative", 1.0)

        # Update baseline
        self.speech_rate_history.append(current_rate)
        if len(self.speech_rate_history) > 100:
            self.speech_rate_history.pop(0)

        if len(self.speech_rate_history) >= 10:
            recent_rates = self.speech_rate_history[-50:]
            self.baseline_speech_rate = sum(recent_rates) / len(recent_rates)

        # Check for significant change
        if self.baseline_speech_rate > 0:
            change_percent = abs(current_rate - self.baseline_speech_rate) / self.baseline_speech_rate * 100
            threshold = self.config.get("speech_rate_change_percent", 30)

            if change_percent >= threshold:
                direction = "加速" if current_rate > self.baseline_speech_rate else "減速"
                severity = min(1.0, change_percent / 60)

                return {
                    "type": "speech_rate_change",
                    "timestamp": timestamp,
                    "severity": round(severity, 3),
                    "evidence": f"話速が{change_percent:.0f}%{direction}（基準: {self.baseline_speech_rate:.2f}x → 現在: {current_rate:.2f}x）",
                    "metadata": {
                        "baseline": self.baseline_speech_rate,
                        "current": current_rate,
                        "change_percent": change_percent,
                    }
                }

        return None

    def _analyze_transcript(self, transcript: str, timestamp: int) -> List[dict]:
        """Analyze transcript for triggers"""
        triggers = []

        # Check apology phrases
        apology_matches = TRIGGER_PATTERNS["apology"].findall(transcript)
        if apology_matches:
            self.trigger_counts["apology_phrase"].append(timestamp)
            recent_count = self._get_recent_count("apology_phrase", timestamp)

            if recent_count >= 3:
                severity = min(1.0, recent_count / 5)
                triggers.append({
                    "type": "apology_phrase",
                    "timestamp": timestamp,
                    "severity": round(severity, 3),
                    "evidence": f"謝罪・萎縮表現: 「{apology_matches[0]}」等（{recent_count}回/分）",
                    "metadata": {"matches": apology_matches}
                })

        # Check hedge phrases
        hedge_matches = TRIGGER_PATTERNS["hedge"].findall(transcript)
        if hedge_matches:
            for _ in hedge_matches:
                self.trigger_counts["hedge_increase"].append(timestamp)

            recent_count = self._get_recent_count("hedge_increase", timestamp)
            threshold = self.config.get("hedge_count_per_min", 5)

            if recent_count >= threshold:
                severity = min(1.0, recent_count / 10)
                sample = hedge_matches[:3]
                triggers.append({
                    "type": "hedge_increase",
                    "timestamp": timestamp,
                    "severity": round(severity, 3),
                    "evidence": f"断定回避表現: 「{'」「'.join(sample)}」等（{recent_count}回/分）",
                    "metadata": {"matches": hedge_matches}
                })

        # Check restart phrases
        restart_matches = TRIGGER_PATTERNS["restart"].findall(transcript)
        if restart_matches:
            for _ in restart_matches:
                self.trigger_counts["restart_increase"].append(timestamp)

            recent_count = self._get_recent_count("restart_increase", timestamp)
            threshold = self.config.get("restart_count_per_min", 4)

            if recent_count >= threshold:
                severity = min(1.0, recent_count / 8)
                triggers.append({
                    "type": "restart_increase",
                    "timestamp": timestamp,
                    "severity": round(severity, 3),
                    "evidence": f"言い直し: 「{restart_matches[0]}」等（{recent_count}回/分）",
                    "metadata": {"matches": restart_matches}
                })

        return triggers

    def _get_recent_count(self, trigger_type: str, now: int) -> int:
        """Get count of triggers in the last minute"""
        one_minute_ago = now - 60000
        return len([t for t in self.trigger_counts[trigger_type] if t > one_minute_ago])

    def _prune_old_counts(self, now: int):
        """Remove trigger counts older than one minute"""
        one_minute_ago = now - 60000
        for trigger_type in self.trigger_counts:
            self.trigger_counts[trigger_type] = [
                t for t in self.trigger_counts[trigger_type]
                if t > one_minute_ago
            ]

    def get_recent_triggers(self) -> List[dict]:
        """Get recent triggers"""
        return list(self.recent_triggers)

    def get_trigger_stats(self) -> Dict[str, int]:
        """Get trigger statistics (counts per minute)"""
        now = int(time.time() * 1000)
        return {
            trigger_type: self._get_recent_count(trigger_type, now)
            for trigger_type in self.trigger_counts
        }

    def reset(self):
        """Reset detector state"""
        self.recent_triggers = []
        for trigger_type in self.trigger_counts:
            self.trigger_counts[trigger_type] = []
        self.speech_rate_history = []
        self.baseline_speech_rate = 1.0
