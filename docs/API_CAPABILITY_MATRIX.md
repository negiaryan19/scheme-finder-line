# Verified API Capability Matrix

> **Sources:** [Gnani API Intro](https://docs.gnani.ai/api/introduction/introduction), [Prisma v3](https://www.gnani.ai/resources/prisma-v3), [Timbre TTS](https://www.gnani.ai/text-to-speech), [Gnani API Service](https://gnani-ai.github.io/API-service/), [Twilio Media Streams](https://www.twilio.com/docs/voice/media-streams), [Hugging Face gnani-ai/gnani](https://huggingface.co/gnani-ai/gnani)
>
> **Last verified:** 2026-11-01
> **Marking:** ✅ Verified | ❌ Not supported | ❓ UNKNOWN (not found in official docs)

---

## Gnani Prisma STT (v2.5 / v3.0)

| Capability | Status | Details |
|------------|--------|---------|
| **Access Method** | ✅ Hosted API | `GNANI_API_KEY` header; base URL `https://api.vachana.ai` |
| **Authentication** | ✅ API Key | `X-API-Key-ID: <key>` |
| **REST Endpoint** | ✅ | File upload ≤30s; `model=prisma-v3.0` for multilingual |
| **WebSocket Streaming** | ✅ | Real-time, interim results, <200ms P95 |
| **Batch/Async** | ✅ | Long/multi-file jobs |
| **Supported Languages** | ✅ 10 + English | hi, bn, ta, te, mr, gu, kn, ml, pa, as, en |
| **Language Codes** | ✅ | `hi-IN`, `kn-IN`, `en-IN`, etc. (BCP-47) |
| **Auto Language Detection** | ✅ | 95% accuracy on 3+ sec audio; Prisma v3 default |
| **Code-Mixed Support** | ✅ | Mode: `codemix` — English stays English, numbers spelled out |
| **Output Modes** | ✅ 4 modes | `verbatim`, `transcribe`, `codemix`, `transliterate` |
| **Keyterm Prompting** | ✅ | Up to 200 terms per request |
| **Audio Formats** | ✅ | WAV, MP3, OGG, FLAC, AAC, M4A |
| **Sample Rates** | ✅ | 8 kHz (telephony), 16 kHz (VoIP), 48 kHz (studio) |
| **Auto-Punctuation** | ✅ | On supported endpoints |
| **Text Normalization** | ✅ | On supported endpoints |
| **Rate Limits** | ❓ UNKNOWN | Not in public docs |
| **Pricing/Credits** | ❓ UNKNOWN | 5,000 credits provided for internship; consumption rate not public |
| **SDKs** | ✅ Pipecat, LiveKit | `pip install pipecat-ai[gnani]` |
| **gRPC Endpoint** | ✅ (legacy?) | `asr.gnani.ai:443` with token/accesskey/cert.pem |

---

## Gnani Timbre TTS (v2.5)

| Capability | Status | Details |
|------------|--------|---------|
| **Access Method** | ✅ Hosted API | Same `GNANI_API_KEY` |
| **REST (Sync)** | ✅ | Immediate audio return |
| **SSE Streaming** | ✅ | Progressive audio chunks |
| **WebSocket Realtime** | ✅ | Bidirectional, <200ms to first byte |
| **Voices** | ✅ 42 voices | Male/female across 10 languages |
| **Language Codes** | ✅ | `hi`, `bn`, `ta`, `te`, `mr`, `gu`, `kn`, `ml`, `pa`, `en-IN` |
| **SSML Support** | ✅ | "Fine-grained control" per docs |
| **Output Sample Rates** | ✅ | 8 kHz – 48 kHz (telephony to studio) |
| **μ-law Output** | ❓ UNKNOWN | 8 kHz supported; μ-law not explicitly named |
| **Indian Numeral Formatting** | ✅ | Rupees, lakh, crore, dates, account numbers normalized |
| **Code-Mixed TTS** | ❓ UNKNOWN | Not explicitly documented |
| **Voice Cloning** | ✅ | Embeddings → REST/SSE/WebSocket inference |
| **Rate Limits** | ❓ UNKNOWN | Not in public docs |
| **Pricing/Credits** | ❓ UNKNOWN | Same credit pool as STT? |

---

## Gnani Evon LLM (v3.3)

| Capability | Status | Details |
|------------|--------|---------|
| **Access Method** | ❓ UNKNOWN | Not in speech API docs; possibly separate API or self-host |
| **Model** | ❓ UNKNOWN | 30B MoE, 128K context, 11 languages native (per internship page) |
| **API Endpoint** | ❓ UNKNOWN | Not found in Gnani speech API docs |
| **Authentication** | ❓ UNKNOWN | Likely same `GNANI_API_KEY` or separate |
| **Languages** | ❓ UNKNOWN | 11 Indian languages per internship page |
| **JSON Mode** | ❓ UNKNOWN | Not documented |
| **Function/Tool Calling** | ❓ UNKNOWN | Not documented |
| **Context Window** | ❓ UNKNOWN | 128K per internship page |
| **Self-Host Option** | ❓ UNKNOWN | Apache 2.0 weights on HF per internship page |
| **Hugging Face Repo** | ❓ UNKNOWN | `gnani-ai/gnani` is speech model; Evon repo not found |
| **Rate Limits** | ❓ UNKNOWN | — |
| **Pricing** | ❓ UNKNOWN | — |

> **Action Required:** Check Gnani API dashboard after registration, or contact `speechstack@gnani.ai` / `hello@gnani.ai` for Evon access details.

---

## Twilio Media Streams

| Capability | Status | Details |
|------------|--------|---------|
| **WebSocket Protocol** | ✅ | Secure WSS on port 443 |
| **Audio Format** | ✅ | μ-law 8 kHz (telephony standard) |
| **Bidirectional Streaming** | ✅ | `<Connect><Stream>` TwiML |
| **Unidirectional** | ✅ | `<Start><Stream>` TwiML (up to 4 tracks) |
| **Events** | ✅ | `start`, `media` (audio payload), `stop`, `dtmf` |
| **TwiML Verbs** | ✅ | `<Connect><Stream url="wss://..." track="both_tracks" />` |
| **Max Streams/Call** | ✅ | 1 bidirectional, 4 unidirectional |
| **Regional Endpoints** | ✅ | US1 (default), IE1, AU1 |
| **Authentication** | ✅ | Validate `X-Twilio-Signature` header |
| **Pricing** | ❓ UNKNOWN | Check Twilio Voice pricing page |
| **Media Stream Events** | ✅ | Start → Media* → Stop |

---

## Integration Compatibility Matrix

| From \ To | Prisma STT | Timbre TTS | Evon LLM | Twilio Media Streams |
|-----------|------------|------------|----------|---------------------|
| **Twilio (μ-law 8kHz)** | ✅ Native 8kHz support | ✅ Outputs 8kHz | N/A | ✅ Native |
| **Prisma STT → Evon** | — | — | ❓ UNKNOWN | — |
| **Evon → Timbre TTS** | — | — | ❓ UNKNOWN | — |
| **Timbre → Twilio** | — | ✅ μ-law 8kHz needed | — | ✅ WebSocket send |

---

## Critical Gaps to Resolve Before Coding

1. **Evon LLM API** — No public documentation found. Must obtain from Gnani after registration.
2. **Credit Consumption Rates** — 5,000 credits = how many STT/TTS minutes?
3. **Rate Limits** — Concurrent streams, requests/sec for all three models.
4. **μ-law Output from Timbre** — Confirm `sample_rate: 8000` + `encoding: mulaw` works.
5. **Code-Mixed TTS** — Single voice handling Hinglish/Tanglish naturally?
6. **Evon JSON/Structured Output** — Required for scheme eligibility JSON response.