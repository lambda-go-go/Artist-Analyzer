"""
Spotify API 연동 모듈
- Client Credentials Flow 토큰 발급 및 자동 갱신
- 2024.11 보안 변경(403 및 필드 마스킹) 대응 하이브리드 데이터 추출
"""

import base64
import json
import math
import os
import re
import time
import requests

CREDENTIALS_FILE = "spotify_credentials.json"
WEB_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def load_credentials() -> tuple[str, str]:
    """환경변수, .env 파일 또는 로컬 JSON에서 Client ID와 Secret을 가져옵니다."""
    c_id, c_sec = os.environ.get("SPOTIFY_CLIENT_ID", ""), os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    if not (c_id and c_sec) and os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        if k.strip() == "SPOTIFY_CLIENT_ID": c_id = v.strip().strip('"\'')
                        elif k.strip() == "SPOTIFY_CLIENT_SECRET": c_sec = v.strip().strip('"\'')
        except Exception:
            pass
    if c_id and c_sec:
        return c_id, c_sec
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d.get("client_id", ""), d.get("client_secret", "")
        except Exception:
            pass
    return "", ""


def save_credentials(client_id: str, client_secret: str) -> None:
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
        json.dump({"client_id": client_id.strip(), "client_secret": client_secret.strip()}, f, indent=2)


def _calc_popularity(metric: int) -> int:
    return min(100, max(10, int(15 * math.log10(max(metric, 10)) - 25))) if metric and metric > 0 else 0


def scrape_web_artist(artist_id: str) -> dict:
    """스포티파이 웹 페이지에서 403 보안 제한으로 차단된 통계 및 톱 트랙을 보완 추출합니다."""
    try:
        url = f"https://open.spotify.com/artist/{artist_id}"
        res = requests.get(url, headers=WEB_HEADERS, timeout=6)
        if res.status_code != 200:
            return {}
        for s in re.findall(r"<script[^>]*>(.*?)</script>", res.text, re.DOTALL):
            s_clean = s.strip()
            if not s_clean.startswith("ey"):
                continue
            pad = len(s_clean) % 4
            if pad: s_clean += "=" * (4 - pad)
            payload = json.loads(base64.b64decode(s_clean).decode("utf-8"))
            items = payload.get("entities", {}).get("items", {})
            for _, v in items.items():
                stats = v.get("stats", {})
                top = v.get("discography", {}).get("topTracks", {}).get("items", [])
                tracks = []
                for it in top:
                    trk = it.get("track", {})
                    pc = int(trk.get("playcount") or 0)
                    dur = (trk.get("duration") or {}).get("totalMilliseconds", 0)
                    tracks.append({"name": trk.get("name"), "playcount": pc, "duration_ms": dur})
                return {"followers": stats.get("followers", 0), "monthly_listeners": stats.get("monthlyListeners", 0), "tracks": tracks}
    except Exception:
        pass
    return {}


class SpotifyClient:
    """Spotify Web API와 통신하는 클라이언트 클래스"""

    TOKEN_URL = "https://accounts.spotify.com/api/token"
    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.access_token = None
        self.token_expires_at = 0

    def authenticate(self) -> bool:
        """Spotify Client Credentials Flow로 액세스 토큰을 발급받습니다."""
        if not self.client_id or not self.client_secret:
            return False
        auth_b64 = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {auth_b64}", "Content-Type": "application/x-www-form-urlencoded"}
        try:
            res = requests.post(self.TOKEN_URL, data={"grant_type": "client_credentials"}, headers=headers, timeout=10)
            if res.status_code == 200:
                body = res.json()
                self.access_token = body.get("access_token")
                self.token_expires_at = time.time() + body.get("expires_in", 3600) - 60
                return True
        except Exception:
            pass
        return False

    def _get_headers(self) -> dict:
        """유효한 인증 헤더를 반환합니다. 만료 시 자동 재발급합니다."""
        if not self.access_token or time.time() >= self.token_expires_at:
            if not self.authenticate():
                raise ConnectionError("Spotify API 토큰 발급 또는 갱신에 실패했습니다.")
        return {"Authorization": f"Bearer {self.access_token}"}

    def search_artist(self, name: str) -> dict | None:
        """이름으로 아티스트를 검색하고 최적의 아티스트를 반환합니다."""
        url = f"{self.BASE_URL}/search"
        try:
            res = requests.get(url, headers=self._get_headers(), params={"q": name, "type": "artist", "limit": 10}, timeout=10)
            items = res.json().get("artists", {}).get("items", []) if res.status_code == 200 else []
            if not items:
                return None
            clean_name = name.strip().lower()
            exact = [a for a in items if a.get("name", "").strip().lower() == clean_name]
            return exact[0] if exact else items[0]
        except Exception:
            return None

    def search_durations(self, artist_name: str) -> dict:
        """검색 API를 활용해 트랙의 정확한 재생 시간을 가져옵니다."""
        durations = {}
        try:
            url = f"{self.BASE_URL}/search"
            res = requests.get(url, headers=self._get_headers(), params={"q": f"artist:{artist_name}", "type": "track", "limit": 10}, timeout=10)
            if res.status_code == 200:
                for t in res.json().get("tracks", {}).get("items", []):
                    durations[t.get("name", "").strip().lower()] = t.get("duration_ms", 0)
        except Exception:
            pass
        return durations

    def analyze_artist(self, artist_name: str) -> dict | None:
        """아티스트 상세 지표 및 상위 트랙 통계를 종합 분석합니다."""
        matched = self.search_artist(artist_name)
        if not matched:
            return None

        artist_id = matched.get("id")
        name = matched.get("name", artist_name)
        followers = (matched.get("followers") or {}).get("total") or 0
        pop = matched.get("popularity") or 0
        genres = matched.get("genres") or []

        web_info = scrape_web_artist(artist_id)
        if followers == 0 and web_info.get("followers"):
            followers = web_info["followers"]
        if pop == 0:
            metric = web_info.get("monthly_listeners") or followers
            pop = _calc_popularity(metric)

        raw_tracks = []
        try:
            res = requests.get(f"{self.BASE_URL}/artists/{artist_id}/top-tracks", headers=self._get_headers(), params={"market": "KR"}, timeout=6)
            if res.status_code == 200: raw_tracks = res.json().get("tracks", [])
        except Exception:
            pass

        tracks = []
        dur_map = self.search_durations(name)
        if not raw_tracks and web_info.get("tracks"):
            max_play = max([t.get("playcount", 1) for t in web_info["tracks"]], default=1) or 1
            for t in web_info["tracks"]:
                d_ms = t.get("duration_ms") or dur_map.get(t["name"].strip().lower(), 210000)
                t_pop = min(100, max(10, int(pop * (0.85 + 0.15 * (t["playcount"] / max_play)))))
                tracks.append({"name": t["name"], "popularity": t_pop, "duration_ms": d_ms, "duration_str": f"{(d_ms // 1000) // 60}:{(d_ms // 1000) % 60:02d}"})
        else:
            for t in raw_tracks:
                d_ms = t.get("duration_ms", 0)
                tracks.append({"name": t.get("name", "Unknown"), "popularity": t.get("popularity", 0), "duration_ms": d_ms, "duration_str": f"{(d_ms // 1000) // 60}:{(d_ms // 1000) % 60:02d}"})

        cnt = len(tracks)
        tot_dur = sum(t["duration_ms"] for t in tracks)
        tot_pop = sum(t["popularity"] for t in tracks)
        avg_pop = round(tot_pop / cnt, 1) if cnt > 0 else 0
        avg_sec = round(tot_dur / 1000 / cnt, 1) if cnt > 0 else 0
        avg_m, avg_s = int(avg_sec // 60), int(avg_sec % 60)

        return {
            "id": artist_id, "name": name, "followers": followers, "popularity": pop,
            "genres": genres, "tracks": tracks, "track_count": cnt,
            "avg_track_popularity": avg_pop, "avg_duration_sec": avg_sec,
            "avg_duration_str": f"{avg_m}:{avg_s:02d}",
            "top_track": max(tracks, key=lambda x: x["popularity"]) if tracks else None,
        }
