# Reco E2E Test — Claude Code Context

## Project Purpose

Recoの音声パイプライン（STT → LLM → TTS）を自律的に最適化するシステム。
4つのレイヤーで構成される：

1. **Layer 1 (caller/)** — 偽顧客AIがTwilio Media Streams経由でRecoに電話をかけてE2Eテスト
2. **Layer 2 (scoring/)** — 通話を3軸（ハルシネーション/レイテンシ/自然さ）で自動採点
3. **Layer 3 (monitor/)** — 本番通話のリアルタイム監視、異常検知、Slackアラート
4. **Layer 4 (orchestrator/)** — メタエージェントがconfig変更→A/Bテスト→改善を自律実行

## Current Phase

**Phase 0: 最小テストコール**
- Caller AgentがTwilio経由でRecoに1通話かけることを確認する段階
- Recoのfull-duplex実装は `../voice-fullduplex/` にある — そのコードを参照してCaller Agentを作る

## Architecture

```
Caller Agent (caller/)        Reco (../voice-fullduplex/)
    │                              │
    │  Twilio Media Streams        │  Twilio Media Streams
    │  (WebSocket, 8kHz mulaw)     │  (WebSocket, 8kHz mulaw)
    │                              │
    └──────── Twilio ──────────────┘
                │
          録音 + ログ
                │
         Scorer (scoring/)
                │
         scores.jsonl
                │
         Orchestrator (orchestrator/)
```

## Key Files

- `DESIGN.md` — 全体設計書（必読、全てのアーキテクチャ判断はここに記載）
- `context_prompt.md` — Layer 4 メタエージェントへの指示書
- `configs/current_config.json` — パイプラインconfig（architecture セクション含む）
- `TEAM_CHECKLIST.md` — Reco本番チームへの確認事項

## 3 Goals

| 軸 | 目標 | 測定方法 |
|---|---|---|
| ハルシネーション | 0% | LLM-as-judge（3 Type: STT/LLM/TTS） |
| レイテンシ P95 | < 500ms | パイプラインタイムスタンプ |
| 自然さ | > 8/10 | LLM-as-judge（5項目内訳） |

## Hallucination 3 Types

- **Type 1 (STT):** STTが相手の発話を聞き間違える → LLMに間違ったテキストが渡る
- **Type 2 (LLM):** LLMがフロー定義/CRMデータにない情報を生成する
- **Type 3 (TTS):** TTSがLLM出力テキストを正しく読めない（日本語の読み間違い）

## Tech Stack

- **Twilio** — Media Streams (WebSocket) for telephony
- **Pipecat** — Voice pipeline orchestration framework
- **Deepgram** — STT (current production)
- **Anthropic Claude** — LLM (current production)
- **ElevenLabs** — TTS (current production)
- All 7 provider API keys available: Deepgram, Soniox, Google Cloud STT, OpenAI, Anthropic, ElevenLabs, Cartesia

## Rules

- **DESIGN.md is the source of truth** — all architectural decisions are documented there
- **1 experiment = 1 change** — never change multiple knobs simultaneously
- **Hallucination is priority #1** — any config change that increases hallucination rate is immediately rejected
- **Test volume: 1,000 calls/day** at 10 parallel
- **A/B test minimum: 400 calls per group** before making a decision
- **All experiments logged** in `experiments/experiments.tsv`

## Directory Structure

```
Reco-e2e-test/
├── CLAUDE.md                 ← You are here
├── DESIGN.md                 ← Full system design (READ THIS FIRST)
├── context_prompt.md         ← Layer 4 orchestrator instructions
├── configs/                  ← Pipeline configs
├── caller/                   ← Layer 1: Test call generation
├── scoring/                  ← Layer 2: Auto-scoring (3 axes)
├── monitor/                  ← Layer 3: Production monitoring
├── orchestrator/             ← Layer 4: Autonomous optimization
├── eval/                     ← Offline provider evaluation
├── experiments/              ← Experiment logs
└── scores/                   ← Scoring results
```

## Related Repositories

- `../voice-fullduplex/` — Reco's full-duplex voice pipeline (Pipecat + Twilio Media Streams)
- Reco main production repo (separate, do not modify from here)
