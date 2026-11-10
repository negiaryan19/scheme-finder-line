"""
Audio Utilities

Load, convert, and save audio files for Prisma STT and Timbre TTS integration.

Uses audioop for accurate μ-law (G.711) conversion per ITU-T standard.
"""

import audioop
import wave

import numpy as np
from pydub import AudioSegment


def load_audio_file(file_path: str, target_sample_rate: int = 16000) -> tuple[bytes, int]:
    """
    Load audio file and convert to target sample rate mono PCM.
    Tries native wave module first to avoid ffmpeg dependency.
    """
    # 1. Try native wave module for WAV files
    try:
        with wave.open(file_path, "rb") as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            raw_data = wf.readframes(wf.getnframes())

            # Convert 16-bit stereo to mono if needed
            if channels == 2 and sample_width == 2:
                samples = np.frombuffer(raw_data, dtype=np.int16)
                mono = samples.reshape(-1, 2).mean(axis=1).astype(np.int16)
                raw_data = mono.tobytes()

            # Resample if needed
            if sample_rate != target_sample_rate:
                raw_data = audioop.ratecv(raw_data, sample_width, 1, sample_rate, target_sample_rate, None)[0]

            return raw_data, target_sample_rate
    except Exception:
        pass

    # 2. Fallback to pydub if wave fails
    audio = AudioSegment.from_file(file_path)

    # Convert to mono
    if audio.channels > 1:
        audio = audio.set_channels(1)

    # Resample
    if audio.frame_rate != target_sample_rate:
        audio = audio.set_frame_rate(target_sample_rate)

    # Ensure 16-bit PCM
    audio = audio.set_sample_width(2)

    return audio.raw_data, audio.frame_rate


def save_audio_file(
    audio_bytes: bytes,
    output_path: str,
    sample_rate: int = 8000,
    channels: int = 1,
    sample_width: int = 2,
) -> str:
    """
    Save raw PCM bytes to WAV file.

    Args:
        audio_bytes: Raw PCM audio data
        output_path: Output file path (.wav)
        sample_rate: Sample rate of the audio data
        channels: Number of channels (1 for mono)
        sample_width: Sample width in bytes (2 for 16-bit)

    Returns:
        Output path
    """
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_bytes)
    return output_path


def convert_mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
    """
    Convert μ-law encoded bytes to 16-bit PCM using audioop (ITU-T G.711).

    This is the standard, accurate implementation using the system's audioop module.
    """
    # audioop.ulaw2lin expects 8-bit μ-law input, returns 16-bit linear PCM
    return audioop.ulaw2lin(mulaw_bytes, 2)


def convert_pcm_to_mulaw(pcm_bytes: bytes) -> bytes:
    """
    Convert 16-bit PCM bytes to μ-law encoded bytes using audioop (ITU-T G.711).

    This is the standard, accurate implementation using the system's audioop module.
    """
    # audioop.lin2ulaw expects 16-bit linear PCM input, returns 8-bit μ-law
    return audioop.lin2ulaw(pcm_bytes, 2)


def resample_audio(audio_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
    """Resample PCM audio using audioop (faster than pydub for simple resampling)."""
    return audioop.ratecv(audio_bytes, 2, 1, from_rate, to_rate, None)[0]


def get_audio_duration(file_path: str) -> float:
    """Get duration of audio file in seconds."""
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0


def split_audio_chunks(
    audio_bytes: bytes, sample_rate: int, chunk_duration_ms: int = 100
) -> list[bytes]:
    """Split audio into fixed-duration chunks for streaming."""
    samples_per_chunk = int(sample_rate * chunk_duration_ms / 1000)
    bytes_per_chunk = samples_per_chunk * 2  # 16-bit = 2 bytes/sample

    chunks = []
    for i in range(0, len(audio_bytes), bytes_per_chunk):
        chunk = audio_bytes[i : i + bytes_per_chunk]
        if len(chunk) == bytes_per_chunk:
            chunks.append(chunk)
        elif len(chunk) > 0:
            # Pad last chunk
            chunk += b"\x00" * (bytes_per_chunk - len(chunk))
            chunks.append(chunk)
    return chunks


def convert_twilio_to_stt_format(mulaw_bytes: bytes) -> bytes:
    """
    Convert Twilio Media Stream μ-law 8kHz audio to Prisma STT 16kHz PCM format.

    Twilio sends: μ-law encoded, 8kHz, mono
    Prisma STT expects: 16-bit PCM, 16kHz (or 8kHz/48kHz), mono

    This function:
    1. Decodes μ-law to 16-bit PCM (8kHz)
    2. Resamples from 8kHz to 16kHz
    """
    # Step 1: μ-law → 16-bit PCM (8kHz)
    pcm_8khz = convert_mulaw_to_pcm(mulaw_bytes)

    # Step 2: Resample 8kHz → 16kHz
    pcm_16khz = resample_audio(pcm_8khz, 8000, 16000)

    return pcm_16khz


def convert_stt_to_twilio_format(pcm_16khz_bytes: bytes) -> bytes:
    """
    Convert Prisma STT 16kHz PCM to Twilio μ-law 8kHz format.

    For TTS output going back to Twilio Media Streams.
    """
    # Step 1: Resample 16kHz → 8kHz
    pcm_8khz = resample_audio(pcm_16khz_bytes, 16000, 8000)

    # Step 2: 16-bit PCM → μ-law
    mulaw_bytes = convert_pcm_to_mulaw(pcm_8khz)

    return mulaw_bytes