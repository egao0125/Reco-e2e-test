# Skill: Implement Scoring Pipeline

## Purpose
Implement the 3-axis auto-scoring system for call evaluation.

## The 3 Axes

### Hallucination (3 Types)
- **Type 1 (STT):** Re-transcribe recording with high-accuracy STT, compare to production STT output
- **Type 2 (LLM):** LLM-as-judge comparing AI utterances against flow definition + CRM data
- **Type 3 (TTS):** Re-transcribe TTS output audio, compare to LLM text output

### Latency
- Extract timestamps from Reco's latency log
- Compute per-stage and total perceived latency
- Requires Reco-side instrumentation (5 timestamps)

### Naturalness
- LLM-as-judge scoring 1-10 with 5-item breakdown
- Keigo accuracy (3pts), tempo (2pts), aizuchi (2pts), objective (2pts), impression (1pt)

## Files to Implement
- `scoring/score_call.py` — Entry point (stubs exist, implement TODO sections)
- `scoring/hallucination_judge.py` — 3 Type detection (stub exists)
- `scoring/naturalness_judge.py` — 5-item scoring (stub exists)
- `scoring/latency_extractor.py` — Timestamp parsing (stub exists)

## Dependencies
- `anthropic` Python SDK (for LLM-as-judge calls)
- `deepgram-sdk` (for re-transcription in Type 1/3 detection)

## Output Format
All scores appended to `scores/scores.jsonl`, one JSON object per line per call.
