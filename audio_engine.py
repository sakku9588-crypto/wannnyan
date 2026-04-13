#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎤 さく猫式・ペットトランスレーター - 音声処理エンジン 🎤

音声のキャプチャ、特徴量抽出、リアルタイム処理を担当するにゃ！
マイクから音声を取得して、感情判定エンジンが解析できる形に変換するにゃ。
"""

import numpy as np
import librosa
import sounddevice as sd
from collections import deque
import threading
import time
import warnings

# 警告を黙らせるにゃ（オプション）
warnings.filterwarnings("ignore", category=UserWarning)


class AudioEngine:
    """
    音声処理エンジンクラス
    
    機能:
    - マイクからのリアルタイム音声キャプチャ
    - 特徴量抽出（ピッチ、音量、MFCCなど）
    - 猫のゴロゴロ検出
    - カチカチ音検出
    
    使い方にゃ:
        engine = AudioEngine(sample_rate=22050, duration=1.0)
        engine.start_recording(callback_function)
        ...
        engine.stop_recording()
    """
    
    def __init__(self, sample_rate=22050, duration=1.0, device_id=None):
        """
        音声エンジンを初期化するにゃ！
        
        Args:
            sample_rate (int): サンプリングレート（Hz）。高いほど音質良いけど処理重い
            duration (float): 1回の分析にかける時間（秒）
            device_id (int, optional): 使用するマイクのデバイスID。Noneなら自動検出
        """
        self.sr = sample_rate
        self.duration = duration
        self.device_id = device_id
        self.buffer = deque(maxlen=int(self.sr * self.duration))
        self.stream = None
        self.is_recording = False
        self.callback = None
        
        # デバッグ用の統計情報
        self.stats = {
            "frames_processed": 0,
            "last_frame_time": 0,
            "error_count": 0
        }
        
        print(f"🎤 音声エンジン初期化完了にゃ！")
        print(f"   サンプリングレート: {self.sr} Hz")
        print(f"   分析間隔: {self.duration} 秒")
        if device_id is not None:
            print(f"   使用デバイス: {device_id}")
    
    def extract_features(self, audio):
        """
        音声波形から特徴量を抽出するにゃ！
        
        抽出する特徴量:
        - rms: 音量（強さ）
        - zcr: ゼロ交差率（音のザラつき）
        - pitch: ピッチ（声の高さ）
        - spectral_centroid: スペクトル重心（音の明るさ）
        - spectral_rolloff: スペクトルロールオフ（高周波の割合）
        - duration: 発声の長さ
        - mfcc_1~3: メル周波数ケプストラム係数（音色の特徴）
        - high_freq_ratio: 高周波エネルギー比率（シャー検出用）
        
        Args:
            audio (np.ndarray): 音声波形データ
            
        Returns:
            dict: 特徴量の辞書、または None（分析失敗時）
        """
        if len(audio) < self.sr * 0.1:
            return None
        
        try:
            # ========== 基本特徴量 ==========
            
            # RMS（音量）: 二乗平均平方根、音の強さ
            rms = librosa.feature.rms(y=audio).mean()
            
            # ZCR（ゼロ交差率）: 波形が0を跨ぐ回数、ざらつき感
            zcr = librosa.feature.zero_crossing_rate(y=audio).mean()
            
            # スペクトル重心: 音の明るさ（高いほど明るい音）
            spectral_centroid = librosa.feature.spectral_centroid(
                y=audio, sr=self.sr
            ).mean()
            
            # スペクトルロールオフ: 高周波成分の割合
            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=audio, sr=self.sr
            ).mean()
            
            # ========== ピッチ（声の高さ）検出 ==========
            pitches, magnitudes = librosa.piptrack(y=audio, sr=self.sr)
            pitch_mean = 0
            if np.any(pitches > 0):
                # 大きさで重み付けした平均ピッチ
                pitch_mean = np.average(
                pitches[pitches > 0], 
                weights=magnitudes[pitches > 0]
            )
            
            # ========== MFCC（音色の指紋） ==========
            # 音の特徴を13次元に圧縮したもの
            mfcc = librosa.feature.mfcc(y=audio, sr=self.sr, n_mfcc=5)
            mfcc_mean = mfcc.mean(axis=1)
            
            # ========== 発声検出 ==========
            # 音の立ち上がりを検出して鳴き声の長さを推定
            onset_frames = librosa.onset.onset_detect(
                y=audio, sr=self.sr, units='frames'
            )
            if len(onset_frames) > 0:
                duration_sec = len(onset_frames) * 512 / self.sr
            else:
                duration_sec = 0.1
            
            # ========== 高周波エネルギー比（猫のシャー検出用） ==========
            high_freq_ratio = self._high_freq_ratio(audio)
            
            # 特徴量を辞書にまとめる
            features = {
                'rms': float(np.clip(rms, 0, 1)),  # 0-1に制限
                'zcr': float(np.clip(zcr, 0, 0.5)),
                'pitch': float(pitch_mean),
                'spectral_centroid': float(spectral_centroid),
                'spectral_rolloff': float(spectral_rolloff),
                'duration': min(duration_sec, 1.0),
                'mfcc_1': float(mfcc_mean[0]),
                'mfcc_2': float(mfcc_mean[1]),
                'mfcc_3': float(mfcc_mean[2]),
                'high_freq_ratio': float(high_freq_ratio)
            }
            
            # 統計更新
            self.stats["frames_processed"] += 1
            
            return features
            
        except Exception as e:
            self.stats["error_count"] += 1
            print(f"⚠️ 特徴量抽出エラー: {e}")
            return None
    
    def _high_freq_ratio(self, audio):
        """
        高周波成分（3000Hz以上）のエネルギー比率を計算するにゃ！
        
        猫の「シャー」という音は高周波成分が多いのが特徴にゃ。
        
        Args:
            audio (np.ndarray): 音声波形
            
        Returns:
            float: 高周波エネルギー比率（0-1）
        """
        try:
            # 短時間フーリエ変換
            spec = np.abs(librosa.stft(audio))
            freqs = librosa.fft_frequencies(sr=self.sr)
            
            # 3000Hz以上のマスク
            high_mask = freqs > 3000
            
            if np.any(high_mask):
                high_energy = spec[high_mask].sum()
                total_energy = spec.sum()
                
                if total_energy > 0:
                    return high_energy / total_energy
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def detect_purr_band(self, audio=None):
        """
        猫のゴロゴロ帯域（20-150Hz）のエネルギーを検出するにゃ！
        
        ゴロゴロは低い周波数が連続するのが特徴にゃ。
        
        Args:
            audio (np.ndarray, optional): 音声波形。Noneならバッファから取得
            
        Returns:
            float: ゴロゴロ帯域のエネルギー比率（0-1）
        """
        if audio is None and len(self.buffer) > 0:
            audio = np.array(list(self.buffer))
        
        if audio is None or len(audio) < self.sr * 0.1:
            return 0.0
        
        try:
            spec = np.abs(librosa.stft(audio))
            freqs = librosa.fft_frequencies(sr=self.sr)
            
            # ゴロゴロ帯域（20-150Hz）
            purr_mask = (freqs >= 20) & (freqs <= 150)
            
            if np.any(purr_mask):
                purr_energy = spec[purr_mask].sum()
                total_energy = spec.sum()
                
                if total_energy > 0:
                    return purr_energy / total_energy
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def detect_chatter(self, audio=None):
        """
        猫のカチカチ音を検出するにゃ！
        
        鳥などを見た時の「カチカチ」という音は、
        ゼロ交差率が高く、音量の変動が大きいのが特徴にゃ。
        
        Args:
            audio (np.ndarray, optional): 音声波形。Noneならバッファから取得
            
        Returns:
            bool: カチカチ音が検出されたか
        """
        if audio is None and len(self.buffer) > 0:
            audio = np.array(list(self.buffer))
        
        if audio is None or len(audio) < self.sr * 0.1:
            return False
        
        try:
            # ZCR（ゼロ交差率）
            zcr = librosa.feature.zero_crossing_rate(y=audio).mean()
            
            # RMSの分散（音量の変動）
            rms = librosa.feature.rms(y=audio)
            rms_var = np.var(rms)
            
            # カチカチは高ZCR ＋ 音量変動が大きい
            if zcr > 0.12 and rms_var > 0.003:
                return True
            
            return False
            
        except Exception:
            return False
    
    def get_ambient_noise_level(self, duration=0.5):
        """
        環境ノイズレベルを測定するにゃ！
        
        マイクの感度調整や、静かな環境かどうかの確認に使うにゃ。
        
        Args:
            duration (float): 測定時間（秒）
            
        Returns:
            float: 平均RMS（環境ノイズレベル）
        """
        print(f"🔊 環境ノイズを測定するにゃ...（{duration}秒間）")
        
        # 一時的に録音して測定
        temp_buffer = []
        
        def temp_callback(indata, frames, time, status):
            temp_buffer.extend(indata[:, 0])
        
        temp_stream = sd.InputStream(
            samplerate=self.sr,
            channels=1,
            callback=temp_callback,
            blocksize=int(self.sr * 0.1)
        )
        
        temp_stream.start()
        time.sleep(duration)
        temp_stream.stop()
        temp_stream.close()
        
        if len(temp_buffer) > 0:
            audio = np.array(temp_buffer)
            rms = librosa.feature.rms(y=audio).mean()
            print(f"   環境ノイズレベル: {rms:.4f}")
            return rms
        
        return 0.05  # デフォルト値
    
    def _audio_callback(self, indata, frames, time, status):
        """
        sounddeviceの内部コールバック関数
        
        マイクから音声が来るたびに呼ばれるにゃ！
        """
        if status:
            # ステータスエラーがあれば表示（ただし頻繁すぎる場合は抑制）
            if self.stats["frames_processed"] % 100 == 0:
                print(f"⚠️ Audio status: {status}")
        
        # 音声データをバッファに追加
        audio = indata[:, 0]
        self.buffer.extend(audio)
        
        # バッファが指定時間分溜まったら特徴量抽出してコールバック
        if len(self.buffer) >= self.sr * self.duration and self.callback:
            # バッファを配列に変換
            window = np.array(list(self.buffer))
            
            # 特徴量抽出
            features = self.extract_features(window)
            
            if features:
                # コールバック関数を呼び出し
                self.callback(features)
            
            # バッファをクリア（オーバーラップ防止）
            self.buffer.clear()
            
            # 最終フレームの時間を記録
            self.stats["last_frame_time"] = time.currentTime
    
    def start_recording(self, callback):
        """
        録音を開始するにゃ！
        
        Args:
            callback (function): 特徴量抽出後に呼ばれる関数
                                def callback(features: dict) -> None
                                
        Returns:
            bool: 成功したらTrue
        """
        if self.is_recording:
            print("⚠️ すでに録音中にゃ！")
            return False
        
        self.callback = callback
        self.is_recording = True
        
        # バッファをクリア
        self.buffer.clear()
        
        try:
            import sounddevice as sd
            
            # 使用するデバイスを決定
            device = self.device_id
            if device is None:
                # 自動で入力デバイスを探す
                devices = sd.query_devices()
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0:
                        device = i
                        print(f"🎤 デバイス {i} を自動選択: {dev['name']}")
                        break
                
                if device is None:
                    print("❌ 入力デバイス（マイク）が見つからないにゃ！")
                    return False
            
            # 音声ストリームを開始
            self.stream = sd.InputStream(
                samplerate=self.sr,
                channels=1,
                callback=self._audio_callback,
                blocksize=int(self.sr * 0.1),
                device=device
            )
            self.stream.start()
            
            print(f"🎤 録音開始にゃ！")
            return True
            
        except Exception as e:
            print(f"❌ 録音開始エラー: {e}")
            self.is_recording = False
            return False
    
    def stop_recording(self):
        """
        録音を停止するにゃ！
        
        Returns:
            bool: 成功したらTrue
        """
        if not self.is_recording:
            print("⚠️ 録音中じゃないにゃ…")
            return False
        
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            self.is_recording = False
            self.callback = None
            
            print(f"⏹️ 録音停止にゃ！")
            print(f"   統計: {self.stats['frames_processed']}フレーム処理, "
                  f"{self.stats['error_count']}エラー")
            
            return True
            
        except Exception as e:
            print(f"❌ 録音停止エラー: {e}")
            return False
    
    def get_stats(self):
        """
        統計情報を取得するにゃ！
        
        Returns:
            dict: 統計情報
        """
        return self.stats.copy()
    
    def reset_stats(self):
        """統計情報をリセットするにゃ！"""
        self.stats = {
            "frames_processed": 0,
            "last_frame_time": 0,
            "error_count": 0
        }


# ========== テスト用コード ==========
if __name__ == "__main__":
    """
    単体テスト用のコードにゃ！
    python audio_engine.py で実行できるにゃ。
    """
    import time
    
    def test_callback(features):
        """テスト用コールバック"""
        print(f"\n🎉 特徴量抽出完了！")
        print(f"   ピッチ: {features['pitch']:.1f} Hz")
        print(f"   音量(RMS): {features['rms']:.4f}")
        print(f"   長さ: {features['duration']:.2f}秒")
        print(f"   高周波比率: {features['high_freq_ratio']:.2f}")
    
    print("=" * 50)
    print("🐾 AudioEngine 単体テスト 🐾")
    print("=" * 50)
    
    # エンジン作成
    engine = AudioEngine(sample_rate=22050, duration=1.0)
    
    # 環境ノイズ測定
    engine.get_ambient_noise_level(duration=1.0)
    
    # 録音開始
    print("\n🎤 5秒間録音するにゃ！何か話しかけてみてにゃ〜")
    engine.start_recording(test_callback)
    
    # 5秒間録音
    time.sleep(5)
    
    # 録音停止
    engine.stop_recording()
    
    print("\n✅ テスト完了にゃ！")