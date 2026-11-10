"""
Gnani Prisma STT Client

Supports both file-based (REST) and streaming (WebSocket) transcription.
Integrates with retry logic, circuit breaker, structured logging, and standardized exceptions.

⚠️  UNVERIFIED ASSUMPTIONS (require Gnani API dashboard access):
- REST endpoint path: POST /stt/v3 (verified from docs)
- WebSocket endpoint path: WSS /v1/transcribe/stream
- REST multipart request field names: "audio_file" file + form fields
- WebSocket config message schema and audio wire format (raw PCM? μ-law?)
- Response transcript segment schema (text, is_final, language, confidence, timestamps)
- Rate limits, credit consumption, error codes

Verified from docs:
- Base URL: https://api.vachana.ai
- Auth: X-API-Key-ID header
- Model: prisma-v3.0 for multilingual + code-mixed
- Languages: 10 Indian + English (hi, bn, ta, te, mr, gu, kn, ml, pa, as, en)
- Output modes: verbatim, transcribe, codemix, transliterate
- Sample rates: 8kHz (telephony), 16kHz (VoIP), 48kHz (studio)
- Auto language detection (95% accuracy on 3+ sec audio)
"""

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

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
class TranscriptSegment:
    """Transcript segment from Prisma STT (schema ASSUMED, not verified)."""

    text: str
    is_final: bool
    language: str
    confidence: float
    start_time: float
    end_time: float


class PrismaSTTClient:
    """
    Client for Gnani Prisma STT API.

    Verified Capabilities (from public docs):
    - REST endpoint: file upload ≤30s (POST /stt/v3)
    - WebSocket streaming: real-time (endpoint path UNVERIFIED)
    - Model: prisma-v3.0 for multilingual + code-mixed
    - Languages: 10 Indian + English
    - Output modes: verbatim, transcribe, codemix, transliterate
    - Auto language detection (95% accuracy on 3+ sec)

    UNVERIFIED — requires Gnani API dashboard:
    - Exact WebSocket endpoint path
    - Request/response JSON schemas
    - WebSocket wire protocol (config, audio format, message types)
    - Rate limits and credit consumption
    """

    # Default timeouts (configurable)
    DEFAULT_HTTP_TIMEOUT = 60.0
    DEFAULT_WS_RECV_TIMEOUT = 30.0
    DEFAULT_WS_PING_INTERVAL = 20.0
    DEFAULT_WS_PING_TIMEOUT = 10.0

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.vachana.ai",
        http_timeout: float = DEFAULT_HTTP_TIMEOUT,
        ws_recv_timeout: float = DEFAULT_WS_RECV_TIMEOUT,
        ws_ping_interval: float = DEFAULT_WS_PING_INTERVAL,
        ws_ping_timeout: float = DEFAULT_WS_PING_TIMEOUT,
        retry_config: RetryConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.http_timeout = http_timeout
        self.ws_recv_timeout = ws_recv_timeout
        self.ws_ping_interval = ws_ping_interval
        self.ws_ping_timeout = ws_ping_timeout
        self._http_client: httpx.AsyncClient | None = None
        self._retry_config = retry_config or RetryConfig()
        self._circuit_breaker = circuit_breaker

    @classmethod
    def from_env(cls, env_var: str = "GNANI_API_KEY", **kwargs) -> "PrismaSTTClient":
        """Create client with API key from environment variable."""
        api_key = os.getenv(env_var)
        if not api_key:
            raise ValueError(f"Environment variable {env_var} not set")
        return cls(api_key=api_key, **kwargs)

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self._http_client = httpx.AsyncClient(
                timeout=self.http_timeout,
                limits=limits,
            )
        return self._http_client

    async def close(self):
        """Close HTTP client and release resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self) -> "PrismaSTTClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # ==================== FILE-BASED (REST) ====================

    @with_retry()
    async def transcribe_file(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: str = "auto",
        model: str = "prisma-v3.0",
        output_mode: str = "codemix",
        punctuation: bool = True,
        normalize: bool = True,
        keyterms: list[dict] | None = None,
    ) -> dict:
        """
        Transcribe audio file via REST API with retry logic.

        Args:
            audio_bytes: Raw audio data (WAV, MP3, OGG, FLAC, AAC, M4A)
            sample_rate: 8000 (telephony), 16000 (VoIP), 48000 (studio)
            language: BCP-47 code (hi-IN, mr-IN, etc.) or "auto"
            model: "prisma-v2.5" or "prisma-v3.0" (multilingual)
            output_mode: verbatim, transcribe, codemix, transliterate
            punctuation: Enable auto-punctuation
            normalize: Enable text normalization
            keyterms: Optional list of up to 200 keyterm dicts {"find": "...", "replace": "..."}

        Returns:
            Dict with: text, language, segments[], confidence
            (Response schema UNVERIFIED — adjust after real API test)

        Raises:
            AuthenticationError: On 401/403
            RateLimitError: On 429
            ServerError: On 5xx
            ValidationError: On invalid parameters
        """
        start_time = time.monotonic()

        if not audio_bytes:
            raise ValueError("audio_bytes cannot be empty")
        if sample_rate not in (8000, 16000, 48000):
            raise ValueError(f"Unsupported sample_rate: {sample_rate}. Use 8000, 16000, or 48000")
        if output_mode not in ("verbatim", "transcribe", "codemix", "transliterate"):
            raise ValueError(f"Invalid output_mode: {output_mode}")

        # Map "auto" to Gnani's "indic-auto" language code
        if language == "auto":
            language = "indic-auto"

        client = await self._get_http_client()

        # Wrap raw PCM bytes in a WAV container for the API
        import io
        import wave as wave_mod

        wav_buffer = io.BytesIO()
        with wave_mod.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_bytes)
        wav_bytes = wav_buffer.getvalue()

        # Verified field names from Gnani docs: audio_file, model, language_code, format
        files = {"audio_file": ("audio.wav", wav_bytes, "audio/wav")}
        data = {
            "model": model,
            "language_code": language,
            "format": output_mode,
        }
        if keyterms:
            import json as json_lib

            data["keyterms"] = json_lib.dumps(keyterms)

        # Verified endpoint: POST /stt/v3
        endpoint = f"{self.base_url}/stt/v3"

        try:
            response = await client.post(
                endpoint,
                headers={"X-API-Key-ID": self.api_key},  # No Content-Type — httpx sets multipart
                files=files,
                data=data,
            )
            response.raise_for_status()
            result = response.json()
            # Normalize schema: ensure both "text" and "transcript" are present
            if "transcript" in result and "text" not in result:
                result["text"] = result["transcript"]
            elif "text" in result and "transcript" not in result:
                result["transcript"] = result["text"]

            duration_ms = (time.monotonic() - start_time) * 1000
            log_api_call(
                logger,
                service="prisma-stt",
                method="POST",
                endpoint="/stt/v3",
                status_code=response.status_code,
                duration_ms=duration_ms,
                sample_rate=sample_rate,
                language=language,
                output_mode=output_mode,
            )
            return result

        except httpx.HTTPStatusError as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            error = wrap_httpx_error(e, service="prisma-stt", endpoint="/stt/v3")
            log_api_call(
                logger,
                service="prisma-stt",
                method="POST",
                endpoint="/stt/v3",
                status_code=e.response.status_code,
                duration_ms=duration_ms,
                error=error,
            )
            raise error from e

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            error = wrap_httpx_error(e, service="prisma-stt", endpoint="/stt/v3")
            log_api_call(
                logger,
                service="prisma-stt",
                method="POST",
                endpoint="/stt/v3",
                duration_ms=duration_ms,
                error=error,
            )
            raise error from e

    # ==================== STREAMING (WEBSOCKET) ====================

    async def transcribe_stream(
        self,
        audio_iterator: AsyncIterator[bytes],
        sample_rate: int = 16000,
        language: str = "auto",
        model: str = "prisma-v3.0",
        output_mode: str = "codemix",
        punctuation: bool = True,
        normalize: bool = True,
        audio_encoding: str = "pcm16",  # UNVERIFIED: "pcm16" | "mulaw" | "opus"
    ) -> AsyncIterator[TranscriptSegment]:
        """
        Stream audio to Prisma WebSocket, yield transcript segments in real-time.

        Args:
            audio_iterator: Async iterator yielding audio chunks (bytes)
            sample_rate: 8000, 16000, or 48000
            language: BCP-47 code or "auto"
            model: "prisma-v3.0" for multilingual
            output_mode: verbatim, transcribe, codemix, transliterate
            punctuation: Enable auto-punctuation
            normalize: Enable text normalization
            audio_encoding: UNVERIFIED — expected wire format for audio chunks

        Yields:
            TranscriptSegment objects with interim and final results

        Raises:
            AuthenticationError: On auth failure
            RateLimitError: On 429
            ServerError: On 5xx
            TimeoutError: On receive timeout
            ConnectionError: On connection failure

        UNVERIFIED — requires Gnani API dashboard:
        - WebSocket endpoint path
        - Config message schema
        - Audio chunk wire format (raw PCM16? μ-law? length-prefixed?)
        - Server message types and fields
        """
        if sample_rate not in (8000, 16000, 48000):
            raise ValueError(f"Unsupported sample_rate: {sample_rate}")

        # UNVERIFIED: Exact WebSocket endpoint path
        ws_url = f"{self.base_url.replace('https://', 'wss://')}/v1/transcribe/stream"

        # WebSocket connection with keepalive
        try:
            async with websockets.connect(
                ws_url,
                extra_headers={"X-API-Key-ID": self.api_key},
                ping_interval=self.ws_ping_interval,
                ping_timeout=self.ws_ping_timeout,
                close_timeout=5.0,
            ) as ws:
                # Send configuration (UNVERIFIED schema)
                config_msg = {
                    "config": {
                        "model": model,
                        "language": language,
                        "sample_rate": sample_rate,
                        "output_mode": output_mode,
                        "interim_results": True,
                        "punctuation": punctuation,
                        "normalize": normalize,
                        "audio_encoding": audio_encoding,
                    }
                }
                await ws.send(json.dumps(config_msg))

                # Sender task: stream audio chunks
                async def send_audio():
                    try:
                        async for chunk in audio_iterator:
                            if not chunk:
                                continue
                            # UNVERIFIED: Wire format — raw bytes? length-prefixed? base64?
                            await ws.send(chunk)
                    except Exception as e:
                        logger.error("STT sender error", error=str(e), exc_info=True)
                    finally:
                        # Signal end of stream (UNVERIFIED message type)
                        try:
                            await ws.send(json.dumps({"type": "end"}))
                        except Exception:
                            pass

                sender_task = asyncio.create_task(send_audio())

                # Receiver: yield transcripts with timeout
                try:
                    while True:
                        try:
                            message = await asyncio.wait_for(
                                ws.recv(), timeout=self.ws_recv_timeout
                            )
                        except asyncio.TimeoutError:
                            # Send ping to check connection health
                            try:
                                await ws.ping()
                                continue
                            except Exception:
                                raise TimeoutError("WebSocket connection lost (ping failed)")

                        try:
                            data = json.loads(message)
                        except json.JSONDecodeError:
                            # Might be binary audio echo or malformed — skip
                            continue

                        msg_type = data.get("type")
                        if msg_type == "transcript":
                            yield TranscriptSegment(
                                text=data.get("text", ""),
                                is_final=data.get("is_final", False),
                                language=data.get("language", language),
                                confidence=float(data.get("confidence", 0.0)),
                                start_time=float(data.get("start_time", 0.0)),
                                end_time=float(data.get("end_time", 0.0)),
                            )
                        elif msg_type == "error":
                            error_msg = data.get("message", "Unknown error")
                            error_code = data.get("code")
                            if error_code in (401, 403):
                                raise AuthenticationError(f"Prisma STT auth error: {error_msg}")
                            elif error_code == 429:
                                raise RateLimitError(f"Prisma STT rate limited: {error_msg}")
                            elif error_code and 500 <= error_code < 600:
                                raise ServerError(f"Prisma STT server error: {error_msg}")
                            raise RuntimeError(f"Prisma STT error: {error_msg}")
                        elif msg_type == "end":
                            break
                        # Ignore unknown message types (e.g., "ack", "ping")

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


# ==================== CONVENIENCE FUNCTIONS ====================


async def transcribe_audio_file(
    file_path: str, api_key: str = None, language: str = "auto", **kwargs
) -> dict:
    """Convenience function for file transcription. Loads API key from env if not provided."""
    from utils.audio import load_audio_file

    audio_data, sample_rate = load_audio_file(file_path)
    client = PrismaSTTClient.from_env() if api_key is None else PrismaSTTClient(api_key)
    try:
        return await client.transcribe_file(audio_data, sample_rate, language=language, **kwargs)
    finally:
        await client.close()