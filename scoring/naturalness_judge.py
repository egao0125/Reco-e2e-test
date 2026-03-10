"""
naturalness_judge.py — LLM-as-judgeで会話の自然さを採点

入力: 通話の書き起こし全文
出力: スコア (1-10) + 改善コメント
"""

import json

JUDGE_PROMPT = """あなたは日本のビジネス電話の品質評価者です。
以下のAI電話通話の書き起こしを読み、ビジネス電話としての自然さを1-10のスケールで採点してください。

## 評価基準

### 敬語の正確さ (配点: 3)
- 丁寧語・尊敬語・謙譲語の使い分けが正確か
- ビジネス電話として適切な言葉遣いか

### 応答のテンポ (配点: 2)
- 一文が長すぎないか（自然な電話では一文15-25文字程度）
- 相手の発話に対する応答が噛み合っているか

### 相槌・フィラー (配点: 2)
- 適切なタイミングで相槌を入れているか
- 「はい」「さようでございますか」等のバリエーション

### 目的達成度 (配点: 2)
- 通話の目的（アポ取得、折り返し依頼等）に向かって会話が進んでいるか
- 無駄なやりとりが多くないか

### 全体の印象 (配点: 1)
- 「AIと話している」と気づかれにくいか
- 人間のオペレーターの電話として違和感がないか

## 通話書き起こし

{transcript}

## 出力形式
以下のJSON形式で回答してください。他の文章は含めないでください。

{{
  "score": <1-10>,
  "breakdown": {{
    "keigo": <1-3>,
    "tempo": <1-2>,
    "aizuchi": <1-2>,
    "objective": <1-2>,
    "impression": <0-1>
  }},
  "feedback": "<具体的な改善コメント（日本語）>",
  "worst_utterance": "<最も不自然だったAIの発話>",
  "best_utterance": "<最も自然だったAIの発話>"
}}
"""


def judge_naturalness(transcript):
    """
    通話の自然さを採点する

    Args:
        transcript: str — 通話の書き起こし全文
                    または dict with turns

    Returns:
        dict: {"score": int, "feedback": str, ...}
    """
    # TODO: Anthropic API呼び出し実装
    #
    # client = anthropic.Anthropic()
    # response = client.messages.create(
    #     model="claude-haiku-4-5-20251001",
    #     max_tokens=500,
    #     messages=[{
    #         "role": "user",
    #         "content": JUDGE_PROMPT.format(
    #             transcript=transcript if isinstance(transcript, str)
    #                        else json.dumps(transcript, ensure_ascii=False)
    #         )
    #     }]
    # )
    #
    # result = json.loads(response.content[0].text)
    # return result

    return {
        "score": None,
        "feedback": None,
    }
