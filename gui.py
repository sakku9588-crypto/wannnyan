#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🐾 さく猫式・ペットトランスレーター - GUI画面 🐾

カスタムTkinterを使ったかわいいGUIを提供するにゃ！
ペットの感情をリアルタイムで表示するにゃ。
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext
import threading
import time
from datetime import datetime
from config import DOG_CONFIG, CAT_CONFIG
from pet_profiles import KEI_KUN, GEMI_NYAN

# GUIのテーマ設定
ctk.set_appearance_mode("dark")  # "dark" or "light"
ctk.set_default_color_theme("blue")  # テーマカラー


class PetTranslatorGUI:
    """
    ペットトランスレーターのメインGUIクラス
    
    機能:
    - リアルタイム感情表示
    - 犬/猫モード切り替え
    - 会話ログ表示
    - 音声録音コントロール
    """
    
    def __init__(self, audio_engine, emotion_engine, pet_profile, config):
        """
        GUIを初期化するにゃ！
        
        Args:
            audio_engine: AudioEngineのインスタンス
            emotion_engine: EmotionEngineのインスタンス
            pet_profile: PetProfileのインスタンス（ケイくん or ジェミ猫）
            config: DOG_CONFIG or CAT_CONFIG
        """
        self.audio_engine = audio_engine
        self.emotion_engine = emotion_engine
        self.pet_profile = pet_profile
        self.config = config
        self.is_listening = False
        
        # メインウィンドウ作成
        self.window = ctk.CTk()
        self.window.title(f"🐾 さく猫式・ペットトランスレーター - {pet_profile.name}")
        self.window.geometry("650x800")
        self.window.minsize(550, 700)
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # カスタムフォント（使えるものがあれば）
        self.title_font = ("Arial", 24, "bold")
        self.normal_font = ("Arial", 14)
        self.small_font = ("Arial", 11)
        
        # UI構築
        self.setup_ui()
        
        # 感情履歴（グラフ用）
        self.emotion_history = []
        self.max_history = 50
        
        # アニメーション用の変数
        self.animation_id = None
        
    def setup_ui(self):
        """UIコンポーネントを構築するにゃ！"""
        
        # ========== ヘッダーフレーム ==========
        header_frame = ctk.CTkFrame(self.window, corner_radius=15)
        header_frame.pack(pady=15, padx=20, fill="x")
        
        # ペットアイコン（大きく表示）
        self.pet_icon_label = ctk.CTkLabel(
            header_frame, 
            text="🐕" if self.pet_profile.pet_type == "dog" else "🐱", 
            font=("Arial", 72)
        )
        self.pet_icon_label.pack(side="left", padx=20, pady=10)
        
        # ペット情報表示
        info_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        info_frame.pack(side="left", padx=10, pady=10, fill="both", expand=True)
        
        self.pet_name_label = ctk.CTkLabel(
            info_frame, 
            text=self.pet_profile.name, 
            font=("Arial", 20, "bold")
        )
        self.pet_name_label.pack(anchor="w")
        
        self.pet_breed_label = ctk.CTkLabel(
            info_frame, 
            text=self.pet_profile.breed, 
            font=("Arial", 12)
        )
        self.pet_breed_label.pack(anchor="w")
        
        self.pet_age_label = ctk.CTkLabel(
            info_frame, 
            text=f"年齢: {self.pet_profile.age}", 
            font=("Arial", 11)
        )
        self.pet_age_label.pack(anchor="w")
        
        # ========== 感情表示エリア（メイン） ==========
        main_frame = ctk.CTkFrame(self.window, corner_radius=15)
        main_frame.pack(pady=15, padx=20, fill="both", expand=True)
        
        # 現在の感情（大きく表示）
        self.current_emotion_label = ctk.CTkLabel(
            main_frame, 
            text="🐾 待機中 🐾", 
            font=("Arial", 36, "bold")
        )
        self.current_emotion_label.pack(pady=20)
        
        # 翻訳結果（吹き出し風）
        self.translation_var = ctk.StringVar(value="🎤 翻訳開始ボタンを押してね 🎤")
        self.translation_label = ctk.CTkLabel(
            main_frame, 
            textvariable=self.translation_var,
            font=("Arial", 18),
            wraplength=500,
            justify="center"
        )
        self.translation_label.pack(pady=10)
        
        # ========== 感情確率バー ==========
        progress_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        progress_container.pack(pady=15, padx=20, fill="both", expand=True)
        
        ctk.CTkLabel(
            progress_container, 
            text="📊 感情分析結果", 
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # スクロール可能なフレーム（感情が多い場合）
        self.progress_scroll = ctk.CTkScrollableFrame(
            progress_container, 
            height=250
        )
        self.progress_scroll.pack(fill="both", expand=True)
        
        # 感情バーを格納する辞書
        self.progress_frames = {}
        self.create_emotion_bars()
        
        # ========== 会話ログ ==========
        log_frame = ctk.CTkFrame(self.window, corner_radius=15)
        log_frame.pack(pady=15, padx=20, fill="both", expand=True)
        
        # ログヘッダー
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            log_header, 
            text="📝 会話ログ", 
            font=("Arial", 14, "bold")
        ).pack(side="left")
        
        # ログクリアボタン
        self.clear_log_btn = ctk.CTkButton(
            log_header,
            text="🗑️ クリア",
            command=self.clear_log,
            width=60,
            height=25,
            font=("Arial", 11)
        )
        self.clear_log_btn.pack(side="right")
        
        # ログテキストエリア
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=8, 
            bg="#1e1e1e", 
            fg="#ffffff",
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        self.log_text.pack(padx=10, pady=5, fill="both", expand=True)
        
        # ========== コントロールボタン ==========
        control_frame = ctk.CTkFrame(self.window, corner_radius=15)
        control_frame.pack(pady=15, padx=20, fill="x")
        
        # メインボタン行
        button_row = ctk.CTkFrame(control_frame, fg_color="transparent")
        button_row.pack(pady=10)
        
        # 録音開始/停止ボタン（メイン）
        self.listen_btn = ctk.CTkButton(
            button_row, 
            text="🎤 翻訳開始", 
            command=self.toggle_listening,
            font=("Arial", 16, "bold"),
            width=160,
            height=45,
            corner_radius=25
        )
        self.listen_btn.pack(side="left", padx=10)
        
        # モード切替ボタン
        self.mode_btn = ctk.CTkButton(
            button_row, 
            text="🔄 モード切替", 
            command=self.switch_pet_mode,
            font=("Arial", 14),
            width=120,
            height=45,
            corner_radius=25,
            fg_color="#9b59b6",  # 紫色
            hover_color="#8e44ad"
        )
        self.mode_btn.pack(side="left", padx=10)
        
        # ステータス表示
        status_row = ctk.CTkFrame(control_frame, fg_color="transparent")
        status_row.pack(pady=5)
        
        self.status_label = ctk.CTkLabel(
            status_row, 
            text="⚪ 停止中", 
            font=("Arial", 12)
        )
        self.status_label.pack()
        
        # ヒント表示
        hint_label = ctk.CTkLabel(
            control_frame, 
            text="💡 ヒント: マイクに向かってペットの声を拾ってみてね！", 
            font=("Arial", 10),
            text_color="gray"
        )
        hint_label.pack(pady=5)
    
    def create_emotion_bars(self):
        """感情確率バーを作成するにゃ！"""
        # 既存のバーをクリア
        for widget in self.progress_scroll.winfo_children():
            widget.destroy()
        self.progress_frames.clear()
        
        # 新しいバーを作成
        for emotion, data in self.config["emotions"].items():
            # 感情ごとのフレーム
            frame = ctk.CTkFrame(self.progress_scroll)
            frame.pack(pady=5, padx=10, fill="x")
            
            # ラベル（絵文字 + 名前）
            label = ctk.CTkLabel(
                frame, 
                text=f"{data['emoji']} {data['name']}", 
                width=100,
                font=("Arial", 12)
            )
            label.pack(side="left", padx=10)
            
            # プログレスバー
            progress = ctk.CTkProgressBar(frame, width=300, height=18, corner_radius=9)
            progress.pack(side="left", padx=10, fill="x", expand=True)
            progress.set(0.0)
            
            # パーセント表示
            percent_label = ctk.CTkLabel(frame, text="0%", width=45, font=("Arial", 11))
            percent_label.pack(side="right", padx=10)
            
            self.progress_frames[emotion] = {
                "progress": progress,
                "percent": percent_label,
                "name": data['name'],
                "emoji": data['emoji']
            }
    
    def update_emotion_bars(self, predictions):
        """感情確率バーを更新するにゃ！"""
        for emotion, prob in predictions.items():
            if emotion in self.progress_frames:
                self.progress_frames[emotion]["progress"].set(prob)
                self.progress_frames[emotion]["percent"].configure(text=f"{prob*100:.0f}%")
    
    def update_emotion_display(self, top_emotion, confidence, predictions):
        """感情表示を更新するにゃ！"""
        emotion_data = self.config["emotions"].get(top_emotion, {})
        emoji = emotion_data.get("emoji", "🐾")
        name = emotion_data.get("name", top_emotion)
        
        # メイン感情ラベル
        self.current_emotion_label.configure(
            text=f"{emoji} {name} {confidence*100:.0f}% {emoji}"
        )
        
        # 翻訳テキスト（感情に合わせたフレーズ）
        phrases = emotion_data.get("phrases", ["..."])
        # 確率に応じてフレーズを選ぶ（高いほど最初のフレーズ）
        idx = min(int((1 - confidence) * len(phrases)), len(phrases) - 1)
        phrase = phrases[idx]
        
        # 吹き出し風の表示
        bubble_text = f"💬 「{phrase}」"
        self.translation_var.set(bubble_text)
        
        # ペットアイコンも感情に合わせて変化
        self.update_pet_icon(top_emotion)
    
    def update_pet_icon(self, emotion):
        """ペットアイコンを感情に合わせて更新するにゃ！"""
        # 犬のアイコンマップ
        dog_icons = {
            "happy": "🐕😊", "sad": "🐕😢", "angry": "🐕😠",
            "hungry": "🐕🍖", "lonely": "🐕🥺", "alert": "🐕⚠️"
        }
        # 猫のアイコンマップ
        cat_icons = {
            "purr": "😺✨", "short_meow": "😸", "long_meow": "😿",
            "hiss": "😾", "chatter": "😼🦅", "growl": "😤"
        }
        
        if self.pet_profile.pet_type == "dog":
            icon = dog_icons.get(emotion, "🐕")
        else:
            icon = cat_icons.get(emotion, "🐱")
        
        # アニメーション効果（少し大きめにして戻す）
        original_size = 72
        self.pet_icon_label.configure(text=icon)
    
    def on_audio_callback(self, features):
        """音声認識のコールバック（別スレッドから呼ばれる）"""
        if not self.is_listening:
            return
        
        # 感情判定
        predictions = self.emotion_engine.predict(features, self.audio_engine)
        top_emotion, confidence = self.emotion_engine.get_top_emotion(predictions)
        
        if top_emotion:
            # 履歴に追加
            self.emotion_history.append({
                "time": datetime.now(),
                "emotion": top_emotion,
                "confidence": confidence,
                "predictions": predictions.copy()
            })
            # 履歴が多すぎたら古いものを削除
            if len(self.emotion_history) > self.max_history:
                self.emotion_history.pop(0)
            
            # UI更新（メインスレッドで実行）
            self.window.after(0, self.update_ui, top_emotion, confidence, predictions)
    
    def update_ui(self, emotion, confidence, predictions):
        """UIを更新する（メインスレッド）"""
        # 感情バー更新
        self.update_emotion_bars(predictions)
        
        # 感情表示更新
        self.update_emotion_display(emotion, confidence, predictions)
        
        # ログ追加
        self.add_log_entry(emotion, confidence, predictions)
    
    def add_log_entry(self, emotion, confidence, predictions):
        """会話ログにエントリーを追加するにゃ！"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        emotion_data = self.config["emotions"].get(emotion, {})
        emoji = emotion_data.get("emoji", "🐾")
        name = emotion_data.get("name", emotion)
        
        # トップ感情以外の情報も少し表示
        other_emotions = []
        for e, prob in list(predictions.items())[:3]:
            if e != emotion and prob > 0.1:
                other_emotions.append(f"{e[:3]}{prob*100:.0f}%")
        
        other_text = f" (他: {', '.join(other_emotions)})" if other_emotions else ""
        
        log_line = f"[{timestamp}] {emoji} {name} {confidence*100:.0f}%{other_text}\n"
        
        # テキストエリアに追加
        self.log_text.insert(tk.END, log_line)
        self.log_text.see(tk.END)  # 自動スクロール
    
    def add_system_log(self, message, msg_type="info"):
        """システムログを追加するにゃ！"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        icon = "📌" if msg_type == "info" else "⚠️" if msg_type == "warning" else "❌"
        log_line = f"[{timestamp}] {icon} {message}\n"
        
        self.log_text.insert(tk.END, log_line)
        self.log_text.see(tk.END)
    
    def clear_log(self):
        """ログをクリアするにゃ！"""
        self.log_text.delete(1.0, tk.END)
        self.add_system_log("ログをクリアしました")
    
    def toggle_listening(self):
        """録音開始/停止を切り替えるにゃ！"""
        if not self.is_listening:
            # 録音開始
            try:
                success = self.audio_engine.start_recording(self.on_audio_callback)
                if success:
                    self.is_listening = True
                    self.listen_btn.configure(
                        text="⏹️ 翻訳停止", 
                        fg_color="#e74c3c",  # 赤色
                        hover_color="#c0392b"
                    )
                    self.status_label.configure(
                        text="🔴 録音中...（ペットの声を拾ってね）", 
                        text_color="#e74c3c"
                    )
                    self.add_system_log("🎤 翻訳を開始しました")
                    self.translation_var.set("🎧 聞いてるにゃ... 🎧")
                else:
                    self.add_system_log("❌ マイクが見つかりません！設定を確認してにゃ", "error")
            except Exception as e:
                self.add_system_log(f"❌ 録音開始エラー: {e}", "error")
        else:
            # 録音停止
            self.audio_engine.stop_recording()
            self.is_listening = False
            self.listen_btn.configure(
                text="🎤 翻訳開始", 
                fg_color="#1f538d",
                hover_color="#14375e"
            )
            self.status_label.configure(text="⚪ 停止中", text_color="green")
            self.add_system_log("⏹️ 翻訳を停止しました")
            self.translation_var.set("🎤 翻訳開始ボタンを押してね 🎤")
    
    def switch_pet_mode(self):
        """犬モードと猫モードを切り替えるにゃ！（GUI内でリアルタイム切替）"""
        if self.is_listening:
            # 録音中なら一旦停止
            self.toggle_listening()
        
        if self.pet_profile.pet_type == "dog":
            # 猫モードに切り替え
            self.pet_profile = GEMI_NYAN
            self.config = CAT_CONFIG
            self.emotion_engine.switch_mode("cat", CAT_CONFIG)
            self.add_system_log("🐱 ジェミ猫モードに切り替えたにゃ！")
            
            # ウィンドウタイトル変更
            self.window.title(f"🐾 さく猫式・ペットトランスレーター - ジェミ猫")
            
        else:
            # 犬モードに切り替え
            self.pet_profile = KEI_KUN
            self.config = DOG_CONFIG
            self.emotion_engine.switch_mode("dog", DOG_CONFIG)
            self.add_system_log("🐕 ケイくんモードに切り替えたにゃ！")
            
            # ウィンドウタイトル変更
            self.window.title(f"🐾 さく猫式・ペットトランスレーター - ケイくん")
        
        # UIを更新
        self.update_ui_for_mode_switch()
        
        # 感情履歴をクリア
        self.emotion_history.clear()
    
    def update_ui_for_mode_switch(self):
        """モード切り替え時にUIを更新するにゃ！"""
        # ペット情報更新
        self.pet_name_label.configure(text=self.pet_profile.name)
        self.pet_breed_label.configure(text=self.pet_profile.breed)
        self.pet_age_label.configure(text=f"年齢: {self.pet_profile.age}")
        
        # ペットアイコン更新
        self.pet_icon_label.configure(text="🐕" if self.pet_profile.pet_type == "dog" else "🐱")
        
        # 感情バーを再作成
        self.create_emotion_bars()
        
        # 表示をリセット
        self.current_emotion_label.configure(text="🐾 モード切替完了 🐾")
        self.translation_var.set("🔄 モードを切り替えたにゃ！翻訳を開始してね 🔄")
        
        # 確率バーをリセット
        for emotion in self.progress_frames.values():
            emotion["progress"].set(0.0)
            emotion["percent"].configure(text="0%")
    
    def on_closing(self):
        """ウィンドウを閉じるときの処理にゃ！"""
        if self.is_listening:
            self.audio_engine.stop_recording()
        self.window.destroy()
    
    def run(self):
        """GUIを起動するにゃ！"""
        self.add_system_log(f"🐾 {self.pet_profile.name}とおしゃべりする準備ができたにゃ！")
        self.add_system_log("💡 翻訳開始ボタンを押して、ペットに話しかけてみてね")
        self.window.mainloop()


# ========== テスト用コード ==========
if __name__ == "__main__":
    """
    単体テスト用のコードにゃ！
    python gui.py で実行できるにゃ。
    """
    import sys
    sys.path.append('.')
    
    from audio_engine import AudioEngine
    from emotion_engine import EmotionEngine
    from pet_profiles import KEI_KUN
    from config import DOG_CONFIG
    
    print("=" * 50)
    print("🐾 GUI 単体テスト 🐾")
    print("=" * 50)
    
    # ダミーのエンジンを作成
    audio_engine = AudioEngine(sample_rate=22050, duration=1.0)
    emotion_engine = EmotionEngine(pet_type="dog", config=DOG_CONFIG)
    
    # GUI起動
    gui = PetTranslatorGUI(audio_engine, emotion_engine, KEI_KUN, DOG_CONFIG)
    
    print("GUIが起動するにゃ！")
    print("（実際の音声認識は動かないけど、UIの確認はできるにゃ）")
    
    # テスト用のダミーデータ
    def test_display():
        import random
        test_predictions = {
            "happy": random.random(),
            "sad": random.random(),
            "angry": random.random(),
            "hungry": random.random(),
            "lonely": random.random(),
            "alert": random.random()
        }
        gui.update_ui("happy", 0.85, test_predictions)
        gui.window.after(3000, test_display)
    
    # テスト表示（3秒ごとに更新）
    # gui.window.after(1000, test_display)
    
    gui.run()