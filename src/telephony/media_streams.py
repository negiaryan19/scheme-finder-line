"""
Twilio Media Streams Integration

Modular integration layer for bidirectional audio streaming with Twilio Media Streams.
Handles μ-law 8kHz ↔ PCM 16kHz conversion and message framing.

⚠️  UNVERIFIED ASSUMPTIONS (require Twilio console testing):
- Media Stream WebSocket message format
- Audio payload encoding (base64 μ-law)
- Track labels and streamSid handling
- DTMF and mark event handling
- Custom parameter passing via <Start><Stream>
"""

from __future__ import annotations

import base64
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from utils.audio import (
    convert_stt_to_twilio_format,
    convert_twilio_to_stt_format,
)
from utils.exceptions import AudioProcessingError
from utils.logging import get_logger

logger = get_logger(__name__)


class MediaStreamMessageType(Enum):
    """Twilio Media Stream message types (from Twilio docs)."""

    CONNECTED = "connected"
    START = "start"
    MEDIA = "media"
    MARK = "mark"
    DTMF = "dtmf"
    STOP = "stop"


@dataclass
class MediaStreamConfig:
    """Configuration for Media Stream connection."""

    # Audio format (Twilio always sends μ-law 8kHz)
    input_encoding: str = "audio/x-mulaw"
    input_sample_rate: int = 8000
    input_channels: int = 1

    # Output format for TTS → Twilio
    output_encoding: str = "audio/x-mulaw"
    output_sample_rate: int = 8000
    output_channels: int = 1

    # Chunk size for streaming (20ms frames at 8kHz = 160 samples = 320 bytes μ-law)
    chunk_duration_ms: int = 20

    # STT target format (Prisma expects 16kHz PCM)
    stt_sample_rate: int = 16000


@dataclass
class MediaStreamState:
    """Runtime state for a Media Stream connection."""

    stream_sid: str | None = None
    call_sid: str | None = None
    tracks: dict[str, str] = field(default_factory=dict)  # track_name → track_sid
    custom_parameters: dict[str, str] = field(default_factory=dict)
    is_active: bool = False
    sequence_number: int = 0


class MediaStreamHandler:
    """
    Handles bidirectional Twilio Media Stream WebSocket communication.

    Provides:
    - Automatic μ-law 8kHz ↔ PCM 16kHz conversion
    - Message parsing and framing
    - Async iterators for incoming audio (STT-ready) and outgoing audio (Twilio-ready)
    - Event handlers for DTMF, marks, etc.
    """

    def __init__(
        self,
        config: MediaStreamConfig | None = None,
        on_dtmf: Callable[[str, str], Any] | None = None,  # (digit, track_sid)
        on_mark: Callable[[str, str], Any] | None = None,  # (name, track_sid)
        on_stop: Callable[[], Any] | None = None,
    ):
        self.config = config or MediaStreamConfig()
        self.state = MediaStreamState()
        self._on_dtmf = on_dtmf
        self._on_mark = on_mark
        self._on_stop = on_stop

        # Queues for bidirectional audio flow
        self._incoming_audio: asyncio.Queue[bytes] = asyncio.Queue()
        self._outgoing_audio: asyncio.Queue[bytes] = asyncio.Queue()
        self._control_messages: asyncio.Queue[dict] = asyncio.Queue()

        # WebSocket reference (set by connect())
        self._ws: Any = None

    async def connect(self, websocket: Any) -> None:
        """Initialize handler with WebSocket connection."""
        self._ws = websocket

    async def handle_message(self, message: str | bytes) -> None:
        """
        Process incoming WebSocket message from Twilio.

        Parses message and routes to appropriate handler.
        """
        if isinstance(message, bytes):
            # Binary frames not expected from Twilio Media Streams
            logger.warning("Received binary WebSocket frame, ignoring")
            return

        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Media Stream message", error=str(e))
            return

        msg_type = data.get("event")
        if not msg_type:
            logger.warning("Media Stream message missing 'event' field", data=data)
            return

        try:
            if msg_type == MediaStreamMessageType.CONNECTED.value:
                await self._handle_connected(data)
            elif msg_type == MediaStreamMessageType.START.value:
                await self._handle_start(data)
            elif msg_type == MediaStreamMessageType.MEDIA.value:
                await self._handle_media(data)
            elif msg_type == MediaStreamMessageType.MARK.value:
                await self._handle_mark(data)
            elif msg_type == MediaStreamMessageType.DTMF.value:
                await self._handle_dtmf(data)
            elif msg_type == MediaStreamMessageType.STOP.value:
                await self._handle_stop(data)
            else:
                logger.warning("Unknown Media Stream event type", event_type=msg_type)
        except Exception as e:
            logger.error(
                "Error handling Media Stream message",
                event_type=msg_type,
                error=str(e),
                exc_info=True,
            )

    async def _handle_connected(self, data: dict) -> None:
        """Handle 'connected' event — connection established."""
        logger.info("Media Stream connected", protocol=data.get("protocol"), version=data.get("version"))

    async def _handle_start(self, data: dict) -> None:
        """Handle 'start' event — stream beginning with metadata."""
        start_data = data.get("start", {})
        self.state.stream_sid = start_data.get("streamSid")
        self.state.call_sid = start_data.get("callSid")
        self.state.tracks = start_data.get("tracks", {})
        self.state.custom_parameters = start_data.get("customParameters", {})
        self.state.is_active = True
        self.state.sequence_number = 0

        logger.info(
            "Media Stream started",
            stream_sid=self.state.stream_sid,
            call_sid=self.state.call_sid,
            tracks=list(self.state.tracks.keys()),
            custom_params=list(self.state.custom_parameters.keys()),
        )

    async def _handle_media(self, data: dict) -> None:
        """Handle 'media' event — audio payload from Twilio."""
        media = data.get("media", {})
        payload_b64 = media.get("payload")
        track_sid = media.get("trackSid")

        if not payload_b64:
            return

        # Decode base64 μ-law payload
        try:
            mulaw_bytes = base64.b64decode(payload_b64)
        except Exception as e:
            raise AudioProcessingError(f"Failed to decode base64 audio payload: {e}") from e

        # Convert μ-law 8kHz → PCM 16kHz for STT
        try:
            pcm_16khz = convert_twilio_to_stt_format(mulaw_bytes)
        except Exception as e:
            raise AudioProcessingError(f"Audio format conversion failed: {e}") from e

        # Queue for STT consumer
        await self._incoming_audio.put(pcm_16khz)

        self.state.sequence_number += 1

    async def _handle_mark(self, data: dict) -> None:
        """Handle 'mark' event — marker reached in playback."""
        mark = data.get("mark", {})
        name = mark.get("name")
        track_sid = mark.get("trackSid")

        logger.debug("Media Stream mark received", name=name, track_sid=track_sid)

        if self._on_mark and name:
            await self._on_mark(name, track_sid or "")

    async def _handle_dtmf(self, data: dict) -> None:
        """Handle 'dtmf' event — DTMF digit pressed."""
        dtmf = data.get("dtmf", {})
        digit = dtmf.get("digit")
        track_sid = dtmf.get("trackSid")

        logger.info("DTMF received", digit=digit, track_sid=track_sid)

        if self._on_dtmf and digit:
            await self._on_dtmf(digit, track_sid or "")

    async def _handle_stop(self, data: dict) -> None:
        """Handle 'stop' event — stream ending."""
        logger.info("Media Stream stopped", stream_sid=self.state.stream_sid)
        self.state.is_active = False

        if self._on_stop:
            await self._on_stop()

        # Signal end of audio streams
        await self._incoming_audio.put(b"")  # Sentinel
        await self._outgoing_audio.put(b"")  # Sentinel

    # ==================== OUTGOING AUDIO (TTS → Twilio) ====================

    async def send_audio(self, pcm_16khz_bytes: bytes) -> None:
        """
        Send PCM 16kHz audio to Twilio (converts to μ-law 8kHz).

        Args:
            pcm_16khz_bytes: 16-bit PCM audio at 16kHz mono
        """
        if not self.state.is_active:
            logger.warning("Attempted to send audio on inactive stream")
            return

        # Convert PCM 16kHz → μ-law 8kHz for Twilio
        try:
            mulaw_bytes = convert_stt_to_twilio_format(pcm_16khz_bytes)
        except Exception as e:
            raise AudioProcessingError(f"Audio format conversion failed: {e}") from e

        # Encode as base64
        payload_b64 = base64.b64encode(mulaw_bytes).decode("ascii")

        # Build media message
        message = {
            "event": "media",
            "streamSid": self.state.stream_sid,
            "media": {
                "payload": payload_b64,
            },
        }

        await self._ws.send_text(json.dumps(message))

    async def send_mark(self, name: str) -> None:
        """Send a mark event to Twilio for playback synchronization."""
        message = {
            "event": "mark",
            "streamSid": self.state.stream_sid,
            "mark": {"name": name},
        }
        await self._ws.send_text(json.dumps(message))

    async def send_clear(self) -> None:
        """Send clear event to stop current audio playback."""
        message = {
            "event": "clear",
            "streamSid": self.state.stream_sid,
        }
        await self._ws.send_text(json.dumps(message))

    # ==================== ASYNC ITERATORS FOR CONSUMERS ====================

    async def incoming_audio_iterator(self) -> AsyncIterator[bytes]:
        """
        Async iterator yielding STT-ready PCM 16kHz audio chunks.

        Yields empty bytes as sentinel when stream ends.
        """
        while True:
            chunk = await self._incoming_audio.get()
            if not chunk:  # Sentinel
                break
            yield chunk

    def outgoing_audio_iterator(self) -> AsyncIterator[bytes]:
        """
        Async iterator for TTS to push PCM 16kHz audio chunks.

        This is a helper — typically TTS would call send_audio() directly.
        """
        async def _gen():
            while True:
                chunk = await self._outgoing_audio.get()
                if not chunk:  # Sentinel
                    break
                await self.send_audio(chunk)
                yield chunk
        return _gen()

    # ==================== UTILITY ====================

    def get_stream_info(self) -> dict[str, Any]:
        """Get current stream metadata."""
        return {
            "stream_sid": self.state.stream_sid,
            "call_sid": self.state.call_sid,
            "tracks": dict(self.state.tracks),
            "custom_parameters": dict(self.state.custom_parameters),
            "is_active": self.state.is_active,
            "sequence_number": self.state.sequence_number,
        }


# ==================== TWIML GENERATION ====================


def generate_media_stream_twiml(
    websocket_url: str,
    *,
    name: str = "scheme-finder-stream",
    track: str = "inbound_track",
    custom_parameters: dict[str, str] | None = None,
) -> str:
    """
    Generate TwiML for starting a Media Stream.

    Args:
        websocket_url: WSS URL for Media Stream (e.g., wss://example.com/media-stream)
        name: Stream name
        track: Track to stream (inbound_track, outbound_track, both_tracks)
        custom_parameters: Optional custom parameters passed to WebSocket

    Returns:
        TwiML XML string
    """
    params_xml = ""
    if custom_parameters:
        for key, value in custom_parameters.items():
            params_xml += f'        <Parameter name="{key}" value="{value}" />\n'

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Start>
        <Stream name="{name}" url="{websocket_url}" track="{track}">
{params_xml}        </Stream>
    </Start>
    <Say voice="Polly.Aditi" language="hi-IN">
        नमस्ते! मैं सरकारी योजनाओं की जानकारी के लिए आपकी सहायता कर सकता हूँ।
        कृपया बताएं आप किस योजना के बारे में जानना चाहते हैं।
    </Say>
    <Pause length="60"/>
</Response>"""
    return twiml


# Import asyncio at module level for queue usage
import asyncio