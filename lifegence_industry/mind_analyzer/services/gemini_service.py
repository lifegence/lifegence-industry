# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Gemini LLM Service
Integration with Google Gemini for psychological state analysis
"""

import json
from typing import Dict, List, Optional

import frappe
from frappe import _

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


# System prompts
INDIVIDUAL_SYSTEM_PROMPT = """あなたは心理状態分析の専門家です。
発話テキストと音響統計から、話者の心理状態を推定してください。

【重要な制約】
- これは診断ではなく推定です
- 各指標は0-1のスコアで出力
- 必ず根拠（evidence）を提示
- 断定的表現は使用禁止（「〜の可能性が高い」形式で）
- 医学的・臨床的判断は行わない

【音響統計の解釈ガイド】
1. speech_ratio (発話率):
   - 高い（>0.7）: 活発に発話している
   - 中程度（0.4-0.7）: 通常の会話
   - 低い（<0.4）: 沈黙が多い、躊躇している可能性

2. silence_mean_ms (平均沈黙長):
   - 短い（<500ms）: 即座に返答、流暢
   - 中程度（500-1500ms）: 思考しながら発話
   - 長い（>1500ms）: 躊躇、不確実性、慎重

3. filler_rate (フィラー率):
   - 低い（<0.05）: 流暢、準備されている
   - 中程度（0.05-0.15）: 自然な会話
   - 高い（>0.15）: 認知負荷、不確実性

4. speech_rate_rel (相対話速):
   - 高い（>1.2）: 焦り、興奮、熱意
   - 通常（0.8-1.2）: 安定した発話
   - 低い（<0.8）: 慎重、疲労、躊躇

5. rms_variance (音量変動):
   - 高い: 感情的起伏、強調
   - 低い: 単調、抑制された感情

【出力形式】
JSON形式で以下を出力してください:
{
  "stress_load": 0.0-1.0,
  "anxiety_uncertainty": 0.0-1.0,
  "cognitive_load": 0.0-1.0,
  "confidence_assertiveness": 0.0-1.0,
  "stability": 0.0-1.0,
  "confidence": 0.0-1.0,
  "evidence": ["根拠1", "根拠2", ...],
  "suggestion": "改善提案（任意）"
}"""

MEETING_SYSTEM_PROMPT = """あなたは組織心理学と心理的安全性の専門家です。
会議の音響統計とイベントから、チームの心理的安全性を評価してください。

【心理的安全性の4つの柱】
1. speak_up: 発言の自由度 - 自分の意見を言いやすいか
2. respect_interaction: 対人尊重 - 互いを尊重しているか
3. error_tolerance: 失敗許容度 - 失敗を恐れずにチャレンジできるか
4. power_balance: 権力バランス - 発言機会が均等か

【評価のポイント】
- 沈黙パターン: 特定の人の発言後に沈黙→心理的抑圧の可能性
- 発言の偏り: 一人が80%以上→power_imbalance
- 遮断: 発言中に遮られる→respect低下
- 謝罪過多: 頻繁な謝罪→error_tolerance低下

【出力形式】
JSON形式で以下を出力してください:
{
  "speak_up": 0.0-1.0,
  "respect_interaction": 0.0-1.0,
  "error_tolerance": 0.0-1.0,
  "power_balance": 0.0-1.0,
  "overall_ps": 0.0-1.0,
  "confidence": 0.0-1.0,
  "key_moments": [
    {"timestamp_sec": 0, "event": "説明", "impact": -1.0 to 1.0}
  ],
  "speaker_stats": {}
}"""


class GeminiService:
    """
    Gemini API integration for psychological analysis
    """

    def __init__(self):
        self.model = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Gemini client with API key from settings"""
        if not GENAI_AVAILABLE:
            frappe.log_error("google-generativeai package not installed")
            return

        try:
            from lifegence_industry.mind_analyzer.mind_analyzer.doctype.mind_analyzer_settings.mind_analyzer_settings import VoiceAnalyzerSettings
            api_key = VoiceAnalyzerSettings.get_gemini_api_key()

            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            frappe.log_error(f"Failed to initialize Gemini: {str(e)}")

    def analyze_individual(
        self,
        statistics: dict,
        triggers: List[dict],
        transcript: str = None
    ) -> dict:
        """
        Analyze individual psychological state

        Args:
            statistics: Acoustic statistics
            triggers: Detected triggers
            transcript: Optional transcript

        Returns:
            dict: Analysis result
        """
        if not self.model:
            return self._fallback_individual_analysis(statistics, triggers)

        # Format prompt
        user_prompt = self._format_individual_prompt(statistics, triggers, transcript)

        try:
            response = self.model.generate_content(
                f"{INDIVIDUAL_SYSTEM_PROMPT}\n\n{user_prompt}"
            )

            # Parse response
            result = self._parse_json_response(response.text)
            if result:
                return result

        except Exception as e:
            frappe.log_error(f"Gemini analysis failed: {str(e)}")

        return self._fallback_individual_analysis(statistics, triggers)

    def analyze_meeting(
        self,
        statistics: dict,
        triggers: List[dict],
        speaker_stats: dict = None
    ) -> dict:
        """
        Analyze meeting psychological safety

        Args:
            statistics: Acoustic statistics
            triggers: Detected triggers
            speaker_stats: Speaker-level statistics

        Returns:
            dict: Analysis result
        """
        if not self.model:
            return self._fallback_meeting_analysis(statistics, triggers)

        # Format prompt
        user_prompt = self._format_meeting_prompt(statistics, triggers, speaker_stats)

        try:
            response = self.model.generate_content(
                f"{MEETING_SYSTEM_PROMPT}\n\n{user_prompt}"
            )

            # Parse response
            result = self._parse_json_response(response.text)
            if result:
                return result

        except Exception as e:
            frappe.log_error(f"Gemini meeting analysis failed: {str(e)}")

        return self._fallback_meeting_analysis(statistics, triggers)

    def _format_individual_prompt(
        self,
        statistics: dict,
        triggers: List[dict],
        transcript: str = None
    ) -> str:
        """Format prompt for individual analysis"""
        triggers_text = ""
        if triggers:
            triggers_text = "最近検出されたトリガー:\n" + "\n".join(
                f"- {t.get('type', 'unknown')}: {t.get('evidence', '')}"
                for t in triggers
            )

        return f"""【分析対象データ】

発話テキスト:
{transcript or '（音声認識データなし）'}

音響統計:
- 発話率: {statistics.get('speech_ratio', 0) * 100:.1f}%
- 平均沈黙長: {statistics.get('silence_mean_ms', 0):.0f}ms
- 最大沈黙長: {statistics.get('silence_max_ms', 0):.0f}ms
- 相対話速: {statistics.get('speech_rate_relative', 1.0):.2f}x
- フィラー率: {statistics.get('filler_rate', 0) * 100:.1f}%
- 音量変動: {statistics.get('rms_variance', 0):.4f}

{triggers_text}

上記のデータから話者の心理状態を分析してください。"""

    def _format_meeting_prompt(
        self,
        statistics: dict,
        triggers: List[dict],
        speaker_stats: dict = None
    ) -> str:
        """Format prompt for meeting analysis"""
        triggers_text = ""
        if triggers:
            triggers_text = "検出されたイベント:\n" + "\n".join(
                f"- {t.get('type', 'unknown')}: {t.get('evidence', '')}"
                for t in triggers
            )

        speaker_text = ""
        if speaker_stats:
            speaker_text = "話者統計:\n" + json.dumps(speaker_stats, ensure_ascii=False, indent=2)

        return f"""【会議分析データ】

音響統計:
- 発話率: {statistics.get('speech_ratio', 0) * 100:.1f}%
- 平均沈黙長: {statistics.get('silence_mean_ms', 0):.0f}ms
- 相対話速: {statistics.get('speech_rate_relative', 1.0):.2f}x
- 音量変動: {statistics.get('rms_variance', 0):.4f}

{triggers_text}

{speaker_text}

上記のデータから会議の心理的安全性を評価してください。"""

    def _parse_json_response(self, response_text: str) -> Optional[dict]:
        """Parse JSON from Gemini response"""
        try:
            # Try direct JSON parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _fallback_individual_analysis(self, statistics: dict, triggers: List[dict]) -> dict:
        """
        Fallback analysis when Gemini is not available
        Uses simple heuristics based on statistics
        """
        # Calculate metrics from statistics
        speech_ratio = statistics.get("speech_ratio", 0.5)
        silence_mean = statistics.get("silence_mean_ms", 500)
        filler_rate = statistics.get("filler_rate", 0.1)
        speech_rate = statistics.get("speech_rate_relative", 1.0)
        rms_variance = statistics.get("rms_variance", 0.01)

        # Stress: high silence + high variance
        stress = min(1.0, (silence_mean / 3000) * 0.5 + rms_variance * 5 * 0.5)

        # Anxiety: high filler rate + long silence
        anxiety = min(1.0, filler_rate * 5 * 0.6 + (silence_mean / 2000) * 0.4)

        # Cognitive load: speech rate deviation + fillers
        rate_deviation = abs(1.0 - speech_rate)
        cognitive = min(1.0, rate_deviation * 0.5 + filler_rate * 3 * 0.5)

        # Confidence: inverse of hedges (from triggers)
        hedge_triggers = [t for t in triggers if t.get("type") == "hedge_increase"]
        confidence = max(0.0, 1.0 - len(hedge_triggers) * 0.2 - filler_rate * 2)

        # Stability: low variance indicators
        stability = max(0.0, 1.0 - stress * 0.5 - anxiety * 0.3 - cognitive * 0.2)

        evidence = []
        if stress > 0.5:
            evidence.append(f"沈黙パターン（平均{silence_mean:.0f}ms）からストレスの可能性")
        if anxiety > 0.5:
            evidence.append(f"フィラー率{filler_rate * 100:.1f}%から不安の可能性")
        if cognitive > 0.5:
            evidence.append(f"話速変動（{speech_rate:.2f}x）から認知負荷の可能性")

        return {
            "stress_load": round(stress, 3),
            "anxiety_uncertainty": round(anxiety, 3),
            "cognitive_load": round(cognitive, 3),
            "confidence_assertiveness": round(confidence, 3),
            "stability": round(stability, 3),
            "confidence": 0.6,  # Lower confidence for heuristic analysis
            "evidence": evidence or ["統計データに基づく推定"],
            "suggestion": None
        }

    def _fallback_meeting_analysis(self, statistics: dict, triggers: List[dict]) -> dict:
        """
        Fallback meeting analysis when Gemini is not available
        """
        speech_ratio = statistics.get("speech_ratio", 0.5)
        silence_mean = statistics.get("silence_mean_ms", 500)

        # Simple heuristics
        speak_up = max(0.0, min(1.0, speech_ratio * 1.2))
        respect = max(0.0, 1.0 - len([t for t in triggers if t.get("type") == "interruption"]) * 0.2)
        error_tolerance = max(0.0, 1.0 - len([t for t in triggers if t.get("type") == "apology_phrase"]) * 0.15)
        power_balance = max(0.0, 1.0 - len([t for t in triggers if t.get("type") == "power_imbalance"]) * 0.3)

        overall = (speak_up + respect + error_tolerance + power_balance) / 4

        return {
            "speak_up": round(speak_up, 3),
            "respect_interaction": round(respect, 3),
            "error_tolerance": round(error_tolerance, 3),
            "power_balance": round(power_balance, 3),
            "overall_ps": round(overall, 3),
            "confidence": 0.5,
            "key_moments": [],
            "speaker_stats": {}
        }
