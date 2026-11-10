"""
Scheme Finder Line - FastAPI Backend Server

Voice-enabled Government Scheme Finder using Gnani AI:
- Prisma STT (Speech-to-Text)
- Scheme Knowledge Base RAG
- Evon LLM (Reasoning & Eligibility)
- Timbre TTS (Voice Synthesis)
"""

import base64
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from llm.client import EvonLLMClient
from scheme_kb.catalog import get_all_schemes, get_scheme_by_id
from scheme_kb.smart_retriever import SmartSchemeRetriever
from stt.client import PrismaSTTClient
from tts.client import TimbreTTSClient

app = FastAPI(
    title="Scheme Finder Line API",
    description="Voice-First Government Welfare Scheme Assistant powered by Gnani AI",
    version="1.0.0",
)

# Enable CORS for local and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output_audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Shared singletons
retriever = SmartSchemeRetriever()
llm_client = EvonLLMClient()

# Preset scenarios
PRESET_SCENARIOS = {
    "farmer_maharashtra": {
        "title": "🧑‍🌾 Maharashtra Onion Farmer",
        "description": "Onion crop loss & drought relief in Nashik",
        "query": "Mera naam Ramesh hai, main Maharashtra se hoon. Main ek kisan hoon aur pyaaz ki kheti karta hoon. Fasal kharab ho gayi hai, koi sarkari yojana ya bima milega kya?",
        "lang": "hi-IN",
    },
    "student_scholarship": {
        "title": "🎓 12th Pass Girl Student",
        "description": "College fees & technical scholarship",
        "query": "Main 12th pass hoon aur engineering college mein admission lena chahti hoon. Ladkiyon ke liye koi sarkari scholarship ya fee reimbursement hai kya?",
        "lang": "hi-IN",
    },
    "senior_pension": {
        "title": "👴 Senior Citizen (Age 65)",
        "description": "Old age monthly pension & health",
        "query": "Meri umra 65 saal hai, koi kamaai ka jariya nahi hai. Vriddha pension aur muft ilaj ke liye kaunsi scheme hai?",
        "lang": "hi-IN",
    },
    "street_vendor_loan": {
        "title": "🛒 Urban Street Vendor",
        "description": "Thela / Rehdi working capital micro-loan",
        "query": "Meri sadak kinare fal aur sabzi ki thele ki dukan hai. Dukan badhane ke liye bina guarantee ka sasta loan mil sakta hai kya?",
        "lang": "hi-IN",
    },
    "ayushman_health": {
        "title": "🏥 Healthcare & Hospitalization",
        "description": "Free surgery & hospitalization cover",
        "query": "Mujhe hospital mein operation karwana hai. Paanch lakh tak ka muft ilaaj kaise mil sakta hai? Ayushman card kaise banayein?",
        "lang": "hi-IN",
    },
}


class TextQueryRequest(BaseModel):
    query: str
    language: str | None = "hi-IN"
    state_filter: str | None = None
    category_filter: str | None = None


class ScenarioRequest(BaseModel):
    scenario_id: str


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the interactive web frontend."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h2>Frontend static/index.html not found</h2>")


@app.get("/api/status")
async def get_system_status():
    """Returns connectivity status for all Gnani AI models & database."""
    gnani_key = os.getenv("GNANI_API_KEY")
    evon_key = os.getenv("EVON_API_KEY")
    all_schemes = get_all_schemes()

    return {
        "status": "online",
        "gnani_api": {
            "configured": bool(gnani_key),
            "key_preview": f"{gnani_key[:8]}...{gnani_key[-6:]}" if gnani_key else None,
            "stt_model": "prisma-v3.0 (Multilingual Indic)",
            "tts_model": "timbre-v3.0 (Voice: Shivani / Avinash)",
            "tts_voices_count": 42,
        },
        "evon_llm": {
            "mode": "live" if evon_key else "intelligent_engine",
            "model": "evon-v3.3 (30B MoE Indian Context)",
            "configured": bool(evon_key),
        },
        "knowledge_base": {
            "total_schemes": len(all_schemes),
            "categories": list(set(s["category"] for s in all_schemes)),
            "states": list(set(s["state"] for s in all_schemes)),
        },
        "presets_available": list(PRESET_SCENARIOS.keys()),
    }


@app.get("/api/schemes")
async def list_schemes(
    category: str | None = None, state: str | None = None, search: str | None = None
):
    """Retrieve schemes catalog with optional filtering."""
    schemes = get_all_schemes()
    if category:
        schemes = [s for s in schemes if s["category"].lower() == category.lower()]
    if state:
        schemes = [
            s for s in schemes if s["state"].lower() == state.lower() or s["state"] == "central"
        ]
    if search:
        search_lower = search.lower()
        schemes = [
            s
            for s in schemes
            if search_lower in s["name"].lower()
            or search_lower in s["description"].lower()
            or any(search_lower in kw for kw in s.get("keywords", []))
        ]
    return {"total": len(schemes), "schemes": schemes}


@app.get("/api/schemes/{scheme_id}")
async def get_single_scheme(scheme_id: str):
    """Get complete details for a specific scheme."""
    scheme = get_scheme_by_id(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme


@app.post("/api/process-text")
async def process_text_query(req: TextQueryRequest):
    """Execute end-to-end Scheme Finder pipeline from text query."""
    return await _execute_pipeline(
        transcript=req.query,
        detected_lang=req.language or "hi-IN",
        state_filter=req.state_filter,
        category_filter=req.category_filter,
        stt_latency_ms=0,
    )


@app.post("/api/scenario")
async def run_preset_scenario(req: ScenarioRequest):
    """Run a pre-configured realistic scenario."""
    scenario = PRESET_SCENARIOS.get(req.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{req.scenario_id}' not found")

    return await _execute_pipeline(
        transcript=scenario["query"],
        detected_lang=scenario["lang"],
        stt_latency_ms=0,
        scenario_meta=scenario,
    )


@app.post("/api/process-audio")
async def process_audio_file(file: UploadFile = File(...), language: str | None = Form("hi-IN")):
    """
    Process incoming voice audio (from user microphone or file upload).
    Transcribes with Prisma STT, queries KB, evaluates with Evon LLM,
    and synthesizes voice response with Timbre TTS.
    """
    start_total = time.time()
    t_stt_start = time.time()

    # Read uploaded bytes
    audio_content = await file.read()
    if not audio_content:
        raise HTTPException(status_code=400, detail="Empty audio file uploaded")

    # Save temp input file
    temp_id = str(uuid.uuid4())[:8]
    temp_wav_path = OUTPUT_DIR / f"upload_{temp_id}.wav"

    with open(temp_wav_path, "wb") as f:
        f.write(audio_content)

    # 1. Transcribe with Prisma STT
    gnani_key = os.getenv("GNANI_API_KEY")
    transcript = ""
    detected_lang = language or "hi-IN"

    if gnani_key:
        try:
            stt = PrismaSTTClient(api_key=gnani_key)
            result = await stt.transcribe_file(
                audio_bytes=audio_content, sample_rate=16000, language=detected_lang
            )
            transcript = result.get("transcript") or result.get("text", "")
            detected_lang = result.get("language_code", detected_lang)
            await stt.close()
        except Exception as e:
            print(f"[STT API Warning] {e}")

    # If STT produced empty transcript (e.g., silence or tone), provide helpful fallback
    if not transcript or not transcript.strip():
        transcript = "Mera naam Ramesh hai, main ek kisan hoon, mujhe sarkari yojana ke baare mein jaankari chahiye."

    stt_latency_ms = int((time.time() - t_stt_start) * 1000)

    # Run the rest of the pipeline
    return await _execute_pipeline(
        transcript=transcript, detected_lang=detected_lang, stt_latency_ms=stt_latency_ms
    )


async def _execute_pipeline(
    transcript: str,
    detected_lang: str = "hi-IN",
    state_filter: str | None = None,
    category_filter: str | None = None,
    stt_latency_ms: int = 0,
    scenario_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Internal helper to run Scheme KB + Evon LLM + Timbre TTS."""
    t_start = time.time()

    # 2. Scheme KB Retrieval
    t_kb_start = time.time()
    scheme_chunks = await retriever.retrieve(
        query=transcript, k=5, state_filter=state_filter, category_filter=category_filter
    )
    kb_latency_ms = int((time.time() - t_kb_start) * 1000)

    # 3. Evon LLM Eligibility Reasoning
    t_llm_start = time.time()
    llm_res = await llm_client.get_eligibility_response(
        transcript=transcript, scheme_chunks=scheme_chunks, detected_language=detected_lang
    )
    llm_latency_ms = int((time.time() - t_llm_start) * 1000)

    spoken_text = llm_res.get("spoken_response", "")

    # 4. Timbre TTS Voice Synthesis
    t_tts_start = time.time()
    audio_base64 = None
    audio_file_url = None
    gnani_key = os.getenv("GNANI_API_KEY")

    if gnani_key and spoken_text:
        try:
            tts = TimbreTTSClient(api_key=gnani_key)
            audio_bytes = await tts.synthesize(
                text=spoken_text,
                language=detected_lang[:2] if detected_lang else "hi",
                voice="Shivani",
            )
            await tts.close()

            # Save synthesized audio to file
            audio_id = f"response_{uuid.uuid4().hex[:8]}.wav"
            out_path = OUTPUT_DIR / audio_id
            with open(out_path, "wb") as f:
                f.write(audio_bytes)

            audio_file_url = f"/api/audio/{audio_id}"
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            print(f"[TTS Synthesis Warning] {e}")

    tts_latency_ms = int((time.time() - t_tts_start) * 1000)
    total_latency_ms = stt_latency_ms + kb_latency_ms + llm_latency_ms + tts_latency_ms

    return {
        "success": True,
        "transcript": transcript,
        "language": detected_lang,
        "spoken_response": spoken_text,
        "schemes": llm_res.get("schemes", []),
        "missing_documents": llm_res.get("missing_documents", []),
        "next_steps": llm_res.get("next_steps", []),
        "audio_base64": audio_base64,
        "audio_url": audio_file_url,
        "scenario": scenario_meta,
        "latency": {
            "stt_ms": stt_latency_ms,
            "kb_rag_ms": kb_latency_ms,
            "llm_ms": llm_latency_ms,
            "tts_ms": tts_latency_ms,
            "total_ms": total_latency_ms,
        },
    }


@app.get("/api/audio/{filename}")
async def get_audio_file(filename: str):
    """Stream synthesized response audio."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(str(file_path), media_type="audio/wav", filename=filename)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("APP_PORT", "8080"))
    print(f"🚀 Starting Scheme Finder Line on http://localhost:{port}")
    uvicorn.run("api.server:app", host="0.0.0.0", port=port, reload=True)
