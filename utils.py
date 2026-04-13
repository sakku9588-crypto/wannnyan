# utils.py - 便利機能

import json
import os
from datetime import datetime

class Logger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def save_conversation(self, pet_name, conversation):
        filename = f"{self.log_dir}/{pet_name}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(conversation, f, ensure_ascii=False, indent=2)
        return filename
    
    def load_conversation(self, pet_name, date_str):
        filename = f"{self.log_dir}/{pet_name}_{date_str}.json"
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

def list_audio_devices():
    """使用可能な音声デバイスを一覧表示"""
    import sounddevice as sd
    print(sd.query_devices())

def play_test_sound():
    """テスト用の音を再生"""
    import numpy as np
    import sounddevice as sd
    duration = 0.5
    frequency = 440
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    wave = 0.3 * np.sin(2 * np.pi * frequency * t)
    sd.play(wave, sample_rate)
    sd.wait()