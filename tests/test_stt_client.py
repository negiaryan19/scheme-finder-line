"""
Unit Tests for Gnani Prisma STT Client

Tests use mocked HTTP and WebSocket responses.
No real API calls are made.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import websockets

from src.stt.client import PrismaSTTClient, transcribe_audio_file


class MockHTTPResponse:
    """Mock httpx.Response for testing."""

    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=MagicMock(), response=self
            )


class MockWebSocket:
    """Mock websockets connection for testing."""

    def __init__(self, messages):
        self.messages = messages
        self.sent_messages = []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def send(self, message):
        self.sent_messages.append(message)

    async def recv(self):
        if self.messages:
            return self.messages.pop(0)
        raise websockets.ConnectionClosed(1000, "OK")

    async def ping(self):
        return MagicMock()

    async def close(self):
        self.closed = True


# ==================== FIXTURES ====================


@pytest.fixture
def mock_http_client():
    """Mock httpx.AsyncClient."""
    with patch("src.stt.client.httpx.AsyncClient") as mock:
        client_instance = AsyncMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def mock_websocket():
    """Mock websockets.connect."""
    with patch("src.stt.client.websockets.connect") as mock:
        yield mock


@pytest.fixture
def sample_audio_bytes():
    """Sample 16-bit PCM audio bytes (1 second at 16kHz)."""
    import numpy as np

    # Generate 1 second of silence at 16kHz, 16-bit mono
    samples = np.zeros(16000, dtype=np.int16)
    return samples.tobytes()


@pytest.fixture
def stt_client():
    """PrismaSTTClient with test API key."""
    return PrismaSTTClient(api_key="test-api-key-123")


# ==================== TESTS: INITIALIZATION ====================


def test_client_initialization(stt_client):
    """Test client initializes with correct defaults."""
    assert stt_client.api_key == "test-api-key-123"
    assert stt_client.base_url == "https://api.vachana.ai"
    assert stt_client.http_timeout == 60.0
    assert stt_client.ws_recv_timeout == 30.0


def test_client_from_env(monkeypatch):
    """Test from_env classmethod loads API key from environment."""
    monkeypatch.setenv("GNANI_API_KEY", "env-api-key-456")
    client = PrismaSTTClient.from_env()
    assert client.api_key == "env-api-key-456"


def test_client_from_env_missing(monkeypatch):
    """Test from_env raises when env var missing."""
    monkeypatch.delenv("GNANI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GNANI_API_KEY not set"):
        PrismaSTTClient.from_env()


def test_client_invalid_api_key():
    """Test client rejects empty API key."""
    with pytest.raises(ValueError, match="api_key is required"):
        PrismaSTTClient(api_key="")


def test_client_custom_timeouts():
    """Test client accepts custom timeouts."""
    client = PrismaSTTClient(
        api_key="test",
        http_timeout=30.0,
        ws_recv_timeout=10.0,
        ws_ping_interval=5.0,
        ws_ping_timeout=3.0,
    )
    assert client.http_timeout == 30.0
    assert client.ws_recv_timeout == 10.0
    assert client.ws_ping_interval == 5.0
    assert client.ws_ping_timeout == 3.0


# ==================== TESTS: TRANSCRIBE FILE (REST) ====================


@pytest.mark.asyncio
async def test_transcribe_file_success(stt_client, mock_http_client, sample_audio_bytes):
    """Test successful file transcription."""
    # Setup mock response
    mock_response = MockHTTPResponse(
        {
            "text": "Namaste, main kisan hoon",
            "language": "hi-IN",
            "segments": [
                {"text": "Namaste", "start": 0.0, "end": 0.5, "confidence": 0.98},
                {"text": "main kisan hoon", "start": 0.5, "end": 2.0, "confidence": 0.95},
            ],
            "confidence": 0.96,
        }
    )
    mock_http_client.post.return_value = mock_response

    # Call method
    result = await stt_client.transcribe_file(sample_audio_bytes)

    # Verify request
    mock_http_client.post.assert_called_once()
    call_args = mock_http_client.post.call_args
    assert call_args[0][0] == "https://api.vachana.ai/stt/v3"
    assert call_args[1]["headers"]["X-API-Key-ID"] == "test-api-key-123"
    assert "Content-Type" not in call_args[1]["headers"]  # multipart auto-set
    assert call_args[1]["files"]["audio_file"][0] == "audio.wav"
    assert call_args[1]["data"]["model"] == "prisma-v3.0"
    assert call_args[1]["data"]["format"] == "codemix"

    # Verify response
    assert result["text"] == "Namaste, main kisan hoon"
    assert result["language"] == "hi-IN"
    assert result["confidence"] == 0.96


@pytest.mark.asyncio
async def test_transcribe_file_http_error(stt_client, mock_http_client, sample_audio_bytes):
    """Test file transcription handles HTTP errors."""
    from utils.exceptions import AuthenticationError
    mock_http_client.post.return_value = MockHTTPResponse(
        {"error": "Invalid API key"}, status_code=401
    )

    with pytest.raises(AuthenticationError, match="Authentication failed"):
        await stt_client.transcribe_file(sample_audio_bytes)


@pytest.mark.asyncio
async def test_transcribe_file_empty_audio(stt_client):
    """Test file transcription rejects empty audio."""
    with pytest.raises(ValueError, match="audio_bytes cannot be empty"):
        await stt_client.transcribe_file(b"")


@pytest.mark.asyncio
async def test_transcribe_file_invalid_sample_rate(stt_client, sample_audio_bytes):
    """Test file transcription rejects invalid sample rate."""
    with pytest.raises(ValueError, match="Unsupported sample_rate"):
        await stt_client.transcribe_file(sample_audio_bytes, sample_rate=44100)


@pytest.mark.asyncio
async def test_transcribe_file_invalid_output_mode(stt_client, sample_audio_bytes):
    """Test file transcription rejects invalid output mode."""
    with pytest.raises(ValueError, match="Invalid output_mode"):
        await stt_client.transcribe_file(sample_audio_bytes, output_mode="invalid")


@pytest.mark.asyncio
async def test_transcribe_file_with_keyterms(stt_client, mock_http_client, sample_audio_bytes):
    """Test file transcription with keyterms."""
    mock_http_client.post.return_value = MockHTTPResponse({"text": "test"})

    await stt_client.transcribe_file(
        sample_audio_bytes, keyterms=[{"find": "PM KISAN", "replace": "PM-KISAN"}]
    )

    call_args = mock_http_client.post.call_args
    assert "keyterms" in call_args[1]["data"]
    import json

    keyterms = json.loads(call_args[1]["data"]["keyterms"])
    assert keyterms[0]["find"] == "PM KISAN"


# ==================== TESTS: TRANSCRIBE STREAM (WEBSOCKET) ====================


@pytest.mark.asyncio
async def test_transcribe_stream_success(stt_client, mock_websocket, sample_audio_bytes):
    """Test successful streaming transcription."""
    # Setup mock WebSocket messages
    ws_messages = [
        json.dumps(
            {
                "type": "transcript",
                "text": "Namaste",
                "is_final": False,
                "language": "hi-IN",
                "confidence": 0.9,
                "start_time": 0.0,
                "end_time": 0.5,
            }
        ),
        json.dumps(
            {
                "type": "transcript",
                "text": "Namaste main kisan hoon",
                "is_final": True,
                "language": "hi-IN",
                "confidence": 0.95,
                "start_time": 0.0,
                "end_time": 2.0,
            }
        ),
        json.dumps({"type": "end"}),
    ]
    mock_ws = MockWebSocket(ws_messages.copy())
    mock_websocket.return_value.__aenter__.return_value = mock_ws

    # Create audio iterator
    async def audio_iter():
        # Split into chunks
        chunk_size = 3200  # 100ms at 16kHz
        for i in range(0, len(sample_audio_bytes), chunk_size):
            yield sample_audio_bytes[i : i + chunk_size]

    # Collect results
    results = []
    async for segment in stt_client.transcribe_stream(audio_iter()):
        results.append(segment)

    # Verify sent config
    assert len(mock_ws.sent_messages) >= 1
    config_sent = json.loads(mock_ws.sent_messages[0])
    assert "config" in config_sent
    assert config_sent["config"]["model"] == "prisma-v3.0"
    assert config_sent["config"]["sample_rate"] == 16000

    # Verify results
    assert len(results) == 2
    assert results[0].text == "Namaste"
    assert results[0].is_final is False
    assert results[1].text == "Namaste main kisan hoon"
    assert results[1].is_final is True
    assert results[0].language == "hi-IN"
    assert results[1].confidence == 0.95


@pytest.mark.asyncio
async def test_transcribe_stream_server_error(stt_client, mock_websocket):
    """Test streaming handles server error message."""
    ws_messages = [
        json.dumps({"type": "error", "message": "Model overloaded"}),
    ]
    mock_ws = MockWebSocket(ws_messages)
    mock_websocket.return_value.__aenter__.return_value = mock_ws

    async def audio_iter():
        yield b"test"

    with pytest.raises(RuntimeError, match="Prisma STT error: Model overloaded"):
        async for _ in stt_client.transcribe_stream(audio_iter()):
            pass


@pytest.mark.asyncio
async def test_transcribe_stream_invalid_sample_rate(stt_client):
    """Test streaming rejects invalid sample rate."""

    async def audio_iter():
        yield b"test"

    with pytest.raises(ValueError, match="Unsupported sample_rate"):
        # Consume the async generator to trigger validation
        async for _ in stt_client.transcribe_stream(audio_iter(), sample_rate=44100):
            pass


@pytest.mark.asyncio
async def test_transcribe_stream_connection_error(stt_client, mock_websocket):
    """Test streaming handles connection failure."""
    from utils.exceptions import AuthenticationError
    # InvalidStatusCode requires status_code and headers
    mock_websocket.side_effect = websockets.InvalidStatusCode(status_code=403, headers={})

    async def audio_iter():
        yield b"test"

    # Test that exception is raised during async iteration
    try:
        async for _ in stt_client.transcribe_stream(audio_iter()):
            pass
    except AuthenticationError as e:
        assert "WebSocket auth failed: HTTP 403" in str(e)
    else:
        pytest.fail("Expected AuthenticationError")


@pytest.mark.asyncio
async def test_transcribe_stream_connection_closed(stt_client, mock_websocket):
    """Test streaming handles unexpected connection close during streaming."""
    from utils.exceptions import ConnectionError
    # Create a mock websocket that connects successfully but then closes on recv
    mock_ws = MagicMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=None)
    mock_ws.send = AsyncMock()
    mock_ws.ping = AsyncMock()
    # First recv raises ConnectionClosed
    mock_ws.recv = AsyncMock(side_effect=websockets.ConnectionClosed(rcvd=None, sent=None))

    mock_websocket.return_value = mock_ws

    async def audio_iter():
        yield b"test"

    # Test that exception is raised during async iteration
    try:
        async for _ in stt_client.transcribe_stream(audio_iter()):
            pass
    except ConnectionError as e:
        assert "WebSocket closed unexpectedly" in str(e)
    else:
        pytest.fail("Expected ConnectionError")


@pytest.mark.asyncio
async def test_transcribe_stream_receive_timeout(stt_client, mock_websocket):
    """Test streaming handles receive timeout with ping recovery."""
    import asyncio
    from unittest.mock import patch

    # Create a mock websocket
    mock_ws = MagicMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=None)
    mock_ws.send = AsyncMock()
    mock_ws.ping = AsyncMock()
    mock_ws.recv = AsyncMock(side_effect=[
        json.dumps(
            {
                "type": "transcript",
                "text": "Hello",
                "is_final": True,
                "language": "en-IN",
                "confidence": 0.9,
            }
        ),
        json.dumps({"type": "end"}),
    ])

    mock_websocket.return_value = mock_ws

    async def audio_iter():
        yield b"test"

    # Patch asyncio.wait_for to raise TimeoutError on first call, then return recv result
    wait_for_calls = [0]
    original_wait_for = asyncio.wait_for

    async def mock_wait_for(coro, timeout):
        wait_for_calls[0] += 1
        if wait_for_calls[0] == 1:
            # First call: simulate timeout
            raise asyncio.TimeoutError()
        # Subsequent calls: execute normally
        return await original_wait_for(coro, timeout)

    results = []
    with patch("asyncio.wait_for", side_effect=mock_wait_for):
        async for segment in stt_client.transcribe_stream(audio_iter()):
            results.append(segment)

    assert len(results) == 1
    assert results[0].text == "Hello"
    # Verify ping was called for recovery
    mock_ws.ping.assert_called()


# ==================== TESTS: CONVENIENCE FUNCTION ====================


@pytest.mark.asyncio
async def test_transcribe_audio_file_convenience(monkeypatch, tmp_path):
    """Test convenience function loads audio and transcribes."""
    # Create dummy audio file
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"RIFF" + bytes([0]) * 100)  # Minimal WAV header

    # Mock load_audio_file by replacing utils.audio in sys.modules
    # BEFORE the convenience function imports it at runtime.
    # The function does: from utils.audio import load_audio_file
    # So we must ensure both utils.audio and src.utils.audio resolve to our mock.
    import sys

    import src.utils.audio as audio_module

    def mock_load(*args, **kwargs):
        return b"fake audio", 16000

    # Replace the function on the module
    audio_module.load_audio_file = mock_load
    # Ensure sys.modules has the mocked module for BOTH import paths
    monkeypatch.setitem(sys.modules, "src.utils.audio", audio_module)
    monkeypatch.setitem(sys.modules, "utils.audio", audio_module)

    # Mock PrismaSTTClient.transcribe_file
    async def mock_transcribe(*args, **kwargs):
        return {"text": "test transcript", "language": "hi-IN"}

    monkeypatch.setattr(PrismaSTTClient, "transcribe_file", mock_transcribe)
    monkeypatch.setattr(PrismaSTTClient, "close", AsyncMock())
    monkeypatch.setattr(PrismaSTTClient, "from_env", lambda: PrismaSTTClient(api_key="test"))

    result = await transcribe_audio_file(str(audio_file))
    assert result["text"] == "test transcript"
    assert result["language"] == "hi-IN"


# ==================== TESTS: CONTEXT MANAGER ====================
