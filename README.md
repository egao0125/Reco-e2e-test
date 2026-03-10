# Reco-e2e-test

Recoの音声パイプライン（STT → LLM → TTS）を自律的に最適化するメタエージェントシステム。

## What this does

本番通話データを観察 → 3軸（ハルシネーション/レイテンシ/自然さ）で自動採点 → 問題を診断 → 設定変更を提案・実験 → A/Bテストで検証 → 改善をキープ。人間はゴールだけ定義し、何をどう変えるかはエージェントが判断する。

## Goals

| 軸 | 目標 | 現状 |
|---|---|---|
| ハルシネーション | 0% | 未計測 |
| レイテンシ P95 | < 500ms | ~1.5-2.8s |
| 自然さ | > 8/10 | 未計測 |

## Structure

```
context_prompt.md       ← メタエージェントへの指示書（全設計がここに集約）
scoring/                ← 3軸採点スクリプト
  score_call.py         ← エントリーポイント（通話ごとに実行）
  hallucination_judge.py
  naturalness_judge.py
  latency_extractor.py
configs/                ← パイプライン設定
  current_config.json   ← 本番で使用中の設定
  candidate_config.json ← A/Bテスト用の候補設定
  config_history.jsonl  ← 変更履歴
experiments/
  experiments.tsv       ← 全実験ログ
eval/
  corpus/               ← オフライン評価用テストコーパス
  offline_eval.py       ← プロバイダ切り替え時の事前評価
scores/
  scores.jsonl          ← 本番通話の採点結果
```

## Relationship to Reco

このリポジトリはRecoの本番コードとは独立。接点は2つだけ：
1. **configs/** — Reco本番が起動時にcurrent_config.jsonを読む
2. **scores/** — Reco本番の通話ログ/録音を入力として採点

## Setup Prerequisites

Reco本番側で必要な変更：
1. パイプライン内部レイテンシの計装（各ステージにタイムスタンプ追加）
2. config外部化（STT/LLM/TTS設定をJSONから読む仕組み）
3. A/Bスプリット（通話ごとにconfig_a/config_bを振り分ける分岐）

詳細は `context_prompt.md` のSection 9 (Bootstrap Sequence) を参照。

## Prior Art

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — 設計思想の元になったプロジェクト
- autoresearch/nbest-selector（12実験） — accuracy 68%→71%, regressions 0
- autoresearch/stt-params（32実験） — CER 26.9%→24.2%, Deepgram天井確認済み
