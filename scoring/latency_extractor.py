"""
latency_extractor.py — パイプラインレイテンシの抽出

入力: レイテンシログファイル (JSON)
出力: 各ステージのレイテンシ (ms)

依存: Reco本番側でのレイテンシ計装（5つのタイムスタンプ）

Reco側で必要な計装:
  timestamps["vad_speech_end"]   = time.time()  # VADが発話終了を検出
  timestamps["stt_final"]        = time.time()  # STT確定テキスト返却
  timestamps["llm_first_token"]  = time.time()  # LLM最初のトークン
  timestamps["tts_first_byte"]   = time.time()  # TTS最初の音声チャンク
  timestamps["audio_play_start"] = time.time()  # SIPに音声送出
"""

import json
import os


def extract_latency(latency_path):
    """
    レイテンシログから各ステージの遅延を計算する

    Args:
        latency_path: レイテンシログファイルのパス

    Returns:
        dict: 各ステージのレイテンシ (ms)
    """
    if not os.path.exists(latency_path):
        return {"available": False}

    with open(latency_path, "r") as f:
        data = json.load(f)

    # 通話中に複数ターンがある場合、全ターンのタイムスタンプがリストで入る想定
    turns = data.get("turns", [data])  # 単一ターンならそのまま

    latencies = []
    for turn in turns:
        t = {}

        vad_end = turn.get("vad_speech_end")
        stt_final = turn.get("stt_final")
        llm_first = turn.get("llm_first_token")
        tts_first = turn.get("tts_first_byte")
        audio_start = turn.get("audio_play_start")

        if vad_end and stt_final:
            t["vad_to_stt_ms"] = round((stt_final - vad_end) * 1000, 1)
        if stt_final and llm_first:
            t["stt_to_llm_ms"] = round((llm_first - stt_final) * 1000, 1)
        if llm_first and tts_first:
            t["llm_ttfb_ms"] = round((tts_first - llm_first) * 1000, 1)
        if tts_first and audio_start:
            t["tts_ttfb_ms"] = round((audio_start - tts_first) * 1000, 1)
        if vad_end and audio_start:
            t["perceived_ms"] = round((audio_start - vad_end) * 1000, 1)

        if t:
            latencies.append(t)

    if not latencies:
        return {"available": False}

    # 全ターンの統計
    perceived_values = [t["perceived_ms"] for t in latencies if "perceived_ms" in t]

    return {
        "available": True,
        "turn_count": len(latencies),
        "perceived_ms": {
            "mean": round(sum(perceived_values) / len(perceived_values), 1) if perceived_values else None,
            "p50": sorted(perceived_values)[len(perceived_values) // 2] if perceived_values else None,
            "p95": sorted(perceived_values)[int(len(perceived_values) * 0.95)] if perceived_values else None,
            "max": max(perceived_values) if perceived_values else None,
        },
        "per_turn": latencies,
    }
