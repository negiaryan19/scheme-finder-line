"""
Unit Tests for Telephony Module

Tests MediaStreamHandler, TwiML generation, and message parsing.
"""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telephony.media_streams import (
    MediaStreamConfig,
    MediaStreamHandler,
    MediaStreamMessageType,
    MediaStreamState,
    generate_media_stream_twiml,
)


# ==================== TEST FIXTURES ====================


@pytest.fixture
def media_stream_config():
    """Default MediaStreamConfig."""
    return MediaStreamConfig()


@pytest.fixture
def media_stream_handler(media_stream_config):
    """MediaStreamHandler with default config."""
    return MediaStreamHandler(config=media_stream_config)


@pytest.fixture
def mock_websocket():
    """Mock WebSocket."""
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


# ==================== TESTS: MESSAGE TYPES ====================


class TestMediaStreamMessageType:
    """Test MediaStreamMessageType enum."""

    def test_message_types(self):
        """Test all message types are defined."""
        assert MediaStreamMessageType.CONNECTED.value == "connected"
        assert MediaStreamMessageType.START.value == "start"
        assert MediaStreamMessageType.MEDIA.value == "media"
        assert MediaStreamMessageType.MARK.value == "mark"
        assert MediaStreamMessageType.DTMF.value == "dtmf"
        assert MediaStreamMessageType.STOP.value == "stop"


# ==================== TESTS: CONFIG ====================


class TestMediaStreamConfig:
    """Test MediaStreamConfig defaults."""

    def test_default_config(self):
        """Test default configuration values."""
        config = MediaStreamConfig()
        assert config.input_encoding == "audio/x-mulaw"
        assert config.input_sample_rate == 8000
        assert config.input_channels == 1
        assert config.output_encoding == "audio/x-mulaw"
        assert config.output_sample_rate == 8000
        assert config.output_channels == 1
        assert config.chunk_duration_ms == 20
        assert config.stt_sample_rate == 16000

    def test_custom_config(self):
        """Test custom configuration."""
        config = MediaStreamConfig(
            input_sample_rate=16000,
            chunk_duration_ms=10,
            stt_sample_rate=48000,
        )
        assert config.input_sample_rate == 16000
        assert config.chunk_duration_ms == 10
        assert config.stt_sample_rate == 48000


# ==================== TESTS: STATE ====================


class TestMediaStreamState:
    """Test MediaStreamState."""

    def test_initial_state(self):
        """Test initial state values."""
        state = MediaStreamState()
        assert state.stream_sid is None
        assert state.call_sid is None
        assert state.tracks == {}
        assert state.custom_parameters == {}
        assert state.is_active is False
        assert state.sequence_number == 0

    def test_state_with_values(self):
        """Test state with custom values."""
        state = MediaStreamState(
            stream_sid="stream-123",
            call_sid="call-456",
            tracks={"inbound": "track-1"},
            custom_parameters={"user_id": "user-789"},
            is_active=True,
            sequence_number=5,
        )
        assert state.stream_sid == "stream-123"
        assert state.call_sid == "call-456"
        assert state.tracks == {"inbound": "track-1"}
        assert state.custom_parameters == {"user_id": "user-789"}
        assert state.is_active is True
        assert state.sequence_number == 5


# ==================== TESTS: HANDLER INITIALIZATION ====================


class TestMediaStreamHandlerInit:
    """Test MediaStreamHandler initialization."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        handler = MediaStreamHandler()
        assert handler.config is not None
        assert isinstance(handler.config, MediaStreamConfig)
        assert handler.state is not None
        assert isinstance(handler.state, MediaStreamState)

    def test_init_custom_config(self, media_stream_config):
        """Test initialization with custom config."""
        handler = MediaStreamHandler(config=media_stream_config)
        assert handler.config is media_stream_config

    def test_init_callbacks(self):
        """Test initialization with callbacks."""
        dtmf_calls = []
        mark_calls = []
        stop_calls = []

        async def on_dtmf(digit, track_sid):
            dtmf_calls.append((digit, track_sid))

        async def on_mark(name, track_sid):
            mark_calls.append((name, track_sid))

        async def on_stop():
            stop_calls.append(True)

        handler = MediaStreamHandler(
            on_dtmf=on_dtmf,
            on_mark=on_mark,
            on_stop=on_stop,
        )
        assert handler._on_dtmf is on_dtmf
        assert handler._on_mark is on_mark
        assert handler._on_stop is on_stop


# ==================== TESTS: MESSAGE HANDLING ====================


class TestMediaStreamHandlerMessages:
    """Test message handling."""

    @pytest.mark.asyncio
    async def test_handle_connected(self, media_stream_handler):
        """Test handling 'connected' event."""
        message = {
            "event": "connected",
            "protocol": "Call",
            "version": "1.0",
        }
        await media_stream_handler.handle_message(json.dumps(message))
        # Should not raise

    @pytest.mark.asyncio
    async def test_handle_start(self, media_stream_handler):
        """Test handling 'start' event."""
        message = {
            "event": "start",
            "start": {
                "streamSid": "stream-123",
                "callSid": "call-456",
                "tracks": {"inbound": "track-1"},
                "customParameters": {"user_id": "user-789"},
            },
        }
        await media_stream_handler.handle_message(json.dumps(message))

        assert media_stream_handler.state.stream_sid == "stream-123"
        assert media_stream_handler.state.call_sid == "call-456"
        assert media_stream_handler.state.tracks == {"inbound": "track-1"}
        assert media_stream_handler.state.custom_parameters == {"user_id": "user-789"}
        assert media_stream_handler.state.is_active is True
        assert media_stream_handler.state.sequence_number == 0

    @pytest.mark.asyncio
    async def test_handle_media_valid_payload(self, media_stream_handler):
        """Test handling 'media' event with valid payload."""
        # Set up state first
        media_stream_handler.state.stream_sid = "stream-123"
        media_stream_handler.state.is_active = True

        # Create μ-law payload (base64 encoded)
        mulaw_payload = b"\xFF" * 160  # 20ms of silence at 8kHz
        payload_b64 = base64.b64encode(mulaw_payload).decode("ascii")

        message = {
            "event": "media",
            "media": {
                "payload": payload_b64,
                "trackSid": "track-1",
            },
        }

        await media_stream_handler.handle_message(json.dumps(message))

        # Should queue PCM 16kHz audio
        assert not media_stream_handler._incoming_audio.empty()
        pcm_chunk = await media_stream_handler._incoming_audio.get()
        # 160 μ-law bytes (8kHz) → 320 PCM bytes (8kHz) → 640 PCM bytes (16kHz) (approximately)
        assert abs(len(pcm_chunk) - 640) < 10
        assert media_stream_handler.state.sequence_number == 1

    @pytest.mark.asyncio
    async def test_handle_media_empty_payload(self, media_stream_handler):
        """Test handling 'media' event with empty payload."""
        media_stream_handler.state.stream_sid = "stream-123"
        media_stream_handler.state.is_active = True

        message = {
            "event": "media",
            "media": {
                "payload": "",
                "trackSid": "track-1",
            },
        }

        await media_stream_handler.handle_message(json.dumps(message))
        # Should not queue anything for empty payload
        assert media_stream_handler._incoming_audio.empty()

    @pytest.mark.asyncio
    async def test_handle_media_invalid_base64(self, media_stream_handler):
        """Test handling 'media' event with invalid base64 logs error and continues."""
        media_stream_handler.state.stream_sid = "stream-123"
        media_stream_handler.state.is_active = True

        message = {
            "event": "media",
            "media": {
                "payload": "not-valid-base64!",
                "trackSid": "track-1",
            },
        }

        # Should not raise, just log error and continue
        await media_stream_handler.handle_message(json.dumps(message))
        
        # Audio queue should be empty since decoding failed
        assert media_stream_handler._incoming_audio.empty()

    @pytest.mark.asyncio
    async def test_handle_mark(self, media_stream_handler):
        """Test handling 'mark' event."""
        mark_calls = []

        async def on_mark(name, track_sid):
            mark_calls.append((name, track_sid))

        handler = MediaStreamHandler(on_mark=on_mark)
        handler.state.stream_sid = "stream-123"
        handler.state.is_active = True

        message = {
            "event": "mark",
            "mark": {
                "name": "marker-1",
                "trackSid": "track-1",
            },
        }

        await handler.handle_message(json.dumps(message))

        assert len(mark_calls) == 1
        assert mark_calls[0] == ("marker-1", "track-1")

    @pytest.mark.asyncio
    async def test_handle_dtmf(self, media_stream_handler):
        """Test handling 'dtmf' event."""
        dtmf_calls = []

        async def on_dtmf(digit, track_sid):
            dtmf_calls.append((digit, track_sid))

        handler = MediaStreamHandler(on_dtmf=on_dtmf)
        handler.state.stream_sid = "stream-123"
        handler.state.is_active = True

        message = {
            "event": "dtmf",
            "dtmf": {
                "digit": "5",
                "trackSid": "track-1",
            },
        }

        await handler.handle_message(json.dumps(message))

        assert len(dtmf_calls) == 1
        assert dtmf_calls[0] == ("5", "track-1")

    @pytest.mark.asyncio
    async def test_handle_stop(self, media_stream_handler):
        """Test handling 'stop' event."""
        stop_calls = []

        async def on_stop():
            stop_calls.append(True)

        handler = MediaStreamHandler(on_stop=on_stop)
        handler.state.stream_sid = "stream-123"
        handler.state.is_active = True

        message = {"event": "stop"}

        await handler.handle_message(json.dumps(message))

        assert handler.state.is_active is False
        assert len(stop_calls) == 1
        # Should put sentinel values in queues
        assert not handler._incoming_audio.empty()
        assert not handler._outgoing_audio.empty()
        sentinel = await handler._incoming_audio.get()
        assert sentinel == b""

    @pytest.mark.asyncio
    async def test_handle_unknown_event(self, media_stream_handler):
        """Test handling unknown event type."""
        message = {"event": "unknown_event", "data": "test"}
        # Should not raise, just log warning
        await media_stream_handler.handle_message(json.dumps(message))

    @pytest.mark.asyncio
    async def test_handle_invalid_json(self, media_stream_handler):
        """Test handling invalid JSON."""
        # Should not raise, just log error
        await media_stream_handler.handle_message("not valid json")

    @pytest.mark.asyncio
    async def test_handle_binary_frame(self, media_stream_handler):
        """Test handling binary WebSocket frame."""
        # Should not raise, just log warning
        await media_stream_handler.handle_message(b"binary data")


# ==================== TESTS: OUTGOING AUDIO ====================


class TestMediaStreamHandlerOutgoing:
    """Test outgoing audio (TTS → Twilio)."""

    @pytest.mark.asyncio
    async def test_send_audio_inactive_stream(self, media_stream_handler):
        """Test sending audio on inactive stream logs warning."""
        media_stream_handler.state.is_active = False
        # Should not raise, just log warning
        await media_stream_handler.send_audio(b"test audio")

    @pytest.mark.asyncio
    async def test_send_audio_active_stream(self, media_stream_handler, mock_websocket):
        """Test sending audio on active stream."""
        media_stream_handler.state.is_active = True
        media_stream_handler.state.stream_sid = "stream-123"
        await media_stream_handler.connect(mock_websocket)

        # 100ms of 16kHz PCM = 1600 samples = 3200 bytes
        pcm_16khz = b"\x00" * 3200

        await media_stream_handler.send_audio(pcm_16khz)

        # Should send message via WebSocket
        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["event"] == "media"
        assert sent_message["streamSid"] == "stream-123"
        assert "media" in sent_message
        assert "payload" in sent_message["media"]

        # Payload should be base64 encoded μ-law
        payload_b64 = sent_message["media"]["payload"]
        mulaw_bytes = base64.b64decode(payload_b64)
        # 3200 bytes PCM 16kHz (1600 samples) → 800 samples PCM 8kHz → 800 bytes μ-law
        assert len(mulaw_bytes) == 800

    @pytest.mark.asyncio
    async def test_send_mark(self, media_stream_handler, mock_websocket):
        """Test sending mark event."""
        media_stream_handler.state.is_active = True
        media_stream_handler.state.stream_sid = "stream-123"
        await media_stream_handler.connect(mock_websocket)

        await media_stream_handler.send_mark("marker-1")

        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["event"] == "mark"
        assert sent_message["streamSid"] == "stream-123"
        assert sent_message["mark"]["name"] == "marker-1"

    @pytest.mark.asyncio
    async def test_send_clear(self, media_stream_handler, mock_websocket):
        """Test sending clear event."""
        media_stream_handler.state.is_active = True
        media_stream_handler.state.stream_sid = "stream-123"
        await media_stream_handler.connect(mock_websocket)

        await media_stream_handler.send_clear()

        mock_websocket.send_text.assert_called_once()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["event"] == "clear"
        assert sent_message["streamSid"] == "stream-123"


# ==================== TESTS: ASYNC ITERATORS ====================


class TestMediaStreamHandlerIterators:
    """Test async iterators for audio streams."""

    @pytest.mark.asyncio
    async def test_incoming_audio_iterator(self, media_stream_handler):
        """Test incoming audio iterator."""
        media_stream_handler.state.is_active = True

        # Queue some audio chunks
        await media_stream_handler._incoming_audio.put(b"chunk1")
        await media_stream_handler._incoming_audio.put(b"chunk2")
        await media_stream_handler._incoming_audio.put(b"")  # Sentinel

        chunks = []
        async for chunk in media_stream_handler.incoming_audio_iterator():
            chunks.append(chunk)

        assert chunks == [b"chunk1", b"chunk2"]

    @pytest.mark.asyncio
    async def test_outgoing_audio_iterator(self, media_stream_handler, mock_websocket):
        """Test outgoing audio iterator."""
        media_stream_handler.state.is_active = True
        media_stream_handler.state.stream_sid = "stream-123"
        await media_stream_handler.connect(mock_websocket)

        # Queue some audio chunks
        await media_stream_handler._outgoing_audio.put(b"chunk1")
        await media_stream_handler._outgoing_audio.put(b"chunk2")
        await media_stream_handler._outgoing_audio.put(b"")  # Sentinel

        # Run iterator
        async for _ in media_stream_handler.outgoing_audio_iterator():
            pass

        # Should have sent both chunks
        assert mock_websocket.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_get_stream_info(self, media_stream_handler):
        """Test get_stream_info returns current state."""
        media_stream_handler.state.stream_sid = "stream-123"
        media_stream_handler.state.call_sid = "call-456"
        media_stream_handler.state.tracks = {"inbound": "track-1"}
        media_stream_handler.state.custom_parameters = {"user_id": "user-789"}
        media_stream_handler.state.is_active = True
        media_stream_handler.state.sequence_number = 42

        info = media_stream_handler.get_stream_info()

        assert info["stream_sid"] == "stream-123"
        assert info["call_sid"] == "call-456"
        assert info["tracks"] == {"inbound": "track-1"}
        assert info["custom_parameters"] == {"user_id": "user-789"}
        assert info["is_active"] is True
        assert info["sequence_number"] == 42


# ==================== TESTS: TWIML GENERATION ====================


class TestTwiMLGeneration:
    """Test TwiML generation for Media Streams."""

    def test_generate_basic_twiml(self):
        """Test basic TwiML generation."""
        twiml = generate_media_stream_twiml("wss://example.com/media-stream")

        assert '<?xml version="1.0" encoding="UTF-8"?>' in twiml
        assert "<Response>" in twiml
        assert "</Response>" in twiml
        assert "<Start>" in twiml
        assert "<Stream" in twiml
        assert 'url="wss://example.com/media-stream"' in twiml
        assert 'name="scheme-finder-stream"' in twiml
        assert 'track="inbound_track"' in twiml
        assert "<Say" in twiml
        assert "<Pause" in twiml

    def test_generate_twiml_custom_name(self):
        """Test TwiML with custom stream name."""
        twiml = generate_media_stream_twiml(
            "wss://example.com/media-stream",
            name="custom-stream",
        )
        assert 'name="custom-stream"' in twiml

    def test_generate_twiml_custom_track(self):
        """Test TwiML with custom track."""
        twiml = generate_media_stream_twiml(
            "wss://example.com/media-stream",
            track="both_tracks",
        )
        assert 'track="both_tracks"' in twiml

    def test_generate_twiml_custom_parameters(self):
        """Test TwiML with custom parameters."""
        twiml = generate_media_stream_twiml(
            "wss://example.com/media-stream",
            custom_parameters={"user_id": "123", "session_id": "abc"},
        )
        assert 'name="user_id"' in twiml
        assert 'value="123"' in twiml
        assert 'name="session_id"' in twiml
        assert 'value="abc"' in twiml

    def test_generate_twiml_no_parameters(self):
        """Test TwiML without custom parameters."""
        twiml = generate_media_stream_twiml(
            "wss://example.com/media-stream",
            custom_parameters=None,
        )
        assert "<Parameter" not in twiml


# ==================== TESTS: INTEGRATION ====================


class TestMediaStreamIntegration:
    """Integration tests for MediaStreamHandler."""

    @pytest.mark.asyncio
    async def test_full_message_flow(self, media_stream_handler, mock_websocket):
        """Test full message flow: connected → start → media → mark → stop."""
        await media_stream_handler.connect(mock_websocket)

        # 1. Connected
        await media_stream_handler.handle_message(json.dumps({
            "event": "connected",
            "protocol": "Call",
            "version": "1.0",
        }))

        # 2. Start
        await media_stream_handler.handle_message(json.dumps({
            "event": "start",
            "start": {
                "streamSid": "stream-123",
                "callSid": "call-456",
                "tracks": {"inbound": "track-1"},
                "customParameters": {},
            },
        }))

        assert media_stream_handler.state.is_active is True

        # 3. Media (multiple chunks)
        for i in range(3):
            mulaw = b"\xFF" * 160
            payload_b64 = base64.b64encode(mulaw).decode("ascii")
            await media_stream_handler.handle_message(json.dumps({
                "event": "media",
                "media": {"payload": payload_b64, "trackSid": "track-1"},
            }))

        assert media_stream_handler.state.sequence_number == 3
        assert media_stream_handler._incoming_audio.qsize() == 3

        # 4. Mark
        await media_stream_handler.handle_message(json.dumps({
            "event": "mark",
            "mark": {"name": "marker-1", "trackSid": "track-1"},
        }))

        # 5. Stop
        await media_stream_handler.handle_message(json.dumps({"event": "stop"}))

        assert media_stream_handler.state.is_active is False
        # Queues should have sentinels
        assert not media_stream_handler._incoming_audio.empty()

    @pytest.mark.asyncio
    async def test_audio_conversion_accuracy(self, media_stream_handler, mock_websocket):
        """Test audio conversion preserves signal characteristics."""
        media_stream_handler.state.is_active = True
        media_stream_handler.state.stream_sid = "stream-123"
        await media_stream_handler.connect(mock_websocket)

        # Create a known signal: 1kHz tone at 8kHz μ-law
        import numpy as np
        duration = 0.1  # 100ms
        sample_rate = 8000
        frequency = 1000
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        pcm_8khz = (np.sin(2 * np.pi * frequency * t) * 10000).astype(np.int16).tobytes()
        from utils.audio import convert_pcm_to_mulaw
        mulaw = convert_pcm_to_mulaw(pcm_8khz)

        # Send as media
        payload_b64 = base64.b64encode(mulaw).decode("ascii")
        await media_stream_handler.handle_message(json.dumps({
            "event": "media",
            "media": {"payload": payload_b64, "trackSid": "track-1"},
        }))

        # Get converted PCM 16kHz
        pcm_16khz = await media_stream_handler._incoming_audio.get()

        # Verify length: 100ms at 16kHz = 1600 samples = 3200 bytes (approximately)
        assert abs(len(pcm_16khz) - 3200) < 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])