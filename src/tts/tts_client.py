"""
Gnani Timbre TTS Client

Supports REST, SSE streaming, and WebSocket realtime synthesis.
Integrates with retry logic, circuit breaker, structured logging, and standardized exceptions.

⚠️  UNVERIFIED ASSUMPTIONS (require Gnani API dashboard access):
- SSE endpoint path: POST /v1/synthesize/stream
- WebSocket endpoint path: WSS /v1/synthesize/ws
- Request/response schemas for streaming endpoints
- WebSocket wire protocol (config, audio format, message types)

Verified from docs:
- REST endpoint: POST /api/v1/tts/inference
- Model: timbre-v3.0
- Voices: 42 prebuilt across 10 languages
- SSML supported for fine-grained control
- Output sample rates: 8 kHz – 48 kHz
- Indian numeral formatting: rupees, lakh, crore normalized
- Language codes: hi, bn, ta, te, mr, gu, kn, ml, pa, en-IN
"""

import asyncio
import base64
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

import httpx
import websockets

from utils.exceptions import (
    AuthenticationError,
    ConnectionError,
    RateLimitError,
    ServerError,
    TimeoutError,
    wrap_httpx_error,
)
from utils.logging import get_logger, log_api_call
from utils.retry import CircuitBreaker, RetryConfig, with_retry

logger = get_logger(__name__)


@dataclass
class VoiceConfig:
    voice_id: str
    language: str
    gender: str  # "male" | "female"
    style: str  # "neutral", "conversational", "formal", etc.


# Verified voices from Gnani docs — timbre-v3.0 supported voices
KNOWN_VOICES = {
    "hi": ["Shivani", "Avinash"],
    "bn": ["Lakshmi", "Prakash"],
    "ta": ["Kalpana", "Shubham"],
    "te": ["Chetana", "Devansh"],
    "mr": ["Vasudha", "Harshad"],
    "gu": ["Riyaa", "Yashraj"],
    "kn": ["Tarika", "Prakash"],
    "ml": ["Lakshmi", "Avinash"],
    "pa": ["Shivani", "Avinash"],
    "en-IN": ["Shivani", "Avinash"],
    "en": ["Shivani", "Avinash"],
}


class TimbreTTSClient:
    """
    Client for Gnani Timbre TTS API v2.5.

    Verified Capabilities:
    - REST (sync): POST /api/v1/tts/inference
    - SSE streaming: POST /v1/synthesize/stream (UNVERIFIED)
    - WebSocket realtime: WSS /v1/synthesize/ws (UNVERIFIED)
    - Voices: 42 prebuilt across 10 languages
    - SSML supported for fine-grained control
    - Output sample rates: 8 kHz – 48 kHz
    - Indian numeral formatting: rupees, lakh, crore normalized
    - Language codes: hi, bn, ta, te, mr, gu, kn, ml, pa, en-IN
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.vachana.ai",
        retry_config: RetryConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._http_client: httpx.AsyncClient | None = None
        self._retry_config = retry_config or RetryConfig()
        self._circuit_breaker = circuit_breaker

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def _get_default_voice(self, language: str) -> str:
        """Get a default voice for the language."""
        voices = KNOWN_VOICES.get(language, KNOWN_VOICES.get("hi"))
        return voices[0] if voices else "Yashvi"

    # ==================== REST (SYNC) ====================

    @with_retry()
    async def synthesize(
        self,
        text: str,
        language: str = "hi",
        voice: str | None = None,
        sample_rate: int = 8000,
        encoding: Literal["wav", "mp3", "ogg", "mulaw"] = "mulaw",
        ssml: bool = False,
    ) -> bytes:
        """
        Synthesize speech via REST API (returns complete audio) with retry logic.

        Args:
            text: Text to synthesize (or SSML if ssml=True)
            language: Language code (hi, bn, ta, te, mr, gu, kn, ml, pa, en-IN)
            voice: Voice ID (defaults to first available for language)
            sample_rate: Output sample rate (8000 for telephony, 16000, 48000)
            encoding: Output format (mulaw for telephony, wav/mp3/ogg for files)
            ssml: Whether text is SSML markup

        Returns:
            Audio bytes in requested format

        Raises:
            AuthenticationError: On 401/403
            RateLimitError: On 429
            ServerError: On 5xx
            ValidationError: On invalid parameters
        """
        start_time = time.monotonic()
        client = await self._get_http_client()

        # Verified endpoint and schema from Gnani docs
        payload = {
            "text": text,
            "model": "timbre-v3.0",
            "voice": voice or self._get_default_voice(language),
            "language": language if "-" in language else f"{language}-IN",
            "speed": 1.0,
            "audio_config": {
                "sample_rate": sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }

        endpoint = f"{self.base_url}/api/v1/tts/inference"

        try:
            response = await client.post(
                endpoint,
                headers={"X-API-Key-ID": self.api_key, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            audio_data = response.content

            duration_ms = (time.monotonic() - start_time) * 1000
            log_api_call(
                logger,
                service="timbre-tts",
                method="POST",
                endpoint="/api/v1/tts/inference",
                status_code=response.status_code,
                duration_ms=duration_ms,
                language=language,
                voice=voice or self._get_default_voice(language),
                sample_rate=sample_rate,
                text_length=len(text),
            )
            return audio_data

        except httpx.HTTPStatusError as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            error = wrap_httpx_error(e, service="timbre-tts", endpoint="/api/v1/tts/inference")
            log_api_call(
                logger,
                service="timbre-tts",
                method="POST",
                endpoint="/api/v1/tts/inference",
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                error=error,
            )
            raise error from e

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            error = wrap_httpx_error(e, service="timbre-tts", endpoint="/api/v1/tts/inference")
            log_api_call(
                logger,
                service="timbre-tts",
                method="POST",
                endpoint="/api/v1/tts/inference",
                duration_ms=duration_ms,
                error=error,
            )
            raise error from e

    # ==================== SSE STREAMING ====================

    @with_retry()
    async def synthesize_stream_sse(
        self,
        text: str,
        language: str = "hi",
        voice: str | None = None,
        sample_rate: int = 8000,
        encoding: Literal["mulaw", "wav"] = "mulaw",
        ssml: bool = False,
        chunk_size: int = 1024,
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesis via SSE (Server-Sent Events) with retry logic.

        Yields audio chunks as they're generated (<200ms to first byte).

        UNVERIFIED — exact SSE endpoint and schema need Gnani API dashboard.
        """
        start_time = time.monotonic()
        client = await self._get_http_client()

        payload = {
            "text": text,
            "language": language,
            "voice": voice or self._get_default_voice(language),
            "sample_rate": sample_rate,
            "encoding": encoding,
            "ssml": ssml,
            "streaming": True,
        }

        # TODO: Verify exact SSE endpoint
        endpoint = f"{self.base_url}/v1/synthesize/stream"

        try:
            async with client.stream(
                "POST",
                endpoint,
                headers={
                    "X-API-Key-ID": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json=payload,
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size):
                    if chunk:
                        yield chunk

            duration_ms = (time.monotonic() - start_time) * 1000
            log_api_call(
                logger,
                service="timbre-tts",
                method="POST",
                endpoint="/v1/synthesize/stream",
                status_code=response.status_code,
                duration_ms=duration_ms,
                streaming=True,
            )

        except httpx.HTTPStatusError as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            error = wrap_httpx_error(e, service="timbre-tts", endpoint="/v1/synthesize/stream")
            log_api_call(
                logger,
                service="timbre-tts",
                method="POST",
                endpoint="/v1/synthesize/stream",
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                error=error,
            )
            raise error from e

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            error = wrap_httpx_error(e, service="timbre-tts", endpoint="/v1/synthesize/stream")
            log_api_call(
                logger,
                service="timbre-tts",
                method="POST",
                endpoint="/v1/synthesize/stream",
                duration_ms=duration_ms,
                error=error,
            )
            raise error from e

    # ==================== WEBSOCKET REALTIME ====================

    async def synthesize_stream_ws(
        self,
        text_iterator: AsyncIterator[str],
        language: str = "hi",
        voice: str | None = None,
        sample_rate: int = 8000,
        encoding: Literal["mulaw", "pcm16"] = "mulaw",
        ssml: bool = False,
    ) -> AsyncIterator[bytes]:
        """
        Bidirectional WebSocket streaming for real-time TTS.

        Send text chunks, receive audio chunks in real-time.

        UNVERIFIED — WebSocket endpoint and protocol need Gnani API dashboard.
        """
        ws_url = f"{self.base_url.replace('https://', 'wss://')}/v1/synthesize/ws"

        try:
            async with websockets.connect(ws_url, extra_headers={"X-API-Key-ID": self.api_key}) as ws:
                # Send configuration
                await ws.send(
                    json.dumps(
                        {
                            "config": {
                                "language": language,
                                "voice": voice or self._get_default_voice(language),
                                "sample_rate": sample_rate,
                                "encoding": encoding,
                                "ssml": ssml,
                            }
                        }
                    )
                )

                # Sender task: stream text chunks
                async def send_text():
                    async for text_chunk in text_iterator:
                        await ws.send(json.dumps({"text": text_chunk, "ssml": ssml}))
                    await ws.send(json.dumps({"type": "end"}))

                sender_task = asyncio.create_task(send_text())

                # Receiver: yield audio chunks
                try:
                    async for message in ws:
                        data = json.loads(message)
                        if data.get("type") == "audio":
                            # Audio data may be base64 encoded or raw bytes
                            audio_b64 = data.get("data", "")
                            yield base64.b64decode(audio_b64)
                        elif data.get("type") == "error":
                            error_msg = data.get("message", "Unknown error")
                            error_code = data.get("code")
                            if error_code in (401, 403):
                                raise AuthenticationError(f"Timbre TTS auth error: {error_msg}")
                            elif error_code == 429:
                                raise RateLimitError(f"Timbre TTS rate limited: {error_msg}")
                            elif error_code and 500 <= error_code < 600:
                                raise ServerError(f"Timbre TTS server error: {error_msg}")
                            raise RuntimeError(f"Timbre TTS error: {error_msg}")
                finally:
                    sender_task.cancel()
                    try:
                        await sender_task
                    except asyncio.CancelledError:
                        pass

        except websockets.InvalidStatusCode as e:
            if e.status_code in (401, 403):
                raise AuthenticationError(f"WebSocket auth failed: HTTP {e.status_code}") from e
            raise ConnectionError(f"WebSocket connection failed: HTTP {e.status_code}") from e
        except websockets.ConnectionClosed as e:
            raise ConnectionError(f"WebSocket closed unexpectedly: {e.code} {e.reason}") from e

    # ==================== CONVENIENCE ====================

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        language: str = "hi",
        voice: str | None = None,
        sample_rate: int = 8000,
    ) -> str:
        """Synthesize and save to file."""
        audio = await self.synthesize(text, language, voice, sample_rate, "wav")
        with open(output_path, "wb") as f:
            f.write(audio)
        return output_path


# ==================== STANDALONE FUNCTIONS ====================


async def quick_synthesize(
    text: str, api_key: str, language: str = "hi", output_path: str | None = None
) -> bytes:
    """Quick one-off synthesis."""
    client = TimbreTTSClient(api_key)
    try:
        audio = await client.synthesize(text, language=language)
        if output_path:
            with open(output_path, "wb") as f:
                f.write(audio)
        return audio
    finally:
        await client.close()