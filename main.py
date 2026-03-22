#!/usr/bin/env python3
"""
FT 데일리 브리핑 자동화 - 메인 오케스트레이션
"""
import argparse
import sys
import os
from datetime import datetime
from config.config import KST, ANALYSIS_RECIPIENT_EMAIL
from src.logger import setup_logger
from src.rss_fetcher import fetch_ft_rss, get_articles_summary
from src.translator import translate_articles
from src.email_sender import send_daily_brief
from src.article_analyzer import analyze_article
from src.page_generator import generate_briefing_page

logger = setup_logger(__name__)

def daily_mode():
    """일일 브리핑 모드: RSS → 번역 → 이메일 발송 → 웹페이지 생성"""
    try:
        logger.info("=" * 60)
        logger.info(f"FT 데일리 브리핑 실행 시작 - {datetime.now(KST)}")
        logger.info("=" * 60)
        
        # 1단계: RSS 수집
        logger.info("\n[1/4] RSS 수집 중...")
        articles_by_section = fetch_ft_rss()
        if not articles_by_section:
            logger.error("수집된 기사가 없습니다.")
            return False
        
        logger.info(get_articles_summary(articles_by_section))
        
        # 2단계: 번역
        logger.info("[2/4] 기사 번역 중...")
        articles_by_section = translate_articles(articles_by_section)
        
        # 3단계: 이메일 발송
        logger.info("[3/4] 이메일 발송 중...")
        email_success = send_daily_brief(articles_by_section)
        
        if email_success:
            logger.info("✅ 이메일 발송 완료!")
        else:
            logger.warning("⚠️ 이메일 발송 실패 (웹페이지 생성은 계속 진행)")
        
        # 4단계: 웹페이지 생성
        logger.info("[4/4] 브리핑 웹페이지 생성 중...")
        page_path = generate_briefing_page(articles_by_section)
        
        if page_path:
            logger.info(f"✅ 웹페이지 생성 완료: {page_path}")
        else:
            logger.warning("⚠️ 웹페이지 생성 실패")
        
        logger.info("=" * 60)
        logger.info("✅ 일일 브리핑 완료!")
        logger.info("=" * 60)
        return True
    
    except Exception as e:
        logger.error(f"일일 브리핑 실패: {str(e)}", exc_info=True)
        return False

def analyze_mode(url: str = None):
    """
    분석 모드: 특정 기사를 4섹션 분석
    
    Args:
        url: 분석할 기사 URL
    """
    try:
        logger.info("=" * 60)
        logger.info(f"기사 상세분석 모드 실행 - {datetime.now(KST)}")
        logger.info("=" * 60)
        
        # URL 입력
        if not url:
            print("\n📰 분석할 기사 URL을 입력하세요:")
            url = input("URL: ").strip()
            if not url:
                logger.error("URL을 입력해주세요.")
                return False
        
        # URL 검증
        if not url.startswith('http'):
            logger.error("유효한 URL을 입력해주세요.")
            return False
        
        # 제목 입력 (옵션)
        print("\n📝 기사 제목을 입력하세요 (선택):")
        title = input("제목 (또는 Enter): ").strip()
        if not title:
            title = "FT 기사"
        
        # 분석 실행
        logger.info(f"\n[분석] {title}")
        logger.info(f"URL: {url}")
        
        report = analyze_article(url, title, "")
        if not report:
            logger.error("분석 실패")
            return False
        
        logger.info("=" * 60)
        logger.info("✅ 분석 완료! output/ 디렉토리에서 확인하세요.")
        logger.info("=" * 60)
        
        # 콘솔에도 출력
        print("\n" + report)
        return True
    
    except Exception as e:
        logger.error(f"분석 실패: {str(e)}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="FT 데일리 브리핑 자동화 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python main.py --mode daily             # 일일 브리핑 실행
  python main.py --mode analyze           # 대화형 기사 분석
  python main.py --mode analyze --url "https://..."  # URL 직접 입력
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['daily', 'analyze'],
        default='daily',
        help='실행 모드 (기본값: daily)'
    )
    
    parser.add_argument(
        '--url',
        type=str,
        help='분석 모드에서 기사 URL 직접 입력'
    )
    
    args = parser.parse_args()
    
    # 환경 검증
    from config.config import CLAUDE_API_KEY
    if not CLAUDE_API_KEY:
        logger.error("❌ CLAUDE_API_KEY 환경변수가 설정되지 않았습니다.")
        logger.error("   .env 파일을 생성하고 Claude API 키를 설정하세요.")
        return False
    
    # 모드 실행
    if args.mode == 'daily':
        success = daily_mode()
    else:  # analyze
        success = analyze_mode(args.url)
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
