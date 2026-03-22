#!/usr/bin/env python3
"""
Daily News Brief 자동화 - 메인 오케스트레이션
"""
import argparse
import sys
import os
import json
from datetime import datetime, timedelta
from config.config import KST, RSS_HOURS_LOOKBACK
from src.logger import setup_logger
from src.rss_fetcher import fetch_ft_rss, get_articles_summary
from src.translator import translate_articles
from src.page_generator import generate_briefing_page

logger = setup_logger(__name__)

CACHE_PATH = 'docs/articles_cache.json'


def load_cache() -> dict:
    """캐시 파일 로드 (link를 키로 사용)"""
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            logger.info(f"캐시 로드 완료: {len(cache)}개 기사")
            return cache
    except Exception as e:
        logger.warning(f"캐시 로드 실패: {e}")
    return {}


def save_cache(articles_by_section: dict):
    """번역된 기사를 캐시에 저장 (link를 키로)"""
    try:
        cache = {}
        now = datetime.now(KST).isoformat()

        for section, articles in articles_by_section.items():
            for article in articles:
                link = article.get('link', '')
                if link:
                    cache[link] = {
                        'title': article.get('title', ''),
                        'title_ko': article.get('title_ko', ''),
                        'link': link,
                        'pub_date': article.get('pub_date', ''),
                        'summary': article.get('summary', ''),
                        'section': article.get('section', ''),
                        'has_watchlist': article.get('has_watchlist', False),
                        'watchlist_item': article.get('watchlist_item', ''),
                        'is_korean': article.get('is_korean', False),
                        'cached_at': now,
                    }

        os.makedirs('docs', exist_ok=True)
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"캐시 저장 완료: {len(cache)}개 기사")
    except Exception as e:
        logger.warning(f"캐시 저장 실패: {e}")


def apply_cache(articles_by_section: dict, cache: dict) -> tuple:
    """
    캐시에 있는 기사는 번역 결과를 재사용, 없는 기사만 번역 대상으로 분리

    Returns:
        (캐시 적용된 articles_by_section, 새로 번역 필요한 articles_by_section)
    """
    cached_sections = {}
    new_sections = {}
    cache_hit = 0
    cache_miss = 0

    for section, articles in articles_by_section.items():
        cached_list = []
        new_list = []

        for article in articles:
            link = article.get('link', '')
            if link in cache and cache[link].get('title_ko'):
                # 캐시 히트: 번역 결과 재사용
                article['title_ko'] = cache[link]['title_ko']
                article['has_watchlist'] = cache[link].get('has_watchlist', False)
                article['watchlist_item'] = cache[link].get('watchlist_item', '')
                cached_list.append(article)
                cache_hit += 1
            else:
                new_list.append(article)
                cache_miss += 1

        if cached_list:
            cached_sections[section] = cached_list
        if new_list:
            new_sections[section] = new_list

    logger.info(f"캐시 적용: {cache_hit}개 재사용, {cache_miss}개 신규 번역 필요")
    return cached_sections, new_sections


def merge_sections(cached: dict, translated: dict) -> dict:
    """캐시된 기사와 새로 번역된 기사를 합치기"""
    merged = {}
    all_sections = set(list(cached.keys()) + list(translated.keys()))

    for section in all_sections:
        articles = []
        if section in cached:
            articles.extend(cached[section])
        if section in translated:
            articles.extend(translated[section])
        if articles:
            merged[section] = articles

    return merged


def daily_mode():
    """일일 브리핑 모드: RSS → 캐시 확인 → 신규만 번역 → 웹페이지 생성"""
    try:
        logger.info("=" * 60)
        logger.info(f"Daily News Brief 실행 시작 - {datetime.now(KST)}")
        logger.info("=" * 60)

        # 1단계: RSS 수집
        logger.info("\n[1/4] RSS 수집 중...")
        articles_by_section = fetch_ft_rss()
        if not articles_by_section:
            logger.error("수집된 기사가 없습니다.")
            return False

        logger.info(get_articles_summary(articles_by_section))

        # 2단계: 캐시 확인
        logger.info("[2/4] 캐시 확인 중...")
        cache = load_cache()
        cached_sections, new_sections = apply_cache(articles_by_section, cache)

        # 3단계: 신규 기사만 번역
        if new_sections:
            total_new = sum(len(v) for v in new_sections.values())
            logger.info(f"[3/4] 신규 {total_new}개 기사 번역 중...")
            translated_sections = translate_articles(new_sections)
        else:
            logger.info("[3/4] 신규 번역 대상 없음 (모두 캐시)")
            translated_sections = {}

        # 합치기
        all_articles = merge_sections(cached_sections, translated_sections)

        # 4단계: 웹페이지 생성
        logger.info("[4/4] 브리핑 웹페이지 생성 중...")
        page_path = generate_briefing_page(all_articles)

        if page_path:
            logger.info(f"✅ 웹페이지 생성 완료: {page_path}")
        else:
            logger.warning("⚠️ 웹페이지 생성 실패")

        # 캐시 저장
        save_cache(all_articles)

        logger.info("=" * 60)
        logger.info("✅ Daily News Brief 완료!")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"실행 실패: {str(e)}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Daily News Brief 자동화 시스템",
    )
    parser.add_argument(
        '--mode',
        choices=['daily'],
        default='daily',
        help='실행 모드 (기본값: daily)'
    )
    args = parser.parse_args()

    from config.config import CLAUDE_API_KEY
    if not CLAUDE_API_KEY:
        logger.error("❌ CLAUDE_API_KEY 환경변수가 설정되지 않았습니다.")
        return False

    success = daily_mode()
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
