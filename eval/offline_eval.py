"""
offline_eval.py — プロバイダ切り替え時のオフライン評価

プロバイダを本番に入れる前に、テストコーパスで精度・レイテンシ・コストを評価する。

Usage:
  # STTプロバイダ比較
  python eval/offline_eval.py --component stt --provider soniox
  python eval/offline_eval.py --component stt --provider google
  python eval/offline_eval.py --component stt --provider deepgram --compare

  # TTSプロバイダ比較
  python eval/offline_eval.py --component tts --provider cartesia

  # 全プロバイダ一括比較
  python eval/offline_eval.py --component stt --all
"""

import argparse
import json
import os
import time
from pathlib import Path

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "corpus")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "experiments")


# --- STT Evaluation ---

def eval_stt_deepgram(wav_path, config=None):
    """Deepgram STT評価"""
    # TODO: Deepgram REST API呼び出し
    # from scripts.eval.benchmark_stt import stt_deepgram, compute_cer
    pass


def eval_stt_soniox(wav_path, config=None):
    """Soniox STT評価"""
    # TODO: Soniox API呼び出し
    pass


def eval_stt_google(wav_path, config=None):
    """Google Cloud STT評価"""
    # TODO: Google Cloud Speech-to-Text API呼び出し
    pass


def eval_stt_openai(wav_path, config=None):
    """OpenAI Whisper API評価"""
    # TODO: OpenAI API呼び出し
    pass


STT_PROVIDERS = {
    "deepgram": eval_stt_deepgram,
    "soniox": eval_stt_soniox,
    "google": eval_stt_google,
    "openai": eval_stt_openai,
}


# --- TTS Evaluation ---

def eval_tts_elevenlabs(text, config=None):
    """ElevenLabs TTS評価（レイテンシ計測）"""
    # TODO: ElevenLabs API呼び出し + TTFB計測
    pass


def eval_tts_cartesia(text, config=None):
    """Cartesia Sonic-3 TTS評価"""
    # TODO: Cartesia API呼び出し + TTFB計測
    pass


def eval_tts_openai(text, config=None):
    """OpenAI TTS評価"""
    # TODO: OpenAI TTS API呼び出し + TTFB計測
    pass


TTS_PROVIDERS = {
    "elevenlabs": eval_tts_elevenlabs,
    "cartesia": eval_tts_cartesia,
    "openai": eval_tts_openai,
}


# --- Main ---

def run_stt_eval(provider, corpus_dir=CORPUS_DIR):
    """
    テストコーパスで STT プロバイダを評価

    Returns:
        dict: {mean_cer, median_cer, latency_p50, latency_p95, per_file_results}
    """
    ground_truth_path = os.path.join(corpus_dir, "ground_truth.json")
    if not os.path.exists(ground_truth_path):
        print(f"Error: {ground_truth_path} not found")
        return None

    with open(ground_truth_path, "r") as f:
        ground_truth = json.load(f)

    wav_files = sorted(Path(corpus_dir).glob("*.wav"))
    print(f"Evaluating {provider} on {len(wav_files)} files...")

    eval_fn = STT_PROVIDERS.get(provider)
    if not eval_fn:
        print(f"Error: Unknown provider '{provider}'. Available: {list(STT_PROVIDERS.keys())}")
        return None

    results = []
    for wav_path in wav_files:
        file_id = wav_path.stem
        ref_text = ground_truth.get(file_id, {}).get("text", "")

        start = time.time()
        # hyp_text = eval_fn(str(wav_path))
        latency = (time.time() - start) * 1000

        # cer = compute_cer(ref_text, hyp_text)
        # results.append({"file": file_id, "cer": cer, "latency_ms": latency})

    # TODO: 集計してreturn
    return results


def run_tts_eval(provider, test_texts=None):
    """
    TTSプロバイダをレイテンシ + 音質で評価

    Returns:
        dict: {ttfb_p50, ttfb_p95, per_text_results}
    """
    if test_texts is None:
        test_texts = [
            "お電話ありがとうございます。株式会社StepAIの担当でございます。",
            "お支払い期日が過ぎておりますので、ご確認をお願いいたします。",
            "はい、さようでございますか。",
            "それでは、折り返しのお電話をお待ちしております。",
            "お忙しいところ恐れ入りますが、少々お時間よろしいでしょうか。",
        ]

    eval_fn = TTS_PROVIDERS.get(provider)
    if not eval_fn:
        print(f"Error: Unknown provider '{provider}'. Available: {list(TTS_PROVIDERS.keys())}")
        return None

    results = []
    for text in test_texts:
        ttfbs = []
        # 5回ずつ計測して安定性を見る
        for _ in range(5):
            start = time.time()
            # eval_fn(text)
            ttfb = (time.time() - start) * 1000
            ttfbs.append(ttfb)

        results.append({
            "text": text[:20] + "...",
            "ttfb_mean": round(sum(ttfbs) / len(ttfbs), 1),
            "ttfb_p95": round(sorted(ttfbs)[int(len(ttfbs) * 0.95)], 1),
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Offline provider evaluation")
    parser.add_argument("--component", choices=["stt", "tts", "llm"], required=True)
    parser.add_argument("--provider", help="Provider to evaluate")
    parser.add_argument("--all", action="store_true", help="Evaluate all providers")
    parser.add_argument("--compare", action="store_true", help="Compare with current provider")
    args = parser.parse_args()

    if args.component == "stt":
        if args.all:
            for provider in STT_PROVIDERS:
                print(f"\n{'='*60}")
                print(f"  {provider}")
                print(f"{'='*60}")
                run_stt_eval(provider)
        elif args.provider:
            run_stt_eval(args.provider)
        else:
            parser.print_help()

    elif args.component == "tts":
        if args.all:
            for provider in TTS_PROVIDERS:
                print(f"\n{'='*60}")
                print(f"  {provider}")
                print(f"{'='*60}")
                run_tts_eval(provider)
        elif args.provider:
            run_tts_eval(args.provider)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
