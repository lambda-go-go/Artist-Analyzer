"""
시각화 및 리포트 생성 모듈
- 텍스트 리포트 생성 및 텍스트 파일 저장
- Matplotlib을 이용한 두 아티스트 비교 그래프 시각화
"""

import os
import platform
import matplotlib.pyplot as plt


def setup_korean_font():
    """운영체제에 맞춰 Matplotlib의 한글 폰트 및 마이너스 기호를 설정합니다."""
    system_name = platform.system()
    if system_name == "Windows":
        plt.rc("font", family="Malgun Gothic")
    elif system_name == "Darwin":
        plt.rc("font", family="AppleGothic")
    else:
        plt.rc("font", family="NanumGothic")
    plt.rcParams["axes.unicode_minus"] = False


def build_artist_report(data: dict) -> str:
    """단일 아티스트 분석 리포트 문자열을 포맷팅합니다."""
    lines = [
        "=" * 60,
        f" [Artist Analyzer] {data['name']} 분석 리포트",
        "=" * 60,
        f"- 아티스트명 : {data['name']}",
        f"- 인기도     : {data['popularity']} / 100",
        f"- 팔로워 수  : {data['followers']:,}명",
        f"- 장르       : {', '.join(data['genres']) if data['genres'] else '정보 없음'}",
        "-" * 60,
        " [대표 트랙 통계]",
        f"- 분석 트랙 수       : {data['track_count']}곡",
        f"- 트랙 평균 인기도   : {data['avg_track_popularity']} / 100",
        f"- 평균 곡 재생 시간  : {data['avg_duration_str']} ({data['avg_duration_sec']}초)",
    ]
    if data.get("top_track"):
        lines.append(f"- 최고 인기곡        : {data['top_track']['name']} (인기도: {data['top_track']['popularity']})")

    lines.append("-" * 60)
    lines.append(" [상위 트랙 목록]")
    if data.get("tracks"):
        for idx, t in enumerate(data.get("tracks", []), 1):
            lines.append(f" {idx:2d}. {t['name']:<35} | 인기도: {t['popularity']:2d} | 재생시간: {t['duration_str']}")
    else:
        lines.append(" (등록된 상위 트랙 데이터가 없습니다.)")
    lines.append("=" * 60)
    return "\n".join(lines)


def build_comparison_report(d1: dict, d2: dict) -> str:
    """두 아티스트의 지표 비교 리포트 문자열을 포맷팅합니다."""
    n1, n2 = d1["name"], d2["name"]
    fol1 = f"{d1['followers']:,}명"
    fol2 = f"{d2['followers']:,}명"
    lines = [
        "=" * 66,
        f" [Artist Analyzer] 전격 비교: {n1} vs {n2}",
        "=" * 66,
        f"{'지표':<20} | {n1:<20} | {n2:<20}",
        "-" * 66,
        f"{'인기도':<20} | {d1['popularity']:<20} | {d2['popularity']:<20}",
        f"{'팔로워 수':<20} | {fol1:<20} | {fol2:<20}",
        f"{'트랙 평균 인기도':<20} | {d1['avg_track_popularity']:<20} | {d2['avg_track_popularity']:<20}",
        f"{'평균 재생 시간':<20} | {d1['avg_duration_str']:<20} | {d2['avg_duration_str']:<20}",
    ]
    top1 = d1["top_track"]["name"] if d1.get("top_track") else "-"
    top2 = d2["top_track"]["name"] if d2.get("top_track") else "-"
    lines.append(f"{'대표 최고 인기곡':<18} | {top1[:18]:<20} | {top2[:18]:<20}")
    lines.append("=" * 66)
    return "\n".join(lines)


def save_report_file(content: str, filename: str) -> str:
    """리포트 내용을 깔끔한 텍스트 파일로 저장합니다."""
    safe_name = "".join([c if c.isalnum() or c in (" ", "_", "-") else "_" for c in filename])
    if not safe_name.endswith(".txt"):
        safe_name += ".txt"
    with open(safe_name, "w", encoding="utf-8") as f:
        f.write(content)
    return os.path.abspath(safe_name)


def render_comparison_charts(d1: dict, d2: dict, save_path: str = "artist_comparison.png"):
    """두 아티스트의 주요 지표를 시각적 그래프(막대 차트)로 비교하고 저장 및 표시합니다."""
    setup_korean_font()
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    fig.suptitle(f"아티스트 비교 분석: {d1['name']} VS {d2['name']}", fontsize=15, fontweight="bold")

    names = [d1["name"], d2["name"]]
    colors = ["#1DB954", "#191414"]

    # 1. 인기도 비교
    ax1 = axes[0, 0]
    bars1 = ax1.bar(names, [d1["popularity"], d2["popularity"]], color=colors, width=0.5)
    ax1.set_title("아티스트 자체 인기도 (0-100)")
    ax1.set_ylim(0, 110)
    ax1.bar_label(bars1, padding=3)

    # 2. 팔로워 수 비교
    ax2 = axes[0, 1]
    followers = [d1["followers"], d2["followers"]]
    bars2 = ax2.bar(names, followers, color=colors, width=0.5)
    ax2.set_title("팔로워 수")
    ax2.bar_label(bars2, labels=[f"{f:,}" for f in followers], padding=3)
    ax2.margins(y=0.15)

    # 3. 상위 트랙 평균 인기도
    ax3 = axes[1, 0]
    track_pops = [d1["avg_track_popularity"], d2["avg_track_popularity"]]
    bars3 = ax3.bar(names, track_pops, color=colors, width=0.5)
    ax3.set_title("대표 상위 트랙 평균 인기도 (0-100)")
    ax3.set_ylim(0, 110)
    ax3.bar_label(bars3, padding=3)

    # 4. 상위 트랙 평균 재생 시간
    ax4 = axes[1, 1]
    durations = [d1["avg_duration_sec"], d2["avg_duration_sec"]]
    bars4 = ax4.bar(names, durations, color=colors, width=0.5)
    ax4.set_title("대표 트랙 평균 재생 시간 (초)")
    dur_labels = [f"{d1['avg_duration_str']} ({d1['avg_duration_sec']}s)", f"{d2['avg_duration_str']} ({d2['avg_duration_sec']}s)"]
    ax4.bar_label(bars4, labels=dur_labels, padding=3)
    ax4.margins(y=0.15)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.show(block=False)
    plt.pause(1)
    return os.path.abspath(save_path)
