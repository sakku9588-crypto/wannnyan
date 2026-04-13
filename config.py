# config.py - 犬猫の感情重み設定

# ============ 犬用設定（ケイくん：ポメラニアン×スピッツ） ============
DOG_CONFIG = {
    "breed": "pomeranian_spitz",
    "display_name": "ケイくん（ポメスピ）🐕",
    "vocal_range": {
        "pitch_min": 500,
        "pitch_max": 1200,
        "bark_duration_min": 0.1,
        "bark_duration_max": 0.4,
        "avg_rms": 0.08,
        "zcr_baseline": 0.12
    },
    "emotions": {
        "happy": {
            "name": "嬉しい",
            "emoji": "😊",
            "weight": {"pitch": 1.5, "duration": -0.3, "rms": 0.8, "zcr": 0.2},
            "phrases": ["わんわん！", "しっぽフリフリ", "遊んでくれるの？"]
        },
        "sad": {
            "name": "悲しい",
            "emoji": "😢",
            "weight": {"pitch": -1.2, "duration": 0.6, "rms": -0.4, "zcr": -0.1},
            "phrases": ["くぅ〜ん...", "しょんぼり", "お留守番さみしいよ"]
        },
        "angry": {
            "name": "怒り",
            "emoji": "😠",
            "weight": {"pitch": 0.8, "duration": 0.3, "rms": 1.2, "zcr": 1.5},
            "phrases": ["ガウガウ！", "近づくな！", "うーっ"]
        },
        "hungry": {
            "name": "お腹すいた",
            "emoji": "🍖",
            "weight": {"pitch": 0.5, "duration": 0.2, "rms": 0.5, "zcr": 0.1},
            "phrases": ["ぐぅ〜", "ごはんまだ？", "おやつちょうだい"]
        },
        "lonely": {
            "name": "寂しい",
            "emoji": "🥺",
            "weight": {"pitch": -0.8, "duration": 0.9, "rms": -0.5, "zcr": -0.2},
            "phrases": ["さみしいよ〜", "なでて？", "どこにいるの？"]
        },
        "alert": {
            "name": "警戒",
            "emoji": "⚠️",
            "weight": {"pitch": 1.8, "duration": 0.1, "rms": 0.9, "zcr": 1.2},
            "phrases": ["誰か来た！", "ワンワンワン！", "ピンポン鳴ったよ"]
        }
    }
}

# ============ 猫用設定（ジェミ猫モデル） ============
CAT_CONFIG = {
    "breed": "mixed_cat",
    "display_name": "ジェミ猫（ミックス）🐱",
    "vocal_range": {
        "pitch_min": 200,
        "pitch_max": 900,
        "meow_duration_min": 0.2,
        "meow_duration_max": 1.2,
        "purr_freq_range": [20, 150]
    },
    "emotions": {
        "purr": {
            "name": "ゴロゴロ満足",
            "emoji": "😺✨",
            "type": "continuous",
            "freq_range": [20, 150],
            "phrases": ["ゴロゴロ...", "気持ちいいにゃ", "もっと撫でて"]
        },
        "short_meow": {
            "name": "短いにゃー",
            "emoji": "😸",
            "type": "short",
            "duration_max": 0.3,
            "phrases": ["にゃ！", "ごはんちょうだい", "おやつ！"]
        },
        "long_meow": {
            "name": "長いにゃー",
            "emoji": "😿",
            "type": "long",
            "duration_min": 0.6,
            "phrases": ["にゃ〜ん...", "さみしいよ", "構ってほしい"]
        },
        "hiss": {
            "name": "シャー",
            "emoji": "😾",
            "type": "hiss",
            "phrases": ["シャーッ！", "近づくな！", "怒ってるにゃ"]
        },
        "chatter": {
            "name": "カチカチ",
            "emoji": "😼🦅",
            "type": "chatter",
            "phrases": ["カチカチ...", "鳥見つけた！", "取れないにゃ"]
        },
        "growl": {
            "name": "ガウガウ",
            "emoji": "😤",
            "type": "growl",
            "phrases": ["うーっ...", "やめろにゃ", "これはボクのもの"]
        }
    }
}

# 正規化パラメータ（全ペット共通）
NORM_PARAMS = {
    "pitch": {"mean": 450, "std": 250},
    "duration": {"mean": 0.4, "std": 0.25},
    "rms": {"mean": 0.05, "std": 0.04},
    "zcr": {"mean": 0.08, "std": 0.05}
}