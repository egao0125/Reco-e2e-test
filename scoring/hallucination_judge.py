"""
hallucination_judge.py — LLM-as-judgeでハルシネーションを検出

入力:
  - STT書き起こし（相手の発話）
  - AI発話テキスト（Recoの発話）
  - 会話フロー定義（許可された発話パターン）
  - CRMデータ（名前、金額、期日等）

出力:
  - detected: bool
  - count: int
  - details: list[dict]  各ハルシネーション箇所の説明
"""

import os
import json

# TODO: anthropic SDK import
# import anthropic


JUDGE_PROMPT = """あなたは音声AIシステムの品質管理者です。
以下のAI電話通話を分析し、AIが発話した内容にハルシネーション（事実に基づかない情報）が含まれているかを判定してください。

## ハルシネーションの定義
AIが発話した内容のうち、以下のいずれにも根拠がないもの：
1. 相手の発話（STT書き起こし）
2. 会話フロー定義（許可された発話パターン）
3. CRMから渡されたデータ

## 具体例
- 相手が言っていない金額を提示する → ハルシネーション
- 存在しない支払い期日を伝える → ハルシネーション
- 相手の名前を間違える → ハルシネーション
- 会話フローに定義されていない条件を約束する → ハルシネーション
- 「お電話ありがとうございます」等の定型フレーズ → ハルシネーションではない
- フローに定義された応答パターンの範囲内 → ハルシネーションではない

## 入力データ

### 相手の発話（STT書き起こし）
{stt_transcript}

### AIの発話テキスト
{ai_transcript}

### 会話フロー定義
{flow_definition}

### CRMデータ
{crm_data}

## 出力形式
以下のJSON形式で回答してください。他の文章は含めないでください。

{{
  "detected": true/false,
  "count": <ハルシネーション箇所数>,
  "details": [
    {{
      "ai_utterance": "<該当するAIの発話>",
      "reason": "<なぜハルシネーションと判定したか>",
      "severity": "critical/minor"
    }}
  ]
}}
"""


def judge_hallucination(transcript, flow_definition=None, crm_data=None):
    """
    通話のハルシネーションを判定する

    Args:
        transcript: dict with "stt" (相手の発話) and "ai" (AIの発話) keys
        flow_definition: str or dict — 会話フロー定義
        crm_data: dict — CRMから渡されたデータ

    Returns:
        dict: {"detected": bool, "count": int, "details": list}
    """
    # TODO: Anthropic API呼び出し実装
    #
    # client = anthropic.Anthropic()
    # response = client.messages.create(
    #     model="claude-haiku-4-5-20251001",
    #     max_tokens=1000,
    #     messages=[{
    #         "role": "user",
    #         "content": JUDGE_PROMPT.format(
    #             stt_transcript=transcript.get("stt", ""),
    #             ai_transcript=transcript.get("ai", ""),
    #             flow_definition=json.dumps(flow_definition or {}, ensure_ascii=False),
    #             crm_data=json.dumps(crm_data or {}, ensure_ascii=False),
    #         )
    #     }]
    # )
    #
    # result = json.loads(response.content[0].text)
    # return result

    return {
        "detected": False,
        "count": 0,
        "details": [],
    }
