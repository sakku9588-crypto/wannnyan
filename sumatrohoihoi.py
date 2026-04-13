#!/usr/bin/env python3
"""
LoLスマトロホイホイ v1.0 - League of Legends スマーフ・トロール検出ツール
バニラちゃんの怒りをスッキリさせるにゃ！(LoL特化版)
"""

import os
import re
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from datetime import datetime, timedelta
from collections import deque, Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import requests

# ==========================================
# 定数定義
# ==========================================
APP_VERSION = "v1.0.0-LOL"
SETTINGS_FILE = "lol_sumatoro_settings.json"
LOG_FILE = "lol_sumatoro_log.json"
CACHE_FILE = "lol_player_cache.json"
REGIONS = ["br1", "eun1", "euw1", "jp1", "kr", "la1", "la2", "na1", "oc1", "tr1", "ru"]
TIERS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]

DEFAULT_SETTINGS = {
    "riot_api_key": "",
    "region": "jp1",
    "discord_webhook": "",
    "auto_record": True,
    "auto_report": False,
    "ng_words": ["kill yourself", "uninstall", "trash", "noob", "int", "ff", "ez", "gg ez", "open mid", "report"],
    "suspicious_winrate": 70,
    "suspicious_kda": 5.0,
    "suspicious_cs": 8.5,
    "suspicious_level": 50,
    "comment_rate_threshold": 10,
    "watch_summoners": []
}

# ==========================================
# データクラス
# ==========================================
@dataclass
class SummonerData:
    """サモナーデータ"""
    name: str
    puuid: str
    summoner_id: str
    account_id: str
    level: int
    profile_icon_id: int
    revision_date: int
    
@dataclass
class LeagueEntry:
    """ランクデータ"""
    queue_type: str  # RANKED_SOLO_5x5, RANKED_FLEX_SR
    tier: str
    rank: str
    league_points: int
    wins: int
    losses: int
    winrate: float = 0.0
    
    def __post_init__(self):
        total = self.wins + self.losses
        self.winrate = (self.wins / total * 100) if total > 0 else 0

@dataclass
class MatchData:
    """試合データ"""
    match_id: str
    champion: str
    kills: int
    deaths: int
    assists: int
    kda: float
    win: bool
    cs: int
    game_duration: int
    cs_per_min: float
    vision_score: int
    damage_dealt: int
    damage_taken: int
    
    def __post_init__(self):
        self.kda = (self.kills + self.assists) / max(self.deaths, 1)
        self.cs_per_min = self.cs / (self.game_duration / 60) if self.game_duration > 0 else 0

@dataclass
class ChampionMastery:
    """チャンプマスタリー"""
    champion_id: int
    champion_name: str
    mastery_level: int
    mastery_points: int
    last_play_time: int

@dataclass
class SmurfAnalysis:
    """スマーフ分析結果"""
    is_smurf: bool
    confidence: int  # 0-100
    reasons: List[str]
    score: int
    summoner_name: str
    level: int
    rank: str
    winrate: float
    kda: float
    cs_per_min: float
    vision_score: float
    champion_stats: Dict[str, Any]

# ==========================================
# Riot APIクライアント
# ==========================================
class RiotAPIClient:
    def __init__(self, api_key: str, region: str = "jp1"):
        self.api_key = api_key
        self.region = region
        self.base_url = f"https://{region}.api.riotgames.com"
        self.platform_url = f"https://{region}.api.riotgames.com"
        self.request_count = 0
        self.last_request_time = 0
    
    def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """APIリクエストを送信（レート制限対策付き）"""
        # レート制限：1秒あたり20リクエストまで
        now = time.time()
        if now - self.last_request_time < 0.05:
            time.sleep(0.05)
        
        headers = {"X-Riot-Token": self.api_key}
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            self.request_count += 1
            self.last_request_time = time.time()
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                time.sleep(retry_after)
                return self._request(endpoint, params)
            else:
                return None
        except Exception as e:
            return None
    
    def get_summoner_by_name(self, name: str) -> Optional[SummonerData]:
        """サモナー名から情報を取得"""
        endpoint = f"/lol/summoner/v4/summoners/by-name/{name}"
        data = self._request(endpoint)
        if data:
            return SummonerData(
                name=data["name"],
                puuid=data["puuid"],
                summoner_id=data["id"],
                account_id=data["accountId"],
                level=data["summonerLevel"],
                profile_icon_id=data["profileIconId"],
                revision_date=data["revisionDate"]
            )
        return None
    
    def get_summoner_by_puuid(self, puuid: str) -> Optional[SummonerData]:
        """PUUIDから情報を取得"""
        endpoint = f"/lol/summoner/v4/summoners/by-puuid/{puuid}"
        data = self._request(endpoint)
        if data:
            return SummonerData(
                name=data["name"],
                puuid=data["puuid"],
                summoner_id=data["id"],
                account_id=data["accountId"],
                level=data["summonerLevel"],
                profile_icon_id=data["profileIconId"],
                revision_date=data["revisionDate"]
            )
        return None
    
    def get_league_entries(self, summoner_id: str) -> List[LeagueEntry]:
        """ランク情報を取得"""
        endpoint = f"/lol/league/v4/entries/by-summoner/{summoner_id}"
        data = self._request(endpoint)
        if data:
            entries = []
            for entry in data:
                entries.append(LeagueEntry(
                    queue_type=entry["queueType"],
                    tier=entry["tier"],
                    rank=entry["rank"],
                    league_points=entry["leaguePoints"],
                    wins=entry["wins"],
                    losses=entry["losses"]
                ))
            return entries
        return []
    
    def get_match_ids(self, puuid: str, count: int = 20, start: int = 0) -> List[str]:
        """試合ID一覧を取得"""
        endpoint = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"start": start, "count": count}
        data = self._request(endpoint, params)
        return data if data else []
    
    def get_match(self, match_id: str) -> Optional[dict]:
        """試合詳細を取得"""
        endpoint = f"/lol/match/v5/matches/{match_id}"
        return self._request(endpoint)
    
    def get_champion_masteries(self, puuid: str, count: int = 10) -> List[ChampionMastery]:
        """チャンプマスタリーを取得"""
        endpoint = f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
        data = self._request(endpoint)
        if data:
            masteries = []
            for m in data[:count]:
                masteries.append(ChampionMastery(
                    champion_id=m["championId"],
                    champion_name=f"Champion_{m['championId']}",
                    mastery_level=m["championLevel"],
                    mastery_points=m["championPoints"],
                    last_play_time=m["lastPlayTime"]
                ))
            return masteries
        return []

# ==========================================
# スマーフ検出エンジン（LoL特化）
# ==========================================
class LoLSmurfDetector:
    def __init__(self, settings: dict, api_client: RiotAPIClient):
        self.settings = settings
        self.api_client = api_client
        self.cache = self._load_cache()
    
    def _load_cache(self) -> dict:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def _get_champion_name(self, champion_id: int) -> str:
        """チャンピオンIDから名前を取得（簡易版）"""
        # 実際はstatic data APIを使うべきだが、簡易的にID→名前マッピング
        champions = {
            266: "Aatrox", 103: "Ahri", 84: "Akali", 12: "Alistar", 32: "Amumu",
            34: "Anivia", 1: "Annie", 523: "Aphelios", 22: "Ashe", 136: "AurelionSol",
            268: "Azir", 53: "Blitzcrank", 63: "Brand", 201: "Braum", 51: "Caitlyn",
            164: "Camille", 69: "Cassiopeia", 31: "Chogath", 42: "Corki", 122: "Darius",
            36: "DrMundo", 119: "Draven", 245: "Ekko", 60: "Elise", 28: "Evelynn",
            81: "Ezreal", 9: "Fiddlesticks", 114: "Fiora", 105: "Fizz", 3: "Galio",
            41: "Gangplank", 86: "Garen", 30: "Gragas", 79: "Graves", 104: "Graves",
            120: "Hecarim", 74: "Heimerdinger", 39: "Irelia", 427: "Ivern", 40: "Janna",
            59: "JarvanIV", 24: "Jax", 126: "Jayce", 202: "Jhin", 222: "Jinx",
            145: "Kaisa", 429: "Kalista", 43: "Karma", 30: "Karthus", 38: "Kassadin",
            55: "Katarina", 10: "Kayle", 141: "Kayn", 85: "Kennen", 121: "Khazix",
            203: "Kindred", 240: "Kled", 96: "KogMaw", 7: "Leblanc", 64: "LeeSin",
            89: "Leona", 127: "Lissandra", 236: "Lucian", 117: "Lulu", 99: "Lux",
            54: "Malphite", 90: "Malzahar", 57: "Maokai", 11: "MasterYi", 21: "MissFortune",
            62: "MonkeyKing", 82: "Mordekaiser", 25: "Morgana", 267: "Nami", 75: "Nasus",
            111: "Nautilus", 518: "Neeko", 76: "Nidalee", 56: "Nocturne", 20: "Nunu",
            2: "Olaf", 61: "Orianna", 516: "Ornn", 80: "Pantheon", 78: "Poppy",
            555: "Pyke", 246: "Qiyana", 133: "Quinn", 497: "Rakan", 33: "Rammus",
            421: "RekSai", 58: "Renekton", 107: "Rengar", 92: "Riven", 68: "Rumble",
            13: "Ryze", 360: "Samira", 113: "Sejuani", 235: "Senna", 147: "Seraphine",
            875: "Sett", 35: "Shaco", 98: "Shen", 102: "Shyvana", 27: "Singed",
            14: "Sion", 15: "Sivir", 72: "Skarner", 37: "Sona", 16: "Soraka",
            50: "Swain", 517: "Sylas", 134: "Syndra", 223: "TahmKench", 163: "Taliyah",
            91: "Talon", 44: "Taric", 17: "Teemo", 412: "Thresh", 18: "Tristana",
            48: "Trundle", 23: "Tryndamere", 4: "TwistedFate", 29: "Twitch", 77: "Udyr",
            6: "Urgot", 110: "Varus", 67: "Vayne", 45: "Veigar", 161: "Velkoz",
            254: "Vi", 112: "Viktor", 8: "Vladimir", 106: "Volibear", 19: "Warwick",
            62: "MonkeyKing", 498: "Xayah", 101: "Xerath", 5: "XinZhao", 157: "Yasuo",
            777: "Yone", 83: "Yorick", 350: "Yuumi", 154: "Zac", 238: "Zed",
            115: "Ziggs", 26: "Zilean", 142: "Zoe", 267: "Zyra"
        }
        return champions.get(champion_id, f"Champ_{champion_id}")
    
    def analyze_summoner(self, summoner_name: str, force_refresh: bool = False) -> SmurfAnalysis:
        """サモナーを分析してスマーフ判定"""
        cache_key = summoner_name.lower()
        
        if not force_refresh and cache_key in self.cache:
            cache_time = self.cache[cache_key].get("timestamp", 0)
            if time.time() - cache_time < 3600:  # 1時間キャッシュ
                return SmurfAnalysis(**self.cache[cache_key]["data"])
        
        # 1. サモナー基本情報取得
        summoner = self.api_client.get_summoner_by_name(summoner_name)
        if not summoner:
            return SmurfAnalysis(
                is_smurf=False,
                confidence=0,
                reasons=["サモナーが見つかりません"],
                score=0,
                summoner_name=summoner_name,
                level=0,
                rank="UNRANKED",
                winrate=0,
                kda=0,
                cs_per_min=0,
                vision_score=0,
                champion_stats={}
            )
        
        # 2. ランク情報取得
        league_entries = self.api_client.get_league_entries(summoner.summoner_id)
        solo_rank = next((e for e in league_entries if e.queue_type == "RANKED_SOLO_5x5"), None)
        
        rank_text = "UNRANKED"
        winrate = 0
        if solo_rank:
            rank_text = f"{solo_rank.tier} {solo_rank.rank}"
            winrate = solo_rank.winrate
        
        # 3. 最近の試合データ取得
        match_ids = self.api_client.get_match_ids(summoner.puuid, count=20)
        matches = []
        champion_stats = {}
        
        for match_id in match_ids:
            match_data = self.api_client.get_match(match_id)
            if match_data:
                # 自分の参加情報を抽出
                for participant in match_data.get("info", {}).get("participants", []):
                    if participant["puuid"] == summoner.puuid:
                        match = MatchData(
                            match_id=match_id,
                            champion=self._get_champion_name(participant["championId"]),
                            kills=participant["kills"],
                            deaths=participant["deaths"],
                            assists=participant["assists"],
                            win=participant["win"],
                            cs=participant["totalMinionsKilled"] + participant.get("neutralMinionsKilled", 0),
                            game_duration=match_data["info"]["gameDuration"],
                            vision_score=participant.get("visionScore", 0),
                            damage_dealt=participant["totalDamageDealtToChampions"],
                            damage_taken=participant["totalDamageTaken"]
                        )
                        matches.append(match)
                        
                        # チャンプ別集計
                        if match.champion not in champion_stats:
                            champion_stats[match.champion] = {"wins": 0, "games": 0, "kda_sum": 0}
                        champion_stats[match.champion]["games"] += 1
                        if match.win:
                            champion_stats[match.champion]["wins"] += 1
                        champion_stats[match.champion]["kda_sum"] += match.kda
                        break
        
        # 4. 統計計算
        total_games = len(matches)
        if total_games == 0:
            return SmurfAnalysis(
                is_smurf=False,
                confidence=0,
                reasons=["試合データがありません"],
                score=0,
                summoner_name=summoner_name,
                level=summoner.level,
                rank=rank_text,
                winrate=winrate,
                kda=0,
                cs_per_min=0,
                vision_score=0,
                champion_stats={}
            )
        
        avg_kda = sum(m.kda for m in matches) / total_games
        avg_cs = sum(m.cs_per_min for m in matches) / total_games
        avg_vision = sum(m.vision_score for m in matches) / total_games
        
        # チャンプ別勝率計算
        champion_winrates = {}
        for champ, stats in champion_stats.items():
            if stats["games"] >= 3:
                champion_winrates[champ] = (stats["wins"] / stats["games"]) * 100
        
        # 5. スマーフ判定
        score = 0
        reasons = []
        settings = self.settings
        
        # 勝率チェック
        if winrate > settings["suspicious_winrate"]:
            score += 30
            reasons.append(f"高勝率: {winrate:.1f}%")
        
        # レベルチェック（低レベルで高勝率）
        if summoner.level < settings["suspicious_level"] and winrate > 60:
            score += 25
            reasons.append(f"低レベル({summoner.level})で高勝率")
        
        # KDAチェック
        if avg_kda > settings["suspicious_kda"]:
            score += 25
            reasons.append(f"異常KDA: {avg_kda:.2f}")
        
        # CSチェック
        if avg_cs > settings["suspicious_cs"]:
            score += 20
            reasons.append(f"高CS/分: {avg_cs:.1f}")
        
        # 視界スコアチェック（高ランク指標）
        if avg_vision > 1.2:
            score += 10
            reasons.append(f"高視界スコア: {avg_vision:.1f}")
        
        # ランク帯とパフォーマンス乖離
        if solo_rank and solo_rank.tier in ["IRON", "BRONZE", "SILVER"]:
            if avg_kda > 4.0:
                score += 20
                reasons.append(f"低ランク({solo_rank.tier})で異常KDA")
            if avg_cs > 8.0:
                score += 15
                reasons.append(f"低ランク({solo_rank.tier})で異常CS")
        
        # チャンプ固有チェック
        high_winrate_champs = [champ for champ, wr in champion_winrates.items() if wr > 75]
        if high_winrate_champs:
            score += 15
            reasons.append(f"特定チャンプ高勝率: {', '.join(high_winrate_champs[:3])}")
        
        # コンフィデンス計算（0-100）
        confidence = min(100, score + (winrate - 50 if winrate > 50 else 0))
        
        # キャッシュ保存
        result = SmurfAnalysis(
            is_smurf=score >= 50,
            confidence=int(confidence),
            reasons=reasons,
            score=score,
            summoner_name=summoner.name,
            level=summoner.level,
            rank=rank_text,
            winrate=winrate,
            kda=avg_kda,
            cs_per_min=avg_cs,
            vision_score=avg_vision,
            champion_stats={k: {"winrate": v, "games": champion_stats[k]["games"]} 
                          for k, v in champion_winrates.items()}
        )
        
        self.cache[cache_key] = {
            "timestamp": time.time(),
            "data": {
                "is_smurf": result.is_smurf,
                "confidence": result.confidence,
                "reasons": result.reasons,
                "score": result.score,
                "summoner_name": result.summoner_name,
                "level": result.level,
                "rank": result.rank,
                "winrate": result.winrate,
                "kda": result.kda,
                "cs_per_min": result.cs_per_min,
                "vision_score": result.vision_score,
                "champion_stats": result.champion_stats
            }
        }
        self._save_cache()
        
        return result

# ==========================================
# トロール検出エンジン
# ==========================================
class TrollDetector:
    def __init__(self, settings: dict):
        self.settings = settings
        self.comment_history = deque(maxlen=200)
        self.user_comment_counts = {}
        self.reported_users = set()
    
    def analyze_comment(self, username: str, comment: str, channel_id: str) -> dict:
        """コメントを分析してトロール度を返す"""
        score = 0
        reasons = []
        
        comment_lower = comment.lower()
        
        # 1. NGワードチェック
        for ng in self.settings.get("ng_words", []):
            if ng.lower() in comment_lower:
                score += 30
                reasons.append(f"NGワード: {ng}")
                break
        
        # 2. 連投チェック
        now = time.time()
        if username not in self.user_comment_counts:
            self.user_comment_counts[username] = []
        self.user_comment_counts[username].append(now)
        
        recent = [t for t in self.user_comment_counts[username] if now - t < 60]
        self.user_comment_counts[username] = recent
        
        if len(recent) > self.settings.get("comment_rate_threshold", 10):
            score += 20
            reasons.append(f"連投: {len(recent)}回/分")
        
        # 3. 長文スパム
        if len(comment) > 300:
            score += 10
            reasons.append("長文スパム")
        
        # 4. 絵文字乱用
        emoji_count = len(re.findall(r'[\U00010000-\U0010ffff]', comment))
        if emoji_count > 15:
            score += 15
            reasons.append(f"絵文字乱用: {emoji_count}個")
        
        # 5. URL貼り付け
        if "http" in comment_lower or "www." in comment_lower:
            score += 25
            reasons.append("URL貼り付け")
        
        # 6. 特定キーワード（FF, open midなど）
        ff_keywords = ["ff", "open mid", "open", "surrender"]
        if any(kw in comment_lower for kw in ff_keywords):
            score += 15
            reasons.append("ネガティブ発言")
        
        return {
            "username": username,
            "comment": comment,
            "score": score,
            "is_troll": score >= 50,
            "reasons": reasons,
            "timestamp": datetime.now().isoformat()
        }
    
    def auto_reply(self, analysis: dict) -> Optional[str]:
        """トロールに自動返信"""
        if not analysis["is_troll"]:
            return None
        
        replies = [
            "にゃ〜ん 🐱 みんなで楽しくプレイしようにゃ！",
            "バニラちゃんが怒ってるにゃ！優しい言葉を使うにゃ〜",
            "このコミュニティでは、そんな言葉は必要ないにゃ 🤫",
            "ポイぼっくすは楽しい場所にゃ！ネガティブはポイっするにゃ！",
            "お互いリスペクトで盛り上げようにゃ 💪"
        ]
        import random
        return random.choice(replies)

# ==========================================
# メインGUI
# ==========================================
class LoLSumatoroHoihoyApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"🐾 LoLスマトロホイホイ {APP_VERSION} - LoLスマーフ・トロール対策")
        self.root.geometry("1100x800")
        self.root.configure(bg="#1a1a1a")
        
        self.settings = self._load_settings()
        self.api_client = None
        self.smurf_detector = None
        self.troll_detector = TrollDetector(self.settings)
        self.is_monitoring = False
        self.monitor_thread = None
        
        self._setup_ui()
        self._update_api_client()
    
    def _load_settings(self) -> dict:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(saved)
                    return merged
            except:
                pass
        return DEFAULT_SETTINGS.copy()
    
    def _save_settings(self):
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)
        self._log("💾 設定を保存しました", "success")
    
    def _update_api_client(self):
        api_key = self.settings.get("riot_api_key", "")
        region = self.settings.get("region", "jp1")
        if api_key:
            self.api_client = RiotAPIClient(api_key, region)
            self.smurf_detector = LoLSmurfDetector(self.settings, self.api_client)
            return True
        return False
    
    def _setup_ui(self):
        # ヘッダー
        header = tk.Frame(self.root, bg="#1a1a1a")
        header.pack(fill="x", pady=10)
        tk.Label(header, text="🐾 LoLスマトロホイホイ", font=("Meiryo", 24, "bold"),
                 fg="#ff5555", bg="#1a1a1a").pack()
        tk.Label(header, text="League of Legends スマーフ・トロール自動検出ツール", 
                 font=("Meiryo", 10), fg="#888888", bg="#1a1a1a").pack()
        
        # メインパネル
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#1a1a1a")
        main_paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 左パネル（設定・検索）
        left_frame = tk.Frame(main_paned, bg="#2a2a2a")
        main_paned.add(left_frame, width=400)
        
        # 設定フレーム
        settings_frame = tk.LabelFrame(left_frame, text="⚙️ API設定", bg="#2a2a2a", fg="white", font=("", 10, "bold"))
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(settings_frame, text="Riot APIキー:", bg="#2a2a2a", fg="white").pack(anchor="w", padx=10, pady=2)
        self.api_entry = tk.Entry(settings_frame, width=50, bg="#1a1a1a", fg="white", show="*")
        self.api_entry.insert(0, self.settings.get("riot_api_key", ""))
        self.api_entry.pack(padx=10, pady=2, fill="x")
        
        tk.Label(settings_frame, text="リージョン:", bg="#2a2a2a", fg="white").pack(anchor="w", padx=10, pady=2)
        self.region_combo = ttk.Combobox(settings_frame, values=REGIONS, state="readonly")
        self.region_combo.set(self.settings.get("region", "jp1"))
        self.region_combo.pack(padx=10, pady=2, fill="x")
        
        tk.Label(settings_frame, text="Discord Webhook:", bg="#2a2a2a", fg="white").pack(anchor="w", padx=10, pady=2)
        self.webhook_entry = tk.Entry(settings_frame, width=50, bg="#1a1a1a", fg="white")
        self.webhook_entry.insert(0, self.settings.get("discord_webhook", ""))
        self.webhook_entry.pack(padx=10, pady=2, fill="x")
        
        # 検出しきい値
        threshold_frame = tk.LabelFrame(left_frame, text="🎯 検出しきい値", bg="#2a2a2a", fg="#ffaa44", font=("", 9, "bold"))
        threshold_frame.pack(fill="x", padx=10, pady=5)
        
        th_frame = tk.Frame(threshold_frame, bg="#2a2a2a")
        th_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(th_frame, text="勝率閾値(%):", bg="#2a2a2a", fg="white", width=12, anchor="w").grid(row=0, column=0)
        self.winrate_entry = tk.Entry(th_frame, width=8, bg="#1a1a1a", fg="white")
        self.winrate_entry.insert(0, str(self.settings.get("suspicious_winrate", 70)))
        self.winrate_entry.grid(row=0, column=1, padx=5)
        
        tk.Label(th_frame, text="KDA閾値:", bg="#2a2a2a", fg="white", width=12, anchor="w").grid(row=0, column=2)
        self.kda_entry = tk.Entry(th_frame, width=8, bg="#1a1a1a", fg="white")
        self.kda_entry.insert(0, str(self.settings.get("suspicious_kda", 5.0)))
        self.kda_entry.grid(row=0, column=3, padx=5)
        
        tk.Label(th_frame, text="CS/分閾値:", bg="#2a2a2a", fg="white", width=12, anchor="w").grid(row=1, column=0)
        self.cs_entry = tk.Entry(th_frame, width=8, bg="#1a1a1a", fg="white")
        self.cs_entry.insert(0, str(self.settings.get("suspicious_cs", 8.5)))
        self.cs_entry.grid(row=1, column=1, padx=5)
        
        tk.Label(th_frame, text="レベル閾値:", bg="#2a2a2a", fg="white", width=12, anchor="w").grid(row=1, column=2)
        self.level_entry = tk.Entry(th_frame, width=8, bg="#1a1a1a", fg="white")
        self.level_entry.insert(0, str(self.settings.get("suspicious_level", 50)))
        self.level_entry.grid(row=1, column=3, padx=5)
        
        # 保存ボタン
        tk.Button(settings_frame, text="💾 設定保存", command=self._save_settings_ui,
                 bg="#4caf50", fg="white", font=("", 9)).pack(pady=10)
        
        # スマーフ検索フレーム
        search_frame = tk.LabelFrame(left_frame, text="🔍 スマーフ検索", bg="#2a2a2a", fg="#ffaa44", font=("", 10, "bold"))
        search_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(search_frame, text="サモナー名:", bg="#2a2a2a", fg="white").pack(anchor="w", padx=10, pady=2)
        self.search_entry = tk.Entry(search_frame, width=40, bg="#1a1a1a", fg="white")
        self.search_entry.pack(padx=10, pady=2, fill="x")
        
        btn_frame = tk.Frame(search_frame, bg="#2a2a2a")
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="🔍 分析開始", command=self._search_smurf,
                 bg="#ff9800", fg="white", font=("", 10, "bold")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🔄 キャッシュ更新", command=lambda: self._search_smurf(force_refresh=True),
                 bg="#2196f3", fg="white", font=("", 9)).pack(side="left", padx=5)
        
        # 監視リスト
        watch_frame = tk.LabelFrame(left_frame, text="👀 監視リスト", bg="#2a2a2a", fg="#00ff88", font=("", 9, "bold"))
        watch_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.watch_listbox = tk.Listbox(watch_frame, bg="#1a1a1a", fg="white", height=8)
        self.watch_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        for name in self.settings.get("watch_summoners", []):
            self.watch_listbox.insert(tk.END, name)
        
        add_frame = tk.Frame(watch_frame, bg="#2a2a2a")
        add_frame.pack(fill="x", padx=5, pady=5)
        self.watch_entry = tk.Entry(add_frame, width=25, bg="#1a1a1a", fg="white")
        self.watch_entry.pack(side="left", fill="x", expand=True)
        tk.Button(add_frame, text="➕", command=self._add_watch, bg="#4caf50", fg="white", width=3).pack(side="right")
        
        # 右パネル（結果表示）
        right_frame = tk.Frame(main_paned, bg="#2a2a2a")
        main_paned.add(right_frame, width=650)
        
        # ボタンフレーム
        btn_panel = tk.Frame(right_frame, bg="#2a2a2a")
        btn_panel.pack(fill="x", padx=10, pady=5)
        
        self.monitor_btn = tk.Button(btn_panel, text="▶ 監視開始", command=self._toggle_monitoring,
                                      bg="#28a745", fg="white", font=("", 10, "bold"))
        self.monitor_btn.pack(side="left", padx=5)
        
        self.status_label = tk.Label(btn_panel, text="● 停止中", fg="red", bg="#2a2a2a", font=("", 9))
        self.status_label.pack(side="left", padx=10)
        
        tk.Button(btn_panel, text="📂 レポートエクスポート", command=self._export_report,
                 bg="#607d8b", fg="white", font=("", 9)).pack(side="right", padx=5)
        
        # 結果表示タブ
        self.result_notebook = ttk.Notebook(right_frame)
        self.result_notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # スマーフ結果タブ
        self.smurf_tab = tk.Frame(self.result_notebook, bg="#1a1a1a")
        self.result_notebook.add(self.smurf_tab, text="🎯 スマーフ検出結果")
        
        self.smurf_text = scrolledtext.ScrolledText(self.smurf_tab, bg="#0a0a0a", fg="#00ff88",
                                                     font=("Consolas", 10), wrap=tk.WORD)
        self.smurf_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.smurf_text.tag_config("smurf", foreground="#ff5555", font=("Consolas", 10, "bold"))
        self.smurf_text.tag_config("normal", foreground="#00ff88")
        self.smurf_text.tag_config("warning", foreground="#ffaa44")
        
        # トロール結果タブ
        self.troll_tab = tk.Frame(self.result_notebook, bg="#1a1a1a")
        self.result_notebook.add(self.troll_tab, text="😾 トロール検出結果")
        
        self.troll_text = scrolledtext.ScrolledText(self.troll_tab, bg="#0a0a0a", fg="#ff8888",
                                                     font=("Consolas", 10), wrap=tk.WORD)
        self.troll_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.troll_text.tag_config("troll", foreground="#ff5555", font=("Consolas", 10, "bold"))
        self.troll_text.tag_config("normal", foreground="#888888")
        
        # ステータスバー
        status_bar = tk.Label(self.root, text="🐾 LoLスマトロホイホイ 準備完了", bg="#333", fg="#aaa", anchor="w", padx=10)
        status_bar.pack(side="bottom", fill="x")
        
        # 初期ログ
        self._log_smurf("🐾 LoLスマトロホイホイ v1.0 起動完了にゃ！", "normal")
        self._log_smurf("Riot APIキーを設定して「分析開始」でスマーフチェックにゃ！", "warning")
    
    def _save_settings_ui(self):
        self.settings["riot_api_key"] = self.api_entry.get().strip()
        self.settings["region"] = self.region_combo.get()
        self.settings["discord_webhook"] = self.webhook_entry.get().strip()
        self.settings["suspicious_winrate"] = int(self.winrate_entry.get())
        self.settings["suspicious_kda"] = float(self.kda_entry.get())
        self.settings["suspicious_cs"] = float(self.cs_entry.get())
        self.settings["suspicious_level"] = int(self.level_entry.get())
        self._save_settings()
        self._update_api_client()
        messagebox.showinfo("保存完了", "設定を保存しましたにゃ！")
    
    def _add_watch(self):
        name = self.watch_entry.get().strip()
        if name and name not in self.settings["watch_summoners"]:
            self.settings["watch_summoners"].append(name)
            self.watch_listbox.insert(tk.END, name)
            self.watch_entry.delete(0, tk.END)
            self._save_settings()
            self._log_smurf(f"➕ 監視リスト追加: {name}", "normal")
    
    def _log_smurf(self, msg: str, tag: str = "normal"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.smurf_text.insert(tk.END, f"[{timestamp}] {msg}\n", tag)
        self.smurf_text.see(tk.END)
    
    def _log_troll(self, msg: str, tag: str = "normal"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.troll_text.insert(tk.END, f"[{timestamp}] {msg}\n", tag)
        self.troll_text.see(tk.END)
    
    def _search_smurf(self, force_refresh: bool = False):
        summoner_name = self.search_entry.get().strip()
        if not summoner_name:
            messagebox.showwarning("入力不足", "サモナー名を入力してくださいにゃ！")
            return
        
        if not self.api_client:
            messagebox.showwarning("API未設定", "Riot APIキーを設定してくださいにゃ！")
            return
        
        self._log_smurf(f"🔍 分析開始: {summoner_name}", "normal")
        
        def search():
            result = self.smurf_detector.analyze_summoner(summoner_name, force_refresh)
            self.root.after(0, lambda: self._display_smurf_result(result))
        
        threading.Thread(target=search, daemon=True).start()
    
    def _display_smurf_result(self, result: SmurfAnalysis):
        self.smurf_text.insert(tk.END, "=" * 60 + "\n", "normal")
        self.smurf_text.insert(tk.END, f"📊 サモナー: {result.summoner_name}\n", "normal")
        self.smurf_text.insert(tk.END, f"   レベル: {result.level}\n", "normal")
        self.smurf_text.insert(tk.END, f"   ランク: {result.rank}\n", "normal")
        self.smurf_text.insert(tk.END, f"   勝率: {result.winrate:.1f}%\n", "normal")
        self.smurf_text.insert(tk.END, f"   KDA: {result.kda:.2f}\n", "normal")
        self.smurf_text.insert(tk.END, f"   CS/分: {result.cs_per_min:.1f}\n", "normal")
        self.smurf_text.insert(tk.END, f"   視界スコア: {result.vision_score:.1f}\n", "normal")
        
        if result.is_smurf:
            self.smurf_text.insert(tk.END, f"\n⚠️ スマーフ疑い！ (確信度: {result.confidence}%)\n", "smurf")
            self.smurf_text.insert(tk.END, f"   理由:\n", "smurf")
            for reason in result.reasons:
                self.smurf_text.insert(tk.END, f"   - {reason}\n", "smurf")
        else:
            self.smurf_text.insert(tk.END, f"\n✅ 通常プレイヤー (確信度: {result.confidence}%)\n", "normal")
        
        if result.champion_stats:
            self.smurf_text.insert(tk.END, f"\n📋 チャンプ別勝率:\n", "normal")
            for champ, stats in result.champion_stats.items():
                self.smurf_text.insert(tk.END, f"   {champ}: {stats['winrate']:.1f}% ({stats['games']}試合)\n", "normal")
        
        self.smurf_text.insert(tk.END, "=" * 60 + "\n\n", "normal")
        self.smurf_text.see(tk.END)
        
        # Discord通知
        if result.is_smurf and self.settings.get("discord_webhook"):
            self._send_discord_smurf_notification(result)
    
    def _send_discord_smurf_notification(self, result: SmurfAnalysis):
        """Discordにスマーフ通知を送信"""
        webhook = self.settings.get("discord_webhook")
        if not webhook:
            return
        
        try:
            data = {
                "content": f"🚨 **スマーフ疑いを検出！**\n"
                          f"サモナー: {result.summoner_name}\n"
                          f"ランク: {result.rank}\n"
                          f"勝率: {result.winrate:.1f}%\n"
                          f"KDA: {result.kda:.2f}\n"
                          f"確信度: {result.confidence}%\n"
                          f"理由: {', '.join(result.reasons)}",
                "username": "LoLスマトロホイホイ"
            }
            requests.post(webhook, json=data, timeout=5)
        except Exception as e:
            self._log_smurf(f"⚠️ Discord通知失敗: {e}", "warning")
    
    def _toggle_monitoring(self):
        if not self.is_monitoring:
            if not self.api_client:
                messagebox.showwarning("API未設定", "Riot APIキーを設定してくださいにゃ！")
                return
            
            self.is_monitoring = True
            self.monitor_btn.config(text="⏹ 監視停止", bg="#dc3545")
            self.status_label.config(text="● 監視中", fg="#00ff00")
            self._log_smurf("🚀 監視を開始しました", "success")
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
        else:
            self.is_monitoring = False
            self.monitor_btn.config(text="▶ 監視開始", bg="#28a745")
            self.status_label.config(text="● 停止中", fg="red")
            self._log_smurf("🛑 監視を停止しました", "success")
    
    def _monitor_loop(self):
        """監視ループ"""
        watch_list = self.settings.get("watch_summoners", [])
        if not watch_list:
            self._log_smurf("⚠️ 監視リストが空にゃ。設定タブで追加するにゃ！", "warning")
            while self.is_monitoring:
                time.sleep(10)
                if not self.is_monitoring:
                    break
            return
        
        self._log_smurf(f"👀 監視中: {', '.join(watch_list)}", "normal")
        
        while self.is_monitoring:
            for summoner_name in watch_list:
                if not self.is_monitoring:
                    break
                
                result = self.smurf_detector.analyze_summoner(summoner_name)
                if result.is_smurf:
                    self.root.after(0, lambda r=result: self._display_smurf_result(r))
                
                time.sleep(5)  # 監視間隔
            
            time.sleep(60)  # 1周終わったら60秒待機
    
    def _export_report(self):
        """レポートをエクスポート"""
        fp = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt"), ("CSVファイル", "*.csv")]
        )
        if not fp:
            return
        
        try:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write(f"LoLスマトロホイホイ レポート\n")
                f.write(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(self.smurf_text.get("1.0", tk.END))
            
            self._log_smurf(f"📄 レポート保存完了: {fp}", "success")
            messagebox.showinfo("完了", f"レポートを保存しましたにゃ！\n{fp}")
        except Exception as e:
            self._log_smurf(f"❌ 保存エラー: {e}", "warning")
            messagebox.showerror("エラー", f"保存に失敗しましたにゃ…\n{e}")

# ==========================================
# メイン実行
# ==========================================
def main():
    root = tk.Tk()
    app = LoLSumatoroHoihoyApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()