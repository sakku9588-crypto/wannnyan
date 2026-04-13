# main.py - エントリーポイント

import sys
import argparse
from audio_engine import AudioEngine
from emotion_engine import EmotionEngine
from gui import PetTranslatorGUI
from pet_profiles import KEI_KUN, GEMI_NYAN
from config import DOG_CONFIG, CAT_CONFIG

def main():
    parser = argparse.ArgumentParser(description="さく猫式・ペットトランスレーター")
    parser.add_argument("--pet", type=str, choices=["dog", "cat"], default="dog",
                        help="ペットの種類（dog or cat）")
    parser.add_argument("--device", type=int, default=None,
                        help="音声入力デバイス番号")
    args = parser.parse_args()
    
    print("🐾 さく猫式・ペットトランスレーター起動にゃ！ 🐾")
    print(f"ペットモード: {args.pet}")
    
    # 設定とプロフィール選択
    if args.pet == "dog":
        config = DOG_CONFIG
        profile = KEI_KUN
        print(f"🐕 ケイくん（{profile.breed}）とおしゃべりするにゃ！")
    else:
        config = CAT_CONFIG
        profile = GEMI_NYAN
        print(f"🐱 ジェミ猫とおしゃべりするにゃ！")
    
    # エンジン初期化
    audio_engine = AudioEngine(sample_rate=22050, duration=1.0)
    emotion_engine = EmotionEngine(pet_type=args.pet, config=config)
    
    # GUI起動
    gui = PetTranslatorGUI(audio_engine, emotion_engine, profile, config)
    
    try:
        gui.run()
    except KeyboardInterrupt:
        print("\n👋 バイバイにゃ！また遊ぼうにゃ！")
        if audio_engine.is_recording:
            audio_engine.stop_recording()
        sys.exit(0)

if __name__ == "__main__":
    main()