"""
score_call.py — 通話の3軸自動採点エントリーポイント

Usage:
  python scoring/score_call.py --call-id <call_id>
  python scoring/score_call.py --watch /var/log/reco/recordings/  # 新規録音を監視

Cronで実行:
  */30 * * * * cd /path/to/reco-orchestrator && python scoring/score_call.py --watch /var/log/reco/recordings/
"""

import argparse
import json
import os
import glob
import time
from datetime import datetime
from pathlib import Path

# --- Config ---
SCORES_DIR = os.path.join(os.path.dirname(__file__), "..", "scores")
SCORES_FILE = os.path.join(SCORES_DIR, "scores.jsonl")
PROCESSED_FILE = os.path.join(SCORES_DIR, ".processed_calls")

# --- Imports (実装後に有効化) ---
# from hallucination_judge import judge_hallucination
# from naturalness_judge import judge_naturalness
# from latency_extractor import extract_latency


def load_processed_calls():
    """既に採点済みの通話IDを読み込む"""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r") as f:
            return set(f.read().splitlines())
    return set()


def mark_processed(call_id):
    """通話IDを採点済みとしてマーク"""
    with open(PROCESSED_FILE, "a") as f:
        f.write(f"{call_id}\n")


def score_call(call_id, recording_path=None, transcript_path=None, latency_path=None):
    """
    1通話を3軸で採点する

    Args:
        call_id: 通話の一意識別子
        recording_path: 録音ファイルのパス (.wav)
        transcript_path: 書き起こしファイルのパス (.json)
        latency_path: レイテンシログのパス (.json)

    Returns:
        dict: 採点結果
    """
    scores = {
        "call_id": call_id,
        "timestamp": datetime.utcnow().isoformat(),
        "config_variant": None,  # "A" or "B" — A/Bテスト用
    }

    # --- 1. ハルシネーション判定 ---
    # TODO: 実装
    # transcript = load_transcript(transcript_path)
    # flow_definition = load_flow_for_call(call_id)
    # crm_data = load_crm_data_for_call(call_id)
    # scores["hallucination"] = judge_hallucination(transcript, flow_definition, crm_data)
    scores["hallucination"] = {
        "detected": False,
        "count": 0,
        "details": [],
    }

    # --- 2. レイテンシ ---
    # TODO: 実装（レイテンシ計装がReco側に入ってから）
    # if latency_path and os.path.exists(latency_path):
    #     scores["latency"] = extract_latency(latency_path)
    # else:
    #     scores["latency"] = {"available": False}
    scores["latency"] = {
        "available": False,
        "perceived_ms": None,
        "vad_to_stt_ms": None,
        "stt_to_llm_ms": None,
        "llm_ttfb_ms": None,
        "tts_ttfb_ms": None,
    }

    # --- 3. 自然さ ---
    # TODO: 実装
    # scores["naturalness"] = judge_naturalness(transcript)
    scores["naturalness"] = {
        "score": None,  # 1-10
        "feedback": None,
    }

    # --- 4. メタデータ ---
    scores["meta"] = {
        "duration_seconds": None,
        "call_completed": None,  # 30秒以上 = True
        "objective_achieved": None,  # アポ取得等
    }

    return scores


def append_score(scores):
    """scores.jsonlに1行追記"""
    os.makedirs(SCORES_DIR, exist_ok=True)
    with open(SCORES_FILE, "a") as f:
        f.write(json.dumps(scores, ensure_ascii=False) + "\n")


def watch_directory(recordings_dir):
    """
    録音ディレクトリを監視して、新しい録音を自動採点する

    Args:
        recordings_dir: Asteriskの録音保存ディレクトリ
    """
    processed = load_processed_calls()
    recordings = glob.glob(os.path.join(recordings_dir, "*.wav"))

    new_count = 0
    for recording_path in recordings:
        call_id = Path(recording_path).stem  # ファイル名から拡張子を除いたもの

        if call_id in processed:
            continue

        print(f"Scoring: {call_id}")

        # パスの推定（実際のディレクトリ構成に合わせて調整）
        transcript_path = recording_path.replace(".wav", "_transcript.json")
        latency_path = recording_path.replace(
            "recordings", "latency"
        ).replace(".wav", ".json")

        try:
            scores = score_call(
                call_id=call_id,
                recording_path=recording_path,
                transcript_path=transcript_path,
                latency_path=latency_path,
            )
            append_score(scores)
            mark_processed(call_id)
            new_count += 1

            # ハルシネーション検出時のアラート
            if scores["hallucination"]["detected"]:
                alert_hallucination(call_id, scores)

        except Exception as e:
            print(f"Error scoring {call_id}: {e}")

    print(f"Done. Scored {new_count} new calls. Total processed: {len(processed) + new_count}")


def alert_hallucination(call_id, scores):
    """
    ハルシネーション検出時のSlack通知

    TODO: Slack webhook URLを設定
    """
    # import requests
    # webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    # if webhook_url:
    #     requests.post(webhook_url, json={
    #         "text": f"🚨 ハルシネーション検出: call {call_id}\n"
    #                 f"詳細: {scores['hallucination']['details']}"
    #     })
    print(f"⚠️  HALLUCINATION DETECTED: {call_id}")
    print(f"   Details: {scores['hallucination']['details']}")


def main():
    parser = argparse.ArgumentParser(description="Score calls on 3 axes")
    parser.add_argument("--call-id", help="Score a single call")
    parser.add_argument("--watch", help="Watch a directory for new recordings")
    parser.add_argument("--recording", help="Path to recording file")
    args = parser.parse_args()

    if args.watch:
        watch_directory(args.watch)
    elif args.call_id:
        scores = score_call(
            call_id=args.call_id,
            recording_path=args.recording,
        )
        append_score(scores)
        print(json.dumps(scores, indent=2, ensure_ascii=False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
