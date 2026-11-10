"""
Timbre TTS Client module re-export.
"""

from tts.tts_client import KNOWN_VOICES, TimbreTTSClient, VoiceConfig, quick_synthesize

__all__ = ["KNOWN_VOICES", "TimbreTTSClient", "VoiceConfig", "quick_synthesize"]
