#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 さく猫式・ペットトランスレーター - 感情判定エンジン 🧠

音声特徴量からペットの感情を判定するにゃ！
犬と猫で異なる判定ロジックを使うにゃ。
"""

import numpy as np
from collections import deque
from config import NORM_PARAMS


class EmotionEngine:
    """
    感情判定エンジンクラス
    
    機能:
    - 犬の感情判定（嬉しい/悲しい/怒り/お腹すいた/寂しい/警戒）
    - 猫の感情判定（ゴロゴロ/短いにゃー/長いにゃー/シャー/カチカチ/ガウガウ）
    - モード切り替え
    - 感情トレンド分析
    """
    
    def __init__(self, pet_type="dog", config=None):
        """
        感情エンジンを初期化するにゃ！
        
        Args:
            pet_type (str): "dog" または "cat"
            config (dict): DOG_CONFIG または CAT_CONFIG
        """
        self.pet_type = pet_type
        self.config = config
        self.emotions = list(config["emotions"].keys())
        self.history = deque(maxlen=20)  # 過去20回分の履歴
        self.norm_params = NORM_PARAMS
        
        print(f"🧠 感情エンジン初期化完了にゃ！")
        print(f"   ペットタイプ: {pet_type}")
        print(f"   検出可能な感情: {self.emotions}")
    
    def switch_mode(self, pet_type, config):
        """
        犬モードと猫モードを切り替えるにゃ！（重要！）
        
        Args:
            pet_type (str): "dog" または "cat"
            config (dict): 新しい設定（DOG_CONFIG or CAT_CONFIG）
        """
        self.pet_type = pet_type
        self.config = config
        self.emotions = list(config["emotions"].keys())
        self.history.clear()  # 履歴をリセット
        print(f"🔄 {pet_type}モードに切り替えたにゃ！")
        print(f"   検出可能な感情: {self.emotions}")
    
    def normalize(self, key, value):
        """
        特徴量を正規化するにゃ！
        
        Args:
            key (str): 特徴量の名前（pitch, duration, rms, zcr）
            value (float): 生の値
            
        Returns:
            float: 正規化された値
        """
        params = self.norm_params.get(key, {"mean": 0, "std": 1})
        if params["std"] > 0:
            return (value - params["mean"]) / params["std"]
        return 0
    
    def predict_dog(self, features):
        """
        犬の感情を判定するにゃ！
        
        Args:
            features (dict): 音声特徴量
            
        Returns:
            dict: 感情ごとの確率
        """
        scores = {emotion: 0.0 for emotion in self.emotions}
        
        for emotion in self.emotions:
            weights = self.config["emotions"][emotion].get("weight", {})
            
            # ピッチ（声の高さ）
            if "pitch" in weights:
                norm_pitch = self.normalize("pitch", features["pitch"])
                scores[emotion] += weights["pitch"] * norm_pitch
            
            # 長さ
            if "duration" in weights:
                norm_dur = self.normalize("duration", features["duration"])
                scores[emotion] += weights["duration"] * norm_dur
            
            # 音量
            if "rms" in weights:
                norm_rms = self.normalize("rms", features["rms"])
                scores[emotion] += weights["rms"] * norm_rms
            
            # ざらつき
            if "zcr" in weights:
                norm_zcr = self.normalize("zcr", features["zcr"])
                scores[emotion] += weights["zcr"] * norm_zcr
        
        return self._softmax(scores)
    
    def predict_cat(self, features, audio_engine=None):
        """
        猫の感情を判定するにゃ！
        
        Args:
            features (dict): 音声特徴量
            audio_engine (AudioEngine, optional): 追加検出用
            
        Returns:
            dict: 感情ごとの確率
        """
        scores = {emotion: 0.05 for emotion in self.emotions}  # ベース確率
        
        duration = features["duration"]
        pitch = features["pitch"]
        high_freq = features.get("high_freq_ratio", 0)
        
        # ゴロゴロ検出（低周波連続音）
        if audio_engine:
            purr_energy = audio_engine.detect_purr_band()
            if purr_energy > 0.2:
                scores["purr"] = min(0.9, purr_energy + 0.3)
        
        # 短いにゃー / 長いにゃー
        if duration < 0.3:
            scores["short_meow"] = 0.7 + (1 - pitch / 1000) * 0.2
        elif duration > 0.6:
            scores["long_meow"] = 0.6 + min(0.3, pitch / 1000)
        
        # シャー検出（高周波比率が高い）
        if high_freq > 0.35:
            scores["hiss"] = min(0.9, high_freq + 0.3)
        
        # カチカチ検出
        if audio_engine and audio_engine.detect_chatter():
            scores["chatter"] = 0.85
        
        # ガウガウ（低音＋長め）
        if pitch < 350 and duration > 0.4:
            scores["growl"] = 0.7
        
        return self._softmax(scores)
    
    def _softmax(self, scores):
        """
        スコアを確率に変換するにゃ！（ソフトマックス関数）
        
        Args:
            scores (dict): 感情ごとのスコア
            
        Returns:
            dict: 感情ごとの確率（合計=1）
        """
        # 負の値を防ぐために最小値を設定
        for k in scores:
            scores[k] = max(scores[k], 0.01)
        
        exp_scores = np.exp(list(scores.values()))
        probs = exp_scores / exp_scores.sum()
        
        result = {list(scores.keys())[i]: float(probs[i]) for i in range(len(scores))}
        self.history.append(result)
        
        return result
    
    def predict(self, features, audio_engine=None):
        """
        メイン予測関数（pet_typeに応じて分岐）
        
        Args:
            features (dict): 音声特徴量
            audio_engine (AudioEngine, optional): 猫モード時に使用
            
        Returns:
            dict: 感情ごとの確率
        """
        if self.pet_type == "dog":
            return self.predict_dog(features)
        else:
            return self.predict_cat(features, audio_engine)
    
    def get_top_emotion(self, predictions):
        """
        最も確率の高い感情を返すにゃ！
        
        Args:
            predictions (dict): predict()の戻り値
            
        Returns:
            tuple: (感情名, 確率)
        """
        if not predictions:
            return None, 0
        top = max(predictions.items(), key=lambda x: x[1])
        return top[0], top[1]
    
    def get_trend(self):
        """
        直近の感情トレンドを返すにゃ！
        
        Returns:
            str or None: 最も頻出した感情
        """
        if len(self.history) < 3:
            return None
        
        # 各感情の平均確率を計算
        avg = {}
        for emotion in self.emotions:
            avg[emotion] = np.mean([h[emotion] for h in self.history])
        
        return max(avg.items(), key=lambda x: x[1])[0]
    
    def get_history_summary(self):
        """
        感情履歴のサマリーを返すにゃ！
        
        Returns:
            dict: 各感情の平均確率
        """
        if len(self.history) == 0:
            return None
        
        summary = {}
        for emotion in self.emotions:
            summary[emotion] = np.mean([h[emotion] for h in self.history])
        
        return summary


# ========== テスト用コード ==========
if __name__ == "__main__":
    from config import DOG_CONFIG, CAT_CONFIG
    
    print("=" * 50)
    print("🧠 EmotionEngine 単体テスト 🧠")
    print("=" * 50)
    
    # テスト用の特徴量
    test_features = {
        'pitch': 523.0,
        'duration': 0.35,
        'rms': 0.12,
        'zcr': 0.08,
        'high_freq_ratio': 0.15
    }
    
    # 犬モードテスト
    print("\n🐕 犬モードテスト")
    engine_dog = EmotionEngine(pet_type="dog", config=DOG_CONFIG)
    result_dog = engine_dog.predict(test_features)
    print(f"   結果: {result_dog}")
    
    # 猫モードテスト
    print("\n🐱 猫モードテスト")
    engine_cat = EmotionEngine(pet_type="cat", config=CAT_CONFIG)
    result_cat = engine_cat.predict(test_features)
    print(f"   結果: {result_cat}")
    
    # モード切替テスト
    print("\n🔄 モード切替テスト")
    engine_dog.switch_mode("cat", CAT_CONFIG)
    print(f"   切り替え後: pet_type={engine_dog.pet_type}")
    print(f"   感情リスト: {engine_dog.emotions}")
    
    print("\n✅ テスト完了にゃ！")