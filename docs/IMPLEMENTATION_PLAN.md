# Day-by-Day Implementation Plan through November 10, 2026

> **Build Window:** 41 days (Oct 1 – Nov 10, 2026)
> **Today:** Nov 1, 2026 — **10 days remaining**
> **Strategy:** Compress to recording-based MVP first; defer Twilio to post-internship demo

---

## Adjusted Timeline (10 Days Remaining)

| Day | Date | Focus | Deliverable |
|-----|------|-------|-------------|
| **1** | Nov 1 | **Setup & Credentials** | Gnani API key, repo init, deps installed, `.env` populated |
| **2** | Nov 2 | **Prisma STT Integration** | `src/stt/client.py` — file upload + streaming transcript (Hindi/English) |
| **3** | Nov 3 | **Timbre TTS Integration** | `src/tts/client.py` — text → streaming audio (Hindi/Marathi) |
| **4** | Nov 4 | **Evon LLM Access** | Obtain Evon endpoint/key from Gnani; `src/llm/client.py` — chat completion |
| **5** | Nov 5 | **Scheme KB Ingestion** | Scrape 20 central + 3 state schemes → embed → pgvector |
| **6** | Nov 6 | **RAG Pipeline** | Query → retrieve → Evon prompt → structured JSON response |
| **7** | Nov 7 | **End-to-End MVP** | `scripts/test_mvp.py` — audio file → transcript → response → audio |
| **8** | Nov 8 | **Multilingual & Code-Mixed** | Add Gujarati, Kannada, Bengali; test Hinglish/Tanglish |
| **9** | Nov 9 | **Polish & Demo Video** | Record demo calls, edit video, write explanation |
| **10** | Nov 10 | **Submission** | Post LinkedIn/X with #GnaniAI #GreatIndianAIInternshipChallenge |

---

## Original 41-Day Plan (Reference)

| Week | Days | Focus | Key Deliverable |
|------|------|-------|-----------------|
| **W1** | Oct 1-7 | Setup, Prisma STT, Telephony Gateway | Twilio Media Streams ↔ FastAPI bridge |
| **W2** | Oct 8-14 | Timbre TTS, Evon LLM, Scheme KB | 55 schemes ingested, RAG working |
| **W3** | Oct 15-21 | End-to-End Flow, Multilingual | Full call: greeting → profile → query → response → SMS |
| **W4** | Oct 22-28 | Code-Mixed, Noise, Latency | <3s end-to-end, 5 languages |
| **W5** | Oct 29 - Nov 4 | Error Handling, WhatsApp, Analytics | Production-grade fallback, logging |
| **W6** | Nov 5-10 | Demo Video, Submission | Video + posts + written explanation |

---

## Daily Checklist Template

```markdown
## Day X - YYYY-MM-DD
- [ ] Morning: Standup (15 min) - what did I do, what's next, blockers
- [ ] Core Task: [specific deliverable]
- [ ] Test: [specific test case]
- [ ] Commit: `git add -A && git commit -m "feat: <description>"`
- [ ] Evening: Push to GitHub, update progress log
```

---

## Critical Path Items (Must Not Slip)

1. **Day 1-2:** Gnani API key + Prisma STT working on Hindi audio file
2. **Day 4:** Evon LLM access — **single biggest risk** (no public docs)
3. **Day 6:** RAG pipeline producing valid JSON from Evon
4. **Day 7:** Full MVP running on recorded audio
5. **Day 9:** Demo video recorded and edited

---

## Fallback Plan (If Evon API Unavailable)

| Scenario | Mitigation |
|----------|------------|
| Evon API not ready by Day 4 | Use `gnani-ai/gnani` on HF as local LLM (quantized 4-bit) via `llama.cpp` or `vLLM` |
| Evon requires separate approval | Build demo with **mock Evon** returning canned scheme responses; show Prisma→Timbre pipeline working |
| No API access at all | Pivot to **Prisma + Timbre only** demo: "Voice Echo Bot with Indian Language Detection" — still uses 2/3 models |

---

## Time Budget (10 Days × 10 hrs = 100 hrs)

| Activity | Hours | % |
|----------|-------|---|
| Core Pipeline (STT→LLM→TTS) | 35 | 35% |
| Scheme KB & RAG | 20 | 20% |
| Multilingual Testing | 15 | 15% |
| Demo Video & Docs | 15 | 15% |
| Buffer / Debugging | 15 | 15% |
| **Total** | **100** | **100%** |