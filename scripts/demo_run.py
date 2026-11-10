#!/usr/bin/env python3
"""
Full Demo Run — Scheme Finder Line MVP

Runs the complete pipeline with mock services so you can see the output
without needing real API keys, PostgreSQL, or audio files.

Usage:
    cd /Users/aryannegi/Desktop/scheme-finder-line
    python scripts/demo_run.py

When real GNANI_API_KEY is set in .env, pass --real-stt to hit the live API.
"""

import asyncio
import math
import os
import struct
import sys
import time
import wave
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

# Import mock Evon (always available)
from llm.mock import mock_evon_response


# ─── Synthetic Audio Generator ───────────────────────────────────────────────
def generate_test_audio(duration_s: float = 3.0, sample_rate: int = 16000) -> bytes:
    """Generate a synthetic WAV-like PCM tone (440 Hz sine wave)."""
    n_samples = int(duration_s * sample_rate)
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        val = int(16000 * math.sin(2 * math.pi * 440 * t))
        samples.append(struct.pack("<h", max(-32768, min(32767, val))))
    return b"".join(samples)


def save_test_wav(path: str, pcm_bytes: bytes, sample_rate: int = 16000):
    """Save PCM bytes as a WAV file."""
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)


# ─── Mock STT ────────────────────────────────────────────────────────────────
class MockPrismaSTT:
    """Simulates Prisma STT response for demo."""

    DEMO_TRANSCRIPTS = {
        "farmer": {
            "text": "Mera naam Ramesh hai, main Maharashtra se hoon. Main ek kisan hoon aur pyaaz ki kheti karta hoon. Koi sarkari yojana hai mere liye?",
            "language": "hi-IN",
        },
        "student": {
            "text": "Main 12th pass hoon aur college mein admission lena chahta hoon. Scholarship mil sakti hai kya?",
            "language": "hi-IN",
        },
        "elderly": {
            "text": "Meri umra 65 saal hai. Pension ke liye koi scheme hai kya?",
            "language": "hi-IN",
        },
    }

    async def transcribe(self, scenario: str = "farmer") -> dict:
        await asyncio.sleep(0.5)  # simulate API latency
        return self.DEMO_TRANSCRIPTS.get(scenario, self.DEMO_TRANSCRIPTS["farmer"])


# ─── Mock Scheme KB ──────────────────────────────────────────────────────────
class MockSchemeRetriever:
    """Returns hardcoded scheme chunks without needing PostgreSQL."""

    SCHEMES = [
        {
            "id": "pm-kisan-001",
            "text": "PM-KISAN provides ₹6,000/year to all landholding farmer families in 3 equal installments.",
            "metadata": {
                "scheme_name": "PM-KISAN",
                "category": "farmer",
                "state": "central",
            },
            "score": 0.95,
        },
        {
            "id": "shetkari-001",
            "text": "Shetkari Sanman Yojana provides ₹6,000/year to Maharashtra farmers with 0.5-20 hectares.",
            "metadata": {
                "scheme_name": "Shetkari Sanman Yojana",
                "category": "farmer",
                "state": "maharashtra",
            },
            "score": 0.90,
        },
        {
            "id": "mis-onion-001",
            "text": "Market Intervention Scheme procures onions at MSP during price crashes to protect farmers.",
            "metadata": {
                "scheme_name": "MIS (Onion)",
                "category": "farmer",
                "state": "central",
            },
            "score": 0.82,
        },
        {
            "id": "fasal-bima-001",
            "text": "Pradhan Mantri Fasal Bima Yojana provides crop insurance with 2% premium for kharif, 1.5% for rabi.",
            "metadata": {
                "scheme_name": "PM Fasal Bima Yojana",
                "category": "farmer",
                "state": "central",
            },
            "score": 0.78,
        },
        {
            "id": "kcc-001",
            "text": "Kisan Credit Card provides short-term crop loans at 4% interest (after subsidy) up to ₹3 lakh.",
            "metadata": {
                "scheme_name": "Kisan Credit Card",
                "category": "farmer",
                "state": "central",
            },
            "score": 0.75,
        },
    ]

    async def retrieve(self, query: str, k: int = 5) -> list[dict]:
        await asyncio.sleep(0.3)  # simulate DB latency
        return self.SCHEMES[:k]


# ─── Mock TTS ────────────────────────────────────────────────────────────────
class MockTimbreTTS:
    """Simulates Timbre TTS response."""

    async def synthesize(self, text: str, language: str = "hi") -> bytes:
        await asyncio.sleep(0.4)  # simulate API latency
        # Return a short synthetic audio (1s tone)
        return generate_test_audio(duration_s=1.0, sample_rate=8000)


# ─── Main Pipeline ───────────────────────────────────────────────────────────
async def run_demo(scenario: str = "farmer", use_real_stt: bool = False):
    start = time.time()

    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " SCHEME FINDER LINE — MVP DEMO ".center(58) + "║")
    print("║" + f" Scenario: {scenario} ".center(58) + "║")
    print("╚" + "═" * 58 + "╝")

    # ── Step 1: Generate / Load Audio ──
    print(f"\n{'─' * 60}")
    print("  [1/5] 🎤  AUDIO INPUT")
    print(f"{'─' * 60}")

    audio_pcm = generate_test_audio(duration_s=3.0, sample_rate=16000)
    sample_rate = 16000
    wav_path = Path(__file__).parent.parent / "tests" / "fixtures" / "demo_audio.wav"
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    save_test_wav(str(wav_path), audio_pcm, sample_rate)

    duration = len(audio_pcm) / (sample_rate * 2)  # 2 bytes per sample
    print(f"  ✓ Generated synthetic audio: {duration:.1f}s at {sample_rate}Hz")
    print(f"  ✓ Saved to: {wav_path}")

    # ── Step 2: Speech-to-Text ──
    print(f"\n{'─' * 60}")
    print("  [2/5] 🗣️  PRISMA STT (Speech → Text)")
    print(f"{'─' * 60}")

    if use_real_stt and os.getenv("GNANI_API_KEY"):
        print("  🔴 LIVE MODE — Calling real Prisma STT API...")
        from stt.client import PrismaSTTClient

        stt = PrismaSTTClient(api_key=os.getenv("GNANI_API_KEY"))
        try:
            result = await stt.transcribe_file(audio_pcm, sample_rate, language="auto")
            transcript = result.get("text", "(empty response)")
            detected_lang = result.get("language", "hi-IN")
            print(f"  ✓ API Response: {result}")
        except Exception as e:
            print(f"  ✗ API Error: {e}")
            print("  ⚠ Falling back to mock STT...")
            mock_stt = MockPrismaSTT()
            result = await mock_stt.transcribe(scenario)
            transcript = result["text"]
            detected_lang = result["language"]
        finally:
            await stt.close()
    else:
        if not os.getenv("GNANI_API_KEY"):
            print("  ⚠ GNANI_API_KEY not set — using mock STT")
        else:
            print("  ⚠ Mock mode — using simulated transcription")

        mock_stt = MockPrismaSTT()
        result = await mock_stt.transcribe(scenario)
        transcript = result["text"]
        detected_lang = result["language"]

    print("\n  📝 Transcript:")
    print(f'     "{transcript}"')
    print(f"  🌐 Language: {detected_lang}")

    # ── Step 3: Scheme KB Retrieval ──
    print(f"\n{'─' * 60}")
    print("  [3/5] 🔍  SCHEME KB RETRIEVAL")
    print(f"{'─' * 60}")

    retriever = MockSchemeRetriever()
    scheme_chunks = await retriever.retrieve(transcript, k=5)

    print(f"  ✓ Found {len(scheme_chunks)} matching schemes:\n")
    for i, chunk in enumerate(scheme_chunks, 1):
        name = chunk["metadata"].get("scheme_name", "Unknown")
        state = chunk["metadata"].get("state", "?")
        score = chunk["score"]
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"     {i}. {name:<30s} [{state:^12s}]  {bar} {score:.0%}")

    # ── Step 4: Evon LLM Response ──
    print(f"\n{'─' * 60}")
    print("  [4/5] 🤖  EVON LLM (Intelligence Layer)")
    print(f"{'─' * 60}")

    if not os.getenv("EVON_API_KEY"):
        print("  ⚠ EVON_API_KEY not set — using mock response")

    response = mock_evon_response(transcript, scheme_chunks, detected_lang)

    print("\n  💬 Spoken Response:")
    print(f'     "{response["spoken_response"]}"')
    print(f"\n  📋 Matched Schemes: {len(response['schemes'])}")
    for i, scheme in enumerate(response["schemes"], 1):
        print(f"     {i}. {scheme['name']} (confidence: {scheme['confidence']:.0%})")
        print(f"        Benefits: {scheme['benefits']}")
        print(f"        Docs needed: {', '.join(scheme['documents_required'])}")
        print(f"        Helpline: {scheme['helpline']}")

    if response.get("missing_documents"):
        print("\n  ⚠ Missing Documents:")
        for doc in response["missing_documents"]:
            print(f"     • {doc}")

    if response.get("next_steps"):
        print("\n  ▶ Next Steps:")
        for step in response["next_steps"]:
            print(f"     → {step}")

    # ── Step 5: TTS ──
    print(f"\n{'─' * 60}")
    print("  [5/5] 🔊  TIMBRE TTS (Text → Speech)")
    print(f"{'─' * 60}")

    output_path = Path(__file__).parent.parent / "output_response.wav"

    if use_real_stt and os.getenv("GNANI_API_KEY"):
        print("  🔴 LIVE MODE — Calling real Timbre TTS API...")
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from tts.tts_client import TimbreTTSClient

        tts_client = TimbreTTSClient(api_key=os.getenv("GNANI_API_KEY"))
        try:
            audio_out = await tts_client.synthesize(
                response["spoken_response"], language=detected_lang[:2]
            )
            with open(str(output_path), "wb") as f:
                f.write(audio_out)
            print(f"  ✓ Real TTS audio saved: {output_path}")
        except Exception as e:
            # Try to get response body for debugging
            err_msg = str(e)
            if hasattr(e, "__cause__") and hasattr(e.__cause__, "response"):
                try:
                    err_msg += f"\n     Response: {e.__cause__.response.text}"
                except Exception:
                    pass
            print(f"  ✗ TTS API Error: {err_msg}")
            print("  ⚠ Falling back to mock TTS...")
            tts = MockTimbreTTS()
            audio_out = await tts.synthesize(
                response["spoken_response"], language=detected_lang[:2]
            )
            save_test_wav(str(output_path), audio_out, sample_rate=8000)
            print(f"  ✓ Mock audio saved: {output_path}")
        finally:
            await tts_client.close()
    else:
        tts = MockTimbreTTS()
        audio_out = await tts.synthesize(response["spoken_response"], language=detected_lang[:2])
        save_test_wav(str(output_path), audio_out, sample_rate=8000)
        print("  ⚠ Using mock TTS (set GNANI_API_KEY for real)")
        print(f"  ✓ Audio saved: {output_path}")

    elapsed = time.time() - start

    # ── Summary ──
    print(f"\n{'═' * 60}")
    print(f"  ✅  MVP PIPELINE COMPLETE  ({elapsed:.1f}s)")
    print(f"{'═' * 60}")
    print()
    print("  🎤 Input:     3.0s synthetic audio (Hindi farmer scenario)")
    print(f"  📝 Transcript: {transcript[:60]}...")
    print(f"  🤖 Response:   {response['spoken_response'][:60]}...")
    print(f"  📋 Schemes:    {len(response['schemes'])} matched")
    print(f"  🔊 Output:     {output_path}")
    print()
    print(f"{'─' * 60}")
    print("  To test with REAL APIs:")
    print("  1. Add GNANI_API_KEY to .env")
    print("  2. Run: python scripts/demo_run.py --real-stt")
    print("  3. Add EVON_API_KEY when ready for full pipeline")
    print(f"{'─' * 60}")
    print()


async def run_all_scenarios(use_real_stt: bool = False):
    """Run all demo scenarios."""
    for scenario in ["farmer", "student", "elderly"]:
        await run_demo(scenario, use_real_stt=use_real_stt)
        print("\n" + "🔄" * 30 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scheme Finder Line MVP Demo")
    parser.add_argument(
        "--scenario",
        default="farmer",
        choices=["farmer", "student", "elderly", "all"],
        help="Demo scenario to run",
    )
    parser.add_argument(
        "--real-stt",
        action="store_true",
        help="Use real Prisma STT & Timbre TTS APIs (requires GNANI_API_KEY)",
    )
    args = parser.parse_args()

    if args.scenario == "all":
        asyncio.run(run_all_scenarios(use_real_stt=args.real_stt))
    else:
        asyncio.run(run_demo(args.scenario, use_real_stt=args.real_stt))
