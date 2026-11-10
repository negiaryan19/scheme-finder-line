#!/usr/bin/env python3
"""
Recording-based MVP Test Script

Usage:
    python scripts/test_mvp.py --audio tests/fixtures/sample_hindi.wav --lang hi-IN

Requirements:
    - GNANI_API_KEY in .env
    - EVON_API_KEY + EVON_API_BASE_URL in .env (or mock)
    - Scheme KB populated (run scripts/ingest_schemes.py first)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from llm.client import EvonLLMClient
from scheme_kb.retriever import SchemeRetriever
from stt.client import PrismaSTTClient
from tts.client import TimbreTTSClient
from utils.audio import load_audio_file, save_audio_file


async def main():
    parser = argparse.ArgumentParser(description="Scheme Finder MVP Test")
    parser.add_argument("--audio", required=True, help="Path to input audio file (WAV/MP3)")
    parser.add_argument("--lang", default="auto", help="Language code (hi-IN, mr-IN, auto)")
    parser.add_argument("--output", default="output_response.wav", help="Output audio file")
    parser.add_argument("--mock-evon", action="store_true", help="Use mock Evon response")
    args = parser.parse_args()

    print("=" * 60)
    print("SCHEME FINDER LINE - MVP TEST")
    print("=" * 60)

    # 1. Load Audio
    print(f"\n[1/5] Loading audio: {args.audio}")
    audio_data, sample_rate = load_audio_file(args.audio)
    print(f"    Duration: {len(audio_data) / sample_rate:.1f}s, Sample Rate: {sample_rate}Hz")

    # 2. Prisma STT
    print("\n[2/5] Transcribing with Prisma STT...")
    stt = PrismaSTTClient(api_key=os.getenv("GNANI_API_KEY"))
    transcript_result = await stt.transcribe_file(audio_data, sample_rate, language=args.lang)
    transcript = transcript_result["text"]
    detected_lang = transcript_result.get("language", "hi-IN")
    print(f"    Transcript: {transcript}")
    print(f"    Detected Language: {detected_lang}")

    # 3. Scheme KB Retrieval
    print("\n[3/5] Retrieving relevant schemes...")
    retriever = SchemeRetriever()
    scheme_chunks = await retriever.retrieve(transcript, k=5)
    print(f"    Found {len(scheme_chunks)} relevant schemes")
    for i, chunk in enumerate(scheme_chunks[:3], 1):
        print(
            f"      {i}. {chunk['metadata'].get('scheme_name', 'Unknown')} (score: {chunk['score']:.3f})"
        )

    # 4. Evon LLM
    print("\n[4/5] Generating response with Evon LLM...")
    if args.mock_evon or not os.getenv("EVON_API_KEY"):
        print("    ⚠️  Using MOCK Evon response (set EVON_API_KEY for real)")
        from llm.mock import mock_evon_response

        response = mock_evon_response(transcript, scheme_chunks, detected_lang)
    else:
        llm = EvonLLMClient(
            api_key=os.getenv("EVON_API_KEY"), base_url=os.getenv("EVON_API_BASE_URL")
        )
        response = await llm.get_eligibility_response(transcript, scheme_chunks, detected_lang)

    print(f"    Response: {response['spoken_response'][:100]}...")
    print(f"    Schemes Found: {len(response['schemes'])}")

    # 5. Timbre TTS
    print("\n[5/5] Synthesizing speech with Timbre TTS...")
    tts = TimbreTTSClient(api_key=os.getenv("GNANI_API_KEY"))
    audio_output = await tts.synthesize(response["spoken_response"], language=detected_lang)
    save_audio_file(audio_output, args.output, sample_rate=8000)  # Telephony rate
    print(f"    Saved to: {args.output}")

    print("\n" + "=" * 60)
    print("MVP TEST COMPLETE")
    print("=" * 60)
    print(f"\nTranscript: {transcript}")
    print(f"Response:   {response['spoken_response']}")
    print(f"Audio:      {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
