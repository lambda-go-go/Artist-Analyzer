"""
메인 실행 스크립트 (Artist Analyzer)
- CLI 인터페이스 및 Spotify API 자동 연결
- 아티스트 상세 분석 및 두 아티스트 지표 비교 (그래프 시각화)
- 레포트 텍스트 파일 저장 기능 및 자격 증명 재설정
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")

from spotify_api import SpotifyClient, load_credentials, save_credentials
from visualizer import (
    build_artist_report,
    build_comparison_report,
    save_report_file,
    render_comparison_charts,
)


def connect_spotify(force_reset: bool = False) -> SpotifyClient | None:
    """Spotify API 인증을 수행하고 연결 완료된 클라이언트를 반환합니다."""
    if not force_reset:
        c_id, c_secret = load_credentials()
        if c_id and c_secret:
            client = SpotifyClient(c_id, c_secret)
            if client.authenticate():
                print("\n=======================================================")
                print(" ✅ Spotify API 토큰 자동 발급 성공! 연결이 완료되었습니다.")
                print("=======================================================\n")
                return client
            print("\n⚠️ 저장된 API 자격 증명이 유효하지 않습니다. 다시 입력해주세요.")

    while True:
        print("\n[Spotify API 자격 증명 설정]")
        print("Spotify Developer Dashboard에서 발급받은 키를 입력하세요. (취소: 엔터)")
        c_id = input("• Client ID: ").strip()
        if not c_id:
            return None
        c_secret = input("• Client Secret: ").strip()
        if not c_secret:
            return None

        client = SpotifyClient(c_id, c_secret)
        print("인증 토큰 발급 시도 중...")
        if client.authenticate():
            save_ans = input("자격 증명을 저장하여 다음 실행 시 자동 로그인하시겠습니까? (y/n): ").strip().lower()
            if save_ans in ("y", "yes", ""):
                save_credentials(c_id, c_secret)
                print("자격 증명이 로컬 파일(spotify_credentials.json)에 저장되었습니다.")
            print("\n=======================================================")
            print(" ✅ Spotify API 토큰 발급 성공! 연결이 완료되었습니다.")
            print("=======================================================\n")
            return client
        print("❌ 인증에 실패했습니다. Client ID 및 Secret을 다시 확인해주세요.")


def run_single_artist_flow(client: SpotifyClient):
    """단일 아티스트 분석 및 리포트 저장 흐름을 처리합니다."""
    name = input("\n분석할 아티스트 이름을 입력하세요 (취소: 엔터): ").strip()
    if not name:
        return

    print(f"\n🔍 '{name}' 아티스트 데이터 수집 중...")
    data = client.analyze_artist(name)
    if not data:
        print(f"⚠️ '{name}' 아티스트를 찾을 수 없습니다. 철자를 확인해주세요.")
        return

    report = build_artist_report(data)
    print("\n" + report)

    save_choice = input("\n이 레포트를 깔끔한 텍스트 파일로 저장하시겠습니까? (y/n): ").strip().lower()
    if save_choice in ("y", "yes"):
        default_file = f"{data['name']}_report.txt"
        saved_path = save_report_file(report, default_file)
        print(f"📄 레포트 파일이 저장되었습니다: {saved_path}")


def run_comparison_flow(client: SpotifyClient):
    """두 아티스트 비교 분석 및 시각화 그래프 흐름을 처리합니다."""
    a1 = input("\n첫 번째 아티스트 이름을 입력하세요: ").strip()
    if not a1:
        return
    a2 = input("두 번째 아티스트 이름을 입력하세요: ").strip()
    if not a2:
        return

    print(f"\n🔍 '{a1}' 및 '{a2}' 데이터 수집 중...")
    d1 = client.analyze_artist(a1)
    if not d1:
        print(f"⚠️ 첫 번째 아티스트 '{a1}'을(를) 찾을 수 없습니다.")
        return
    d2 = client.analyze_artist(a2)
    if not d2:
        print(f"⚠️ 두 번째 아티스트 '{a2}'을(를) 찾을 수 없습니다.")
        return

    report = build_comparison_report(d1, d2)
    print("\n" + report)

    chart_file = f"comparison_{d1['name']}_vs_{d2['name']}.png"
    print("\n📊 두 아티스트 비교 그래프(시각화)를 생성합니다...")
    chart_path = render_comparison_charts(d1, d2, chart_file)
    print(f"📈 비교 그래프가 저장되었습니다: {chart_path}")

    save_choice = input("\n비교 레포트를 텍스트 파일로 저장하시겠습니까? (y/n): ").strip().lower()
    if save_choice in ("y", "yes"):
        text_file = f"comparison_{d1['name']}_vs_{d2['name']}.txt"
        saved_path = save_report_file(report, text_file)
        print(f"📄 비교 레포트 파일이 저장되었습니다: {saved_path}")


def main():
    """프로그램 메인 루프"""
    print("=" * 55)
    print("        🎵 Artist Analyzer - 음악 아티스트 분석기 🎵")
    print("=" * 55)

    try:
        client = None
        while not client:
            client = connect_spotify()
            if not client:
                print("API 인증이 필요합니다. 다시 시도해주세요.")
    except (KeyboardInterrupt, EOFError):
        print("\n프로그램을 종료합니다.")
        sys.exit(0)

    while True:
        print("\n" + "-" * 55)
        print(" [메뉴 선택]")
        print(" 1. 아티스트 상세 분석 및 리포트")
        print(" 2. 두 아티스트 주요 지표 전격 비교 (시각화 그래프)")
        print(" 3. Spotify API 자격 증명 재설정")
        print(" 4. 프로그램 종료")
        print("-" * 55)

        try:
            choice = input("원하시는 메뉴 번호를 입력하세요: ").strip()
            if not choice:
                continue
            if choice == "1":
                run_single_artist_flow(client)
            elif choice == "2":
                run_comparison_flow(client)
            elif choice == "3":
                new_client = connect_spotify(force_reset=True)
                if new_client:
                    client = new_client
                    print("✅ 자격 증명이 성공적으로 재설정되었습니다.")
                else:
                    print("자격 증명 재설정이 취소되었습니다. 기존 인증을 유지합니다.")
            elif choice in ("4", "q", "exit"):
                print("\nArtist Analyzer를 이용해 주셔서 감사합니다. 종료합니다.")
                break
            else:
                print("올바른 번호를 선택해주세요 (1 ~ 4).")
        except (KeyboardInterrupt, EOFError):
            print("\n\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"\n⚠️ 예상치 못한 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()
