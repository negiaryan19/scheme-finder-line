# Exact Commands to Run First End-to-End Test

## Prerequisites (One-time Setup)

```bash
# 1. Navigate to project
cd /Users/aryannegi/scheme-finder-line

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add:
#   GNANI_API_KEY=your_key_from_gnani_dashboard
#   DATABASE_URL=postgresql://user:pass@localhost:5432/scheme_finder
#   (EVON_API_KEY and EVON_API_BASE_URL optional - will use mock if not set)

# 5. Start PostgreSQL with pgvector (if not running)
# Option A: Docker
docker run -d --name pgvector \
  -e POSTGRES_DB=scheme_finder \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  pgvector/pgvector:pg16

# Option B: Local PostgreSQL with pgvector extension
# CREATE EXTENSION vector;

# 6. Start Redis (for session cache)
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

## Test 1: Prisma STT Only (File Transcription)

```bash
# Create a test Hindi audio file first (or use existing)
# Option A: Record using system tools
# Option B: Generate with Timbre TTS (see Test 2)

# Run transcription
python -c "
import asyncio
from src.stt.client import PrismaSTTClient
from src.utils.audio import load_audio_file
import os
from dotenv import load_dotenv
load_dotenv()

async def test():
    client = PrismaSTTClient(os.getenv('GNANI_API_KEY'))
    audio, sr = load_audio_file('tests/fixtures/sample_hindi.wav')
    result = await client.transcribe_file(audio, sr, language='hi-IN')
    print('Transcript:', result.get('text'))
    print('Language:', result.get('language'))
    await client.close()

asyncio.run(test())
"
```

## Test 2: Timbre TTS Only (Synthesis)

```bash
python -c "
import asyncio
from src.tts.tts_client import TimbreTTSClient
import os
from dotenv import load_dotenv
load_dotenv()

async def test():
    client = TimbreTTSClient(os.getenv('GNANI_API_KEY'))
    audio = await client.synthesize(
        'Namaste! Main aapki government schemes dhoondhne mein madad karunga.',
        language='hi',
        sample_rate=8000,
        encoding='wav'
    )
    with open('test_output.wav', 'wb') as f:
        f.write(audio)
    print('Saved test_output.wav')
    await client.close()

asyncio.run(test())
"
```

## Test 3: Scheme KB Ingestion

```bash
# Requires DATABASE_URL in .env
python scripts/ingest_schemes.py
```

## Test 4: Full MVP Pipeline (Recording-based)

```bash
# 1. Prepare a test audio file (Hindi/Hinglish)
#    Record yourself asking: "Main Maharashtra ke kisan hoon, 2 acre pyaaz ugata hoon"
#    Save as tests/fixtures/sample_hindi.wav

# 2. Run full pipeline (uses mock Evon if EVON_API_KEY not set)
python scripts/test_mvp.py --audio tests/fixtures/sample_hindi.wav --lang hi-IN

# 3. With mock Evon explicitly
python scripts/test_mvp.py --audio tests/fixtures/sample_hindi.wav --lang hi-IN --mock-evon

# 4. Specify output file
python scripts/test_mvp.py --audio tests/fixtures/sample_hindi.wav --output my_response.wav
```

## Test 5: Verify Scheme Retrieval

```bash
python -c "
import asyncio
from src.scheme_kb.retriever import SchemeRetriever
import os
from dotenv import load_dotenv
load_dotenv()

async def test():
    retriever = SchemeRetriever()
    results = await retriever.retrieve('Main Maharashtra ke kisan hoon', k=3)
    for r in results:
        print(f'{r.metadata.get(\"scheme_name\")}: {r.score:.3f}')
    await retriever.close()

asyncio.run(test())
"
```

## Expected Output (Successful MVP Run)

```
============================================================
SCHEME FINDER LINE - MVP TEST
============================================================

[1/5] Loading audio: tests/fixtures/sample_hindi.wav
    Duration: 4.2s, Sample Rate: 16000Hz

[2/5] Transcribing with Prisma STT...
    Transcript: Main Maharashtra ke kisan hoon, do acre pyaaz ugata hoon
    Detected Language: hi-IN

[3/5] Retrieving relevant schemes...
    Found 3 relevant schemes
      1. PM-KISAN (score: 0.923)
      2. Shetkari Sanman Yojana (score: 0.887)
      3. Market Intervention Scheme (Onion) (score: 0.756)

[4/5] Generating response with Evon LLM...
    Response: Namaste! Aap PM-KISAN ke liye eligible hain — saal ke 6 hazar rupaye...
    Schemes Found: 3

[5/5] Synthesizing speech with Timbre TTS...
    Saved to: output_response.wav

============================================================
MVP TEST COMPLETE
============================================================

Transcript: Main Maharashtra ke kisan hoon, do acre pyaaz ugata hoon
Response:   Namaste! Aap PM-KISAN ke liye eligible hain — saal ke 6 hazar rupaye...
Audio:      output_response.wav
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'src'` | Run from project root: `cd /Users/aryannegi/scheme-finder-line` |
| `GNANI_API_KEY not set` | Add to `.env` file |
| `Connection refused` (PostgreSQL) | Start Docker container: `docker start pgvector` |
| `pgvector extension not found` | Run `CREATE EXTENSION vector;` in PostgreSQL |
| `EVON_API_KEY not set` | Use `--mock-evon` flag or add key to `.env` |
| `Audio file not found` | Create `tests/fixtures/` and add sample WAV |

## Next Steps After MVP Works

1. **Add real Evon integration** — Replace mock in `src/llm/client.py`
2. **Add Twilio Media Streams** — Implement `src/telephony/` for live calls
3. **Add WhatsApp follow-up** — Integrate Twilio WhatsApp API
4. **Load test** — Run concurrent calls to measure latency
5. **Record demo video** — Use `output_response.wav` + screen recording