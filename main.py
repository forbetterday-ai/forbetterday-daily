#!/usr/bin/env python3
"""
FT 데일리 브리핑 자동화 - 메인 오케스트레이션
"""
import argparse
import sys
import os
from datetime import datetime
from config.config import KST
from src.logger import setup_logger
from src.rss_fetcher import fetch_ft_rss, get_articles_summary
from src.translator import translate_articles
from src.page_generator import generate_briefing_page

logger = setup_logger(__name__)

def daily_mode():
    """일일 브리핑 모드: RSS → 번역 → 웹페이지 생성"""
    try:
        logger.info("=" * 60)
        logger.info(f"FT 데일리 브리핑 실행 시작 - {datetime.now(KST)}")
        logger.info("=" * 60)
        
        # 1단계: RSS 수집
        logger.info("\n[1/3] RSS 수집 중...")
        articles_by_section = fetch_ft_rss()
        if not articles_by_section:
            logger.error("수집된 기사가 없습니다.")
            return False
        
        logger.info(get_articles_summary(articles_by_section))
        
        # 2단계: 번역
        logger.info("[2/3] 기사 번역 중...")
        articles_by_section = translate_articles(articles_by_section)
        
        # 3단계: 웹페이지 생성
        logger.info("[3/3] 브리핑 웹페이지 생성 중...")
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

def main():
    parser = argparse.ArgumentParser(
        description="FT 데일리 브리핑 자동화 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python main.py --mode daily             # 일일 브리핑 실행
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['daily'],
        default='daily',
        help='실행 모드 (기본값: daily)'
    )
    
    args = parser.parse_args()
    
    # 환경 검증
    from config.config import CLAUDE_API_KEY
    if not CLAUDE_API_KEY:
        logger.error("❌ CLAUDE_API_KEY 환경변수가 설정되지 않았습니다.")
        return False
    
    success = daily_mode()
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
