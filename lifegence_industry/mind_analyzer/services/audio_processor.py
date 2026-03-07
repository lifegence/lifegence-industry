# Copyright (c) 2025 Lifegence
# For license information, please see license.txt

"""
Audio Processor Service
Processes audio data and calculates acoustic statistics
"""

import io
import math
from typing import Optional

import numpy as np

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


class AudioProcessor:
    """
    Audio processing and statistics calculation.
    Ported from voice-analizer TypeScript implementation.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.ewma_alpha = self.config.get("ewma_alpha", 0.1)
        self.window_duration_ms = self.config.get("window_duration_ms", 5000)
        self.baseline_speech_rate = self.config.get("baseline_speech_rate", 6.0)

        # Statistics state
        self.statistics = self._create_initial_statistics()

        # Internal tracking
        self.speech_samples = 0
        self.total_samples = 0
        self.silence_start_time = None
        self.silence_durations = []
        self.last_speech_time = 0
        self.filler_count = 0
        self.total_utterances = 0
        self.character_count = 0
        self.speech_duration_ms = 0

    def _create_initial_statistics(self) -> dict:
        """Create initial statistics dict"""
        return {
            "speech_ratio": 0.0,
            "silence_mean_ms": 0.0,
            "silence_max_ms": 0.0,
            "speech_rate_relative": 1.0,
            "rms_level": 0.0,
            "rms_variance": 0.0,
            "filler_rate": 0.0,
        }

    def process_audio(self, audio_bytes: bytes, format: str = "webm") -> dict:
        """
        Process audio data and return statistics

        Args:
            audio_bytes: Raw audio data
            format: Audio format (webm, wav, pcm16)

        Returns:
            dict: Acoustic statistics
        """
        # Convert audio to samples
        samples = self._convert_to_samples(audio_bytes, format)

        if samples is None or len(samples) == 0:
            return self.statistics

        # Calculate RMS
        rms = self._calculate_rms(samples)
        self._update_rms(rms)

        # Simple energy-based VAD
        vad_results = self._energy_vad(samples)
        for is_speech in vad_results:
            self._update_with_vad(is_speech)

        return self.get_statistics()

    def _convert_to_samples(self, audio_bytes: bytes, format: str) -> Optional[np.ndarray]:
        """Convert audio bytes to float samples"""
        if not PYDUB_AVAILABLE:
            # Fallback: assume PCM16 mono 16kHz
            if format == "pcm16":
                samples = np.frombuffer(audio_bytes, dtype=np.int16)
                return samples.astype(np.float32) / 32768.0
            return None

        try:
            # Use pydub for format conversion
            if format == "webm":
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")
            elif format == "wav":
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
            elif format == "pcm16":
                audio = AudioSegment.from_raw(
                    io.BytesIO(audio_bytes),
                    sample_width=2,
                    frame_rate=16000,
                    channels=1
                )
            else:
                # Try auto-detection
                audio = AudioSegment.from_file(io.BytesIO(audio_bytes))

            # Convert to mono and get samples
            audio = audio.set_channels(1)
            samples = np.array(audio.get_array_of_samples())
            return samples.astype(np.float32) / 32768.0

        except Exception:
            return None

    def _calculate_rms(self, samples: np.ndarray) -> float:
        """Calculate RMS (Root Mean Square) of samples"""
        if len(samples) == 0:
            return 0.0
        return float(np.sqrt(np.mean(samples ** 2)))

    def _energy_vad(self, samples: np.ndarray, frame_size: int = 480) -> list:
        """
        Simple energy-based Voice Activity Detection

        Args:
            samples: Audio samples
            frame_size: Frame size in samples (30ms at 16kHz)

        Returns:
            list: List of boolean VAD results per frame
        """
        threshold = 0.01  # Energy threshold

        results = []
        for i in range(0, len(samples), frame_size):
            frame = samples[i:i + frame_size]
            if len(frame) < frame_size // 2:
                continue

            energy = np.mean(frame ** 2)
            is_speech = energy > threshold
            results.append(is_speech)

        return results

    def _update_with_vad(self, is_speech: bool):
        """Update statistics with VAD result"""
        import time
        current_time = int(time.time() * 1000)

        if is_speech:
            if self.silence_start_time is not None:
                silence_duration = current_time - self.silence_start_time
                self.silence_durations.append(silence_duration)
                self._prune_old_data(current_time)
                self.silence_start_time = None

            self.speech_samples += 1
            self.last_speech_time = current_time
        else:
            if self.silence_start_time is None and self.last_speech_time > 0:
                self.silence_start_time = current_time

        self.total_samples += 1
        self._update_speech_ratio()
        self._update_silence_metrics()

    def _update_rms(self, rms: float):
        """Update RMS statistics using EWMA"""
        # EWMA update for RMS level
        self.statistics["rms_level"] = self._ewma_update(
            self.statistics["rms_level"],
            rms
        )

        # Track variance
        prev_variance = self.statistics["rms_variance"]
        delta = rms - self.statistics["rms_level"]
        self.statistics["rms_variance"] = self._ewma_update(
            prev_variance,
            delta * delta
        )

    def _update_speech_ratio(self):
        """Update speech ratio statistic"""
        if self.total_samples > 0:
            new_ratio = self.speech_samples / self.total_samples
            self.statistics["speech_ratio"] = self._ewma_update(
                self.statistics["speech_ratio"],
                new_ratio
            )

    def _update_silence_metrics(self):
        """Update silence-related metrics"""
        if not self.silence_durations:
            return

        # Calculate mean silence
        mean_silence = sum(self.silence_durations) / len(self.silence_durations)
        self.statistics["silence_mean_ms"] = self._ewma_update(
            self.statistics["silence_mean_ms"],
            mean_silence
        )

        # Update max silence with decay
        max_silence = max(self.silence_durations)
        self.statistics["silence_max_ms"] = max(
            self.statistics["silence_max_ms"] * 0.95,
            max_silence
        )

    def _ewma_update(self, old_value: float, new_value: float) -> float:
        """Exponentially Weighted Moving Average update"""
        return self.ewma_alpha * new_value + (1 - self.ewma_alpha) * old_value

    def _prune_old_data(self, current_time: int):
        """Prune old data outside the window"""
        if len(self.silence_durations) > 10:
            self.silence_durations = self.silence_durations[-10:]

        # Periodic reset
        self.speech_samples = int(self.speech_samples * 0.9)
        self.total_samples = int(self.total_samples * 0.9)

    def update_with_transcript(self, transcript: str, duration_ms: int):
        """
        Update statistics with transcript data

        Args:
            transcript: Transcribed text
            duration_ms: Duration of the transcript
        """
        import re

        # Japanese filler patterns
        filler_pattern = r'[えー|あー|えーと|あのー|えっと|まあ]'
        fillers = re.findall(filler_pattern, transcript)

        self.filler_count += len(fillers)
        self.total_utterances += 1

        if self.total_utterances > 0:
            self.statistics["filler_rate"] = self.filler_count / self.total_utterances

        # Update speech rate
        clean_transcript = re.sub(filler_pattern, '', transcript)
        self.character_count += len(clean_transcript)
        self.speech_duration_ms += duration_ms

        if self.speech_duration_ms > 0:
            actual_rate = (self.character_count / self.speech_duration_ms) * 1000
            self.statistics["speech_rate_relative"] = actual_rate / self.baseline_speech_rate

    def get_statistics(self) -> dict:
        """Get current statistics"""
        return {
            "speech_ratio": round(self.statistics["speech_ratio"], 4),
            "silence_mean_ms": round(self.statistics["silence_mean_ms"], 2),
            "silence_max_ms": round(self.statistics["silence_max_ms"], 2),
            "speech_rate_relative": round(self.statistics["speech_rate_relative"], 3),
            "rms_level": round(self.statistics["rms_level"], 6),
            "rms_variance": round(self.statistics["rms_variance"], 6),
            "filler_rate": round(self.statistics["filler_rate"], 4),
        }

    def reset(self):
        """Reset all statistics"""
        self.statistics = self._create_initial_statistics()
        self.speech_samples = 0
        self.total_samples = 0
        self.silence_start_time = None
        self.silence_durations = []
        self.last_speech_time = 0
        self.filler_count = 0
        self.total_utterances = 0
        self.character_count = 0
        self.speech_duration_ms = 0
