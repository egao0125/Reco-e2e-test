# Reco Autonomous Voice Pipeline Optimization System — 全体設計書

> Version: 1.0
> Date: 2026-03-10
> Author: Egao / Claude
> Status: Draft — チーム確認前

---

## 0. Executive Summary

Recoの音声パイプライン（STT → LLM → TTS）を自律的に最適化するシステムを構築する。

**4つのレイヤー:**

| Layer | 機能 | 概要 |
|-------|------|------|
| **Layer 1** | テストコール生成 | 偽顧客AIがTwilio経由でRecoに電話をかける |
| **Layer 2** | 自動採点 | 通話を3軸（ハルシネ/レイテンシ/自然さ）で自動評価 |
| **Layer 3** | 本番モニタリング | リアルタイム監視、異常検知、Slackアラート |
| **Layer 4** | 自律最適化 | メタエージェントがconfig変更→A/Bテスト→改善を自律実行 |

**3つのゴール:**

| 軸 | 目標 | 現状 |
|---|---|---|
| ハルシネーション | 0% | 未計測 |
| レイテンシ P95 | < 500ms | ~1.5-2.8s |
| 自然さ | > 8/10 | 未計測 |

**設計思想:** Karpathyのautoresearchパターン（1ファイル×1指標×自動ループ）を音声パイプライン全体に拡張。人間はゴールだけ定義し、何をどう変えるかはシステムが自律的に判断する。

---

## 1. System Architecture

### 1.1 全体構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 4: Orchestrator                         │
│                    (メタエージェント)                              │
│                                                                  │
│  OBSERVE → DIAGNOSE → HYPOTHESIZE → PLAN → TEST → EVALUATE     │
│                                                                  │
│  入力: scores.jsonl, experiments.tsv                             │
│  出力: candidate_config.json, 実験計画                            │
└──────────┬──────────────────────────────────┬────────────────────┘
           │ config変更                       │ テスト指示
           ▼                                  ▼
┌─────────────────────┐          ┌─────────────────────────┐
│ Layer 3: Monitor     │          │ Layer 1: Caller Agent   │
│                      │          │ (偽顧客AI)               │
│ 本番通話を監視        │          │                          │
│ スコアを蓄積          │          │ シナリオ生成              │
│ 異常時Slackアラート    │          │ Twilio発信               │
│                      │          │ 音声条件シミュレーション    │
└──────────┬───────────┘          └──────────┬──────────────┘
           │                                  │
           │ 録音 + ログ                       │ Twilio Media Streams
           │                                  │
    ┌──────┴──────────────────────────────────┴──────┐
    │              Reco Pipeline (テスト対象)           │
    │                                                  │
    │   Twilio ←→ Pipecat ←→ STT/LLM/TTS             │
    │                                                  │
    │   current_config.json で動的に設定変更可能        │
    └──────────────────────┬───────────────────────────┘
                           │
                           │ 録音 + トランスクリプト + レイテンシログ
                           ▼
                ┌─────────────────────┐
                │ Layer 2: Scorer      │
                │                      │
                │ 3軸自動採点           │
                │ → scores.jsonl       │
                └──────────────────────┘
```

### 1.2 データフロー

```
テストコール or 本番通話
    │
    ├→ 録音ファイル (.wav)
    ├→ トランスクリプト (STT出力 + AI発話テキスト)
    ├→ レイテンシログ (各ステージのタイムスタンプ)
    ├→ 使用config (_variant: A or B)
    │
    ▼
Scorer (Layer 2)
    │
    ├→ hallucination_score (3 Types)
    ├→ latency_metrics (perceived, per-stage)
    ├→ naturalness_score (1-10, 5項目内訳)
    │
    ▼
scores.jsonl
    │
    ▼
Orchestrator (Layer 4)
    │
    ├→ 診断: どの軸が目標から遠いか
    ├→ 仮説: 何を変えれば改善するか
    ├→ candidate_config.json
    │
    ▼
A/Bテスト (次のN通話)
    │
    ▼
scores.jsonl (A群 vs B群の比較)
    │
    ▼
Orchestrator: 採用 or 棄却
```

---

## 2. Layer 1: テストコール生成

### 2.1 概要

「偽顧客AI」がTwilio経由でRecoに電話をかけ、シナリオに沿って会話する。本番と完全に同じ経路（Twilio Media Streams, 8kHz mulaw）を通るため、E2Eテストとして信頼性が高い。

### 2.2 アーキテクチャ

```
Caller Agent (EC2 or ローカル)
    │
    │ 1. Twilio REST API で発信
    │    POST /Calls
    │    From: テスト用Twilio番号
    │    To: Recoテスト用Twilio番号
    │    Url: Caller AgentのTwiML webhook
    │
    │ 2. Twilio が接続確立
    │
    │ 3. Twilio Media Streams (WebSocket)
    │    Caller Agent ←→ Twilio ←→ Reco
    │    双方向8kHz mulaw音声ストリーム
    │
    │ 4. Caller Agent の内部パイプライン:
    │    受信音声 → STT → LLM (顧客役) → TTS → 送信音声
    │
    │ 5. 通話終了後:
    │    Twilio Recording API で録音取得
    │    両サイドのトランスクリプトをJSON保存
    │    Layer 2 (Scorer) に投入
    │
    ▼
```

### 2.3 Caller Agent の技術スタック

Recoと同じスタックを逆向きに使う：

| コンポーネント | Reco (応答側) | Caller Agent (発信側) |
|--------------|-------------|---------------------|
| フレームワーク | Pipecat | Pipecat (同じ) |
| Twilio接続 | Media Streams (受信) | Media Streams (発信) |
| STT | Deepgram Nova-3 | Deepgram Nova-3 (同じ) |
| LLM | Anthropic (業務フロー) | Anthropic (顧客役プロンプト) |
| TTS | ElevenLabs | 別プロバイダ or 別voice_id |

### 2.4 シナリオ設計

#### シナリオ構造

```json
{
  "scenario_id": "tokusoku_happy_001",
  "vertical": "tokusoku",
  "category": "happy_path",
  "persona": {
    "name": "田中太郎",
    "age": 45,
    "personality": "穏やか、協力的",
    "situation": "支払いを忘れていた。言われれば払う意思あり。"
  },
  "caller_system_prompt": "あなたは田中太郎（45歳）です。...",
  "audio_conditions": {
    "background_noise": "none",
    "speaking_speed": 1.0,
    "interruption_probability": 0.0
  },
  "expected_outcome": {
    "call_completed": true,
    "objective_achieved": true,
    "max_duration_seconds": 180
  },
  "evaluation_criteria": {
    "must_not_hallucinate": ["金額", "期日", "名前"],
    "must_mention": ["お支払い", "期日"],
    "tone": "respectful"
  }
}
```

#### シナリオカテゴリ（督促バーティカル）

| カテゴリ | 内容 | テスト目的 |
|---------|------|-----------|
| happy_path | 素直に応答、支払い意思あり | 基本フローの動作確認 |
| refusal | 「今忙しい」「払えない」 | 拒否時の分岐処理 |
| angry | 怒っている、クレーム | 感情的な相手への対応 |
| questioning | 詳細を聞いてくる | 正確な情報提供（ハルシネチェック） |
| silent | 長い沈黙、「えーと...」 | VAD/endpointing の挙動 |
| interrupting | AIの発話中に話し始める | バージイン処理 |
| number_confirm | 金額・日付を聞き返す | 数字の正確さ |
| wrong_person | 「田中じゃないです」 | 人違い時のフロー |

#### シナリオ自動生成

```python
def generate_scenarios(flow_definition, vertical, count=20):
    """
    会話フロー定義からテストシナリオを自動生成する
    
    LLMに会話フローを渡して、多様な顧客ペルソナ×行動パターンを生成
    """
    prompt = f"""
    以下の会話フロー定義に対して、{count}個のテストシナリオを生成してください。
    バーティカル: {vertical}
    
    各シナリオは以下のカテゴリのいずれかに分類してください:
    happy_path, refusal, angry, questioning, silent, 
    interrupting, number_confirm, wrong_person
    
    各カテゴリから最低2つ以上のシナリオを生成してください。
    
    会話フロー定義:
    {flow_definition}
    """
    # LLM呼び出し → JSONパース → scenarios/ に保存
```

### 2.5 音声条件シミュレーション

TTS出力後、Twilioに送る前に音声フィルターを適用：

```python
AUDIO_CONDITIONS = {
    "clean": {
        "description": "クリーンな環境",
        "filters": []
    },
    "office_noise": {
        "description": "オフィスの背景ノイズ",
        "filters": ["anoisesrc=a=0.015,amix"]
    },
    "phone_quality": {
        "description": "低品質電話回線",
        "filters": ["lowpass=f=3400", "highpass=f=300", "anlmdn=s=5"]
    },
    "slow_speaker": {
        "description": "ゆっくり話す高齢者",
        "filters": ["atempo=0.8"]
    },
    "fast_speaker": {
        "description": "早口のビジネスパーソン",
        "filters": ["atempo=1.25"]
    },
    "echo": {
        "description": "エコーのある環境（スピーカーフォン）",
        "filters": ["aecho=0.8:0.88:60:0.4"]
    }
}
```

### 2.6 テストスイート実行

```python
def run_test_suite(scenarios, config_variant=None, parallel=10):
    """
    テストスイートを実行する
    
    1,000回/日 = ~42回/時 = 並列10で4.2回/時/エージェント
    
    Args:
        scenarios: list[dict] — 実行するシナリオ
        config_variant: str — テスト対象のconfig ("A" or "B")
        parallel: int — 同時実行数（目標: 10並列）
    
    Flow:
        1. Recoにconfig_variantを適用
        2. 各シナリオについて:
           a. Caller Agentを起動
           b. Twilio経由でRecoに発信
           c. シナリオに沿って会話
           d. 通話終了後、録音+トランスクリプトを保存
           e. Layer 2 (Scorer) で自動採点
        3. 全結果をresults.tsvに集約
        4. サマリーレポートを生成
    """
```

---

## 3. Layer 2: 自動採点

### 3.1 ハルシネーションの3Type定義

音声AIパイプラインでは「ハルシネーション」が3つの異なるレイヤーで発生する。原因と対策が全く違うため、分けて検出・記録する。

#### Type 1: STTハルシネーション（聞き間違い）

**定義:** STTが相手の発話を正しく認識できず、間違ったテキストをLLMに渡す。

**例:**
- 相手:「5万円」→ STT:「ご満足」→ LLMが「ご満足」に対して返答
- 相手:「田中です」→ STT:「高梨です」→ 名前を間違えて会話が進む
- 相手: 無音 → STT:「はいはいはい」（Whisperのsilence hallucination）

**検出方法:**
- 録音を別のSTT（高精度モデル）で再書き起こしして、本番STT出力と比較
- STTのconfidence scoreが低い発話をフラグ
- 定型パターン検出（無音区間でのSTT出力など）

**対策ノブ:** STTプロバイダ、model、keywords、N-best選択、confidence threshold

#### Type 2: LLMハルシネーション（事実の捏造）

**定義:** LLMが会話フロー定義・CRMデータ・相手の発話のいずれにも根拠がない情報を生成する。

**例:**
- CRM:「期日3月15日」→ LLM:「3月20日までにお支払いください」
- フローに「返金対応可能」と書いていないのに「返金いたします」と約束
- 相手が言っていない条件を前提に話を進める

**検出方法:**
- LLM-as-judge: AI発話テキストを、(1)STT書き起こし, (2)会話フロー定義, (3)CRMデータ と照合
- 数値・日付・固有名詞を抽出して、ソースデータと完全一致チェック

**対策ノブ:** system prompt、temperature、max_tokens、ガードレール文言、RAG

#### Type 3: TTSハルシネーション（読み間違い）

**定義:** TTSがLLMの出力テキストを正しく音声化できない。

**例:**
- LLM:「3月15日」→ TTS:「さんがつじゅうごひ」（正:じゅうごにち）
- LLM:「御社」→ TTS:「おんしゃ」（正:おんしゃ — ただし文脈で「ごしゃ」も）
- LLM:「1,500円」→ TTS: 数字を読み飛ばす

**検出方法:**
- TTS出力音声を再度STTにかけて、LLM出力テキストと比較
- 数字・固有名詞に特化した照合

**対策ノブ:** TTSプロバイダ、SSML（読み仮名指定）、LLM出力に読み仮名を注入

#### 採点出力フォーマット

```json
{
  "hallucination": {
    "type1_stt": {
      "detected": false,
      "count": 0,
      "details": []
    },
    "type2_llm": {
      "detected": true,
      "count": 1,
      "details": [{
        "ai_utterance": "3月20日までにお支払いください",
        "source_data": "CRM: 期日3月15日",
        "reason": "期日が一致しない",
        "severity": "critical"
      }]
    },
    "type3_tts": {
      "detected": false,
      "count": 0,
      "details": []
    },
    "total_detected": true,
    "total_count": 1
  }
}
```

### 3.2 レイテンシ測定

**依存:** Reco側でのレイテンシ計装（5つのタイムスタンプ）

```
測定ポイント:
  t_vad_speech_end      → VADが発話終了を検出
  t_stt_final           → STTが確定テキストを返却
  t_llm_first_token     → LLMが最初のトークンを返却
  t_tts_first_byte      → TTSが最初の音声チャンクを返却
  t_audio_play_start    → 音声がTwilioに送出

導出指標:
  perceived_latency = t_audio_play_start - t_vad_speech_end（目標: <500ms）
  stt_latency = t_stt_final - t_vad_speech_end
  llm_ttfb = t_llm_first_token - t_stt_final
  tts_ttfb = t_tts_first_byte - t_llm_first_token
  audio_overhead = t_audio_play_start - t_tts_first_byte

集計: P50, P95, max を通話単位・日単位で算出
```

### 3.3 自然さ採点

LLM-as-judge で 5項目内訳付きの10点満点：

| 項目 | 配点 | 評価内容 |
|------|------|---------|
| 敬語の正確さ | 3点 | 丁寧語/尊敬語/謙譲語の使い分け |
| 応答テンポ | 2点 | 一文の長さ、応答の噛み合い |
| 相槌・フィラー | 2点 | タイミング、バリエーション |
| 目的達成度 | 2点 | アポ取得等の目的への進捗 |
| 全体印象 | 1点 | 「AIっぽさ」の有無 |

---

## 4. Layer 3: 本番モニタリング

### 4.1 データ収集

本番通話の終了ごとに自動的にデータを収集・採点する。

```
通話終了
  → Twilio Recording API で録音取得
  → Reco側のトランスクリプト + レイテンシログ取得
  → Layer 2 (Scorer) に投入
  → scores.jsonl に追記
  → アラート判定
```

### 4.2 アラート閾値

| 指標 | 計算方法 | 警告閾値 | ロールバック閾値 |
|------|---------|---------|----------------|
| ハルシネーション率 | 過去24h検出件数/総通話 | > 0% (即時通知) | > 2% (即時ロールバック) |
| レイテンシ P95 | 過去24hのP95 | > 600ms | > 800ms |
| 自然さ平均 | 過去24hの平均 | < 7.5 | < 7.0 |
| 通話完了率 | 30秒以上/総通話 | < 80% | < 70% |

### 4.3 Slack通知

| イベント | チャンネル | 緊急度 |
|---------|-----------|--------|
| ハルシネーション検出 | #reco-alerts | 即時 |
| ロールバック実行 | #reco-alerts | 即時 |
| 実験開始/結果 | #reco-experiments | 情報 |
| 日次サマリー | #reco-daily | 情報 |
| プロバイダ変更提案 | #reco-proposals | 要承認 |

---

## 5. Layer 4: 自律最適化オーケストレーター

### 5.1 実験サイクル

```
1. OBSERVE:  scores.jsonl から過去24hのスコアを集計
2. DIAGNOSE: 3軸のうち目標から最も遠いものを特定
3. HYPOTHESIZE: 何を変えれば改善するか仮説を立てる
4. PLAN: どのノブを変えるか決定（1実験1変更）
5. IMPLEMENT: candidate_config.json を生成
6. TEST: 
   - テストコール (Layer 1) で事前検証（20コール）
   - パスしたら本番A/Bテスト（20%トラフィック）
7. EVALUATE: A群 vs B群を比較（最低各20通話）
8. DECIDE: 改善→採用、悪化→棄却
9. LOG: experiments.tsv に記録
→ 1に戻る
```

### 5.2 3つの探索軸

オーケストレーターは以下の3軸で探索を行う。探索の深さが異なる。

#### 軸1: パラメータチューニング（config変更のみ、即時実行可能）

各プロバイダの設定値を変更する。最もリスクが低く、最も高速に実験できる。

| カテゴリ | ノブ | 影響する軸 |
|---------|------|-----------|
| STT設定 | keywords, endpointing閾値 | ハルシネ, 自然さ |
| N-best | N値, 選択ルール, confidence閾値 | ハルシネ |
| LLMプロンプト | system_prompt, ガードレール | ハルシネ, 自然さ |
| LLMパラメータ | temperature, max_tokens | ハルシネ, 自然さ |
| TTSパラメータ | stability, similarity_boost | 自然さ |
| TTSチャンク戦略 | 送信文字数/タイミング | レイテンシ, 自然さ |
| VAD閾値 | confidence, 沈黙時間 | レイテンシ, 自然さ |
| バッファ | audio buffer size | レイテンシ |
| Prefill | partial transcript送信タイミング | レイテンシ |

#### 軸2: モデル/プロバイダ切り替え（config変更、事前オフライン評価が必要）

パイプラインの各コンポーネントのプロバイダやモデルを差し替える。

| コンポーネント | 選択肢 |
|--------------|--------|
| STT | Deepgram Nova-3, Soniox v4, Google Chirp 2, OpenAI gpt-4o-transcribe, faster-whisper (GPU) |
| LLM | Anthropic Claude (Haiku/Sonnet), OpenAI GPT-4o-mini, GPT-4o, Groq Llama |
| TTS | ElevenLabs, Cartesia Sonic-3, Style-BERT-VITS2 (GPU), OpenAI TTS |

ルール:
- 切り替え前にLayer 1のテストコールでオフライン評価を実施
- パスしたら本番A/Bテスト
- GPU必要なモデル（faster-whisper, Style-BERT-VITS2）はインスタンス起動を人間に依頼
- 月額2万円超のコスト増は人間の承認が必要

#### 軸3: アーキテクチャ変更（パイプライン構造の組み替え）

パイプラインに層を追加・削除・並び替えする。最もインパクトが大きいが、リスクも最大。

**config切り替えで実現可能なアーキテクチャ変更:**

パイプラインのモジュール有効/無効をconfigで制御する。オーケストレーターが自律的に切り替え可能。

```json
{
  "architecture": {
    "nbest_enabled": true,
    "nbest_n": 3,
    "confidence_routing_enabled": false,
    "confidence_routing_threshold": 0.6,
    "confidence_routing_fallback_provider": "soniox",
    "speculative_prefill_enabled": true,
    "speculative_prefill_trigger_percent": 0.7,
    "hallucination_guard_enabled": false,
    "hallucination_guard_model": "claude-haiku-4-5",
    "ssml_injection_enabled": false,
    "ssml_injection_targets": ["numbers", "proper_nouns"],
    "rag_enabled": false,
    "rag_knowledge_base": "crm",
    "end_to_end_mode": false,
    "end_to_end_provider": "openai_realtime"
  }
}
```

| 変更 | 説明 | 影響する軸 |
|------|------|-----------|
| **N-best有無** | STT候補を複数取得して選択 | ハルシネ |
| **Confidence-gated routing** | STT信頼度が低い発話を別プロバイダに再送 | ハルシネ, レイテンシ |
| **Speculative prefill** | ユーザー発話中にLLMを先行起動 | レイテンシ |
| **ハルシネーションガード** | LLM出力をTTSに送る前に別LLMでチェック | ハルシネ, レイテンシ |
| **SSML注入** | LLM出力の数字/固有名詞に読み仮名を追加してからTTSに送る | ハルシネ(Type3) |
| **RAG層** | LLMにCRM/ナレッジベースの検索結果を注入 | ハルシネ(Type2) |
| **エンドツーエンド切り替え** | STT→LLM→TTS全体をOpenAI Realtime APIに置換 | 全軸 |

**コード変更が必要なアーキテクチャ変更:**

上記の各モジュールを最初に「無効状態で」実装しておく必要がある。オーケストレーターはconfigのフラグを切り替えるだけだが、モジュール本体のコードは事前に人間が書く。

オーケストレーターが「RAG層を有効にしたい」と判断した場合の流れ:
1. `rag_enabled: true` に変更してテストコールを実行
2. 改善が確認されたら本番A/Bテスト
3. 採用/棄却

オーケストレーターが「まだ実装されていないモジュールが必要」と判断した場合:
1. Slackの#reco-proposalsに提案を投稿
2. 何が必要か、なぜ必要か、期待される改善を説明
3. 人間が実装してconfigフラグを追加
4. オーケストレーターが有効化してテスト

#### 3軸の探索優先順位

オーケストレーターは以下の順序で探索する:

```
1. パラメータチューニング（最も低コスト、高速）
   → 改善が頭打ちになったら
2. モデル/プロバイダ切り替え（中コスト、オフライン評価必要）
   → 改善が頭打ちになったら
3. アーキテクチャ変更（高コスト、モジュール実装が必要な場合あり）
```

ただしこの順序は固定ではない。スコアデータから「パラメータでは解決不可能な構造的問題」が見える場合、オーケストレーターは直接アーキテクチャ変更に飛ぶ判断もできる。

#### 変更不可

- Twilio / SIP設定（インフラ）
- EC2インスタンス構成（インフラ）
- 会話フローの構造自体（顧客合意事項）
- CRMデータ（外部システム、読み取りのみ）

### 5.3 安全制約

### 5.3 安全制約

- **1実験1変更:** 同時に2つ以上のノブを変えない。因果関係が不明になる。
- **最低サンプル数:** A/B各群400通話。1,000回/日（A群800 + B群200）で2日で達成。
- **ハルシネーション最優先:** candidate configでハルシネーション率が上昇したら、他の指標が改善していても即棄却。
- **ロールバック即時:** ロールバック閾値を超えたら、人間の承認を待たずに前のconfigに戻す。
- **記録義務:** すべての実験（成功・失敗とも）をexperiments.tsvに記録する。

---

## 6. リポジトリ構成

```
reco-orchestrator/
│
├── README.md                      # プロジェクト概要
├── DESIGN.md                      # 本ドキュメント
├── context_prompt.md              # Layer 4: メタエージェントへの指示書
├── TEAM_CHECKLIST.md              # チーム確認事項
│
├── caller/                        # Layer 1: テストコール生成
│   ├── caller_agent.py            # 偽顧客AIのメインスクリプト (Pipecat)
│   ├── scenario_generator.py      # シナリオ自動生成 (LLM)
│   ├── audio_conditions.py        # ノイズ・話速フィルター
│   ├── run_test_suite.py          # テストスイート実行
│   ├── twilio_caller.py           # Twilio発信 + Media Streams接続
│   └── scenarios/                 # 生成済みシナリオ
│       ├── tokusoku_happy.json
│       ├── tokusoku_angry.json
│       ├── tokusoku_silent.json
│       └── ...
│
├── scoring/                       # Layer 2: 自動採点
│   ├── score_call.py              # エントリーポイント (cron対応)
│   ├── hallucination_judge.py     # ハルシネ3Type判定 (LLM-as-judge)
│   ├── naturalness_judge.py       # 自然さ採点 (LLM-as-judge)
│   └── latency_extractor.py      # レイテンシ抽出
│
├── monitor/                       # Layer 3: 本番モニタリング
│   ├── watch_production.py        # 本番通話の自動採点ループ
│   ├── alert_slack.py             # Slackアラート
│   └── daily_report.py            # 日次サマリー生成
│
├── orchestrator/                  # Layer 4: 自律最適化
│   ├── orchestrator.py            # メタエージェント本体
│   ├── ab_splitter.py             # A/Bテスト管理
│   └── rollback.py                # 自動ロールバック
│
├── configs/                       # パイプライン設定
│   ├── current_config.json        # 本番config
│   ├── candidate_config.json      # A/B候補config
│   └── config_history.jsonl       # 変更履歴
│
├── experiments/                   # 実験ログ
│   └── experiments.tsv
│
├── eval/                          # オフライン評価
│   ├── offline_eval.py            # プロバイダ切り替え時の事前評価
│   └── corpus/                    # テストコーパス (WAV + ground truth)
│
├── scores/                        # 採点結果
│   └── scores.jsonl
│
└── .gitignore
```

---

## 7. 実装ロードマップ

### Phase 0: 最小テストコール（3日）

**目標:** Caller Agent → Twilio → Reco → 1通話が通ることを確認

```
Day 1:
  - reco-orchestrator リポジトリ作成、骨格コミット
  - caller_agent.py の最小実装
    - Pipecat + Twilio Media Streams で発信
    - 固定テキスト「お世話になっております。田中と申します。」を送信
    - Recoの応答を受信してログに出力

Day 2:
  - Caller Agentに STT + LLM(顧客役) + TTS を組み込む
  - 固定シナリオ1つ（督促 happy_path）で会話が成立することを確認

Day 3:
  - 通話終了後に録音を取得
  - トランスクリプトをJSON保存
  - score_call.py で手動採点を1回実行
```

### Phase 1: 採点パイプライン（1週間）

**目標:** テストコール→自動採点が回る

```
- hallucination_judge.py の3Type実装（LLM-as-judge）
- naturalness_judge.py の実装
- Reco側にレイテンシ計装を依頼（5つのタイムスタンプ）
- latency_extractor.py の実装
- score_call.py を完成させて、テストコール結果を自動採点
```

### Phase 2: シナリオ拡張 + テストスイート（1週間）

**目標:** 多様なシナリオでRecoを自動テストできる

```
- scenario_generator.py 実装
- 督促バーティカルで8カテゴリ×各3シナリオ = 24シナリオ生成
- audio_conditions.py 実装（ノイズ、話速）
- run_test_suite.py で24シナリオを連続実行
- 結果をresults.tsvに自動集約
```

### Phase 3: 本番モニタリング（1週間）

**目標:** 本番通話も自動採点してスコアが溜まる

```
- watch_production.py 実装（cron or daemon）
- Asterisk/Twilio録音の自動取得
- 本番通話の自動採点開始
- alert_slack.py 実装
- daily_report.py 実装
- ベースラインスコアを1週間蓄積
```

### Phase 4: 自律最適化ループ（2週間）

**目標:** オーケストレーターが自律的に実験を回す

```
- orchestrator.py 実装
  - scores.jsonl を読んで診断
  - candidate_config.json を生成
  - Layer 1でテストコールを回して事前検証
  - パスしたら本番A/Bテスト
- ab_splitter.py 実装（Reco側のconfig読み込み変更も含む）
- rollback.py 実装
- 最初の自律実験を実行
```

### タイムライン

```
Week 1:     Phase 0 (最小テストコール) + Phase 1 開始
Week 2:     Phase 1 完了 + Phase 2 開始
Week 3:     Phase 2 完了 + Phase 3 開始
Week 4:     Phase 3 完了 (ベースライン蓄積開始)
Week 5-6:   Phase 4 (自律ループ起動)
```

---

## 8. コスト見積もり

### テストコール1回あたり: ~¥7

### 月間ランニングコスト

| 項目 | 量 | コスト |
|------|-----|--------|
| テストコール | 1,000回/日 × 30日 | ~¥210,000 |
| 本番通話採点 | 50回/日 × 30日 | ~¥2,250 |
| オーケストレーター (Claude Code) | 30実験/月 | ~¥15,000 |
| **合計** | | **~¥227,000/月** |

---

## 9. チーム確認事項（ブロッカー）

本設計を実装するために、以下の確認と作業がReco本番チーム側で必要：

| # | 確認/作業 | 担当 | ブロッカー先 |
|---|----------|------|-------------|
| 1 | STT/LLM/TTS設定の管理方法（ハードコード？config？） | Ryuu | Phase 1, 4 |
| 2 | Asterisk録音ファイルのパスと形式 | Ryuu/Sota | Phase 3 |
| 3 | Twilio Media Streams接続のサンプルコード共有 | Ryuu | Phase 0 |
| 4 | テスト用Twilio番号のSID/AuthToken | Sota | Phase 0 |
| 5 | レイテンシ計装（5行追加）のPR | Ryuu | Phase 1 |
| 6 | config外部化（必要なら） | Ryuu | Phase 4 |
| 7 | Twilio Voice Insights Advanced Featuresの有効化状況 | Sota | Phase 3 |

---

## 10. 成功基準

6週間後に以下が達成されていること：

- [ ] テストコールを自動で1,000回/日（10並列）回せている
- [ ] 全通話（テスト+本番）が3軸×3Type で自動採点されている
- [ ] ハルシネーションの検出率 > 90%（人間が発見したものとの一致率）
- [ ] オーケストレーターが最低5回の自律実験を完了している
- [ ] 少なくとも1つの実験で3軸のいずれかが改善している
