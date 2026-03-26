#!/usr/bin/env python3
"""
Daily News Brief 자동화 - 메인 오케스트레이션
Phase 3: 인사이트 자동 생성 포함
"""
import argparse
import sys
import os
import json
from datetime import datetime
from config.config import KST
from src.logger import setup_logger
from src.rss_fetcher import fetch_ft_rss, get_articles_summary
from src.translator import translate_articles
from src.page_generator import generate_briefing_page

logger = setup_logger(__name__)

CACHE_PATH = 'docs/articles_cache.json'
RATINGS_PATH = 'docs/ratings.json'


def load_cache() -> dict:
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
                        'summary_ko': article.get('summary_ko', ''),
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


def load_ratings() -> dict:
    try:
        if os.path.exists(RATINGS_PATH):
            with open(RATINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            ratings = data.get('ratings', {})
            logger.info(f"평가 데이터 로드: {len(ratings)}개")
            return ratings
    except Exception as e:
        logger.warning(f"평가 데이터 로드 실패: {e}")
    return {}


def get_dislike_patterns(ratings: dict) -> dict:
    disliked_links = set()
    disliked_title_words = {}

    for article_id, info in ratings.items():
        if info.get('rating') != 'dislike':
            continue
        link = info.get('link', '')
        if link:
            disliked_links.add(link)
        title = info.get('title', '')
        if title:
            words = [w for w in title.split() if len(w) >= 2]
            for word in words:
                word_lower = word.lower().strip('.,;:!?()[]{}"\'-')
                if len(word_lower) >= 2:
                    disliked_title_words[word_lower] = disliked_title_words.get(word_lower, 0) + 1

    frequent_words = {w for w, c in disliked_title_words.items() if c >= 3}
    logger.info(f"Dislike 패턴: {len(disliked_links)}개 URL, {len(frequent_words)}개 키워드")
    return {'links': disliked_links, 'frequent_words': frequent_words}


def filter_disliked_articles(articles_by_section: dict, dislike_patterns: dict) -> dict:
    filtered = {}
    removed_count = 0
    soft_dislike_count = 0
    disliked_links = dislike_patterns.get('links', set())
    frequent_words = dislike_patterns.get('frequent_words', set())

    for section, articles in articles_by_section.items():
        section_articles = []
        for article in articles:
            link = article.get('link', '')
            if link in disliked_links:
                removed_count += 1
                continue
            if frequent_words:
                title_lower = article.get('title', '').lower()
                match_count = sum(1 for w in frequent_words if w in title_lower)
                if match_count >= 2:
                    article['is_soft_dislike'] = True
                    soft_dislike_count += 1
            section_articles.append(article)
        if section_articles:
            filtered[section] = section_articles

    if removed_count > 0 or soft_dislike_count > 0:
        logger.info(f"Dislike 필터링: {removed_count}개 제거, {soft_dislike_count}개 흐리게 표시")
    return filtered


def apply_cache(articles_by_section: dict, cache: dict) -> tuple:
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
                article['title_ko'] = cache[link]['title_ko']
                article['summary_ko'] = cache[link].get('summary_ko', '')
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
    try:
        logger.info("=" * 60)
        logger.info(f"Daily News Brief 실행 시작 - {datetime.now(KST)}")
        logger.info("=" * 60)

        # 1단계: RSS 수집
        logger.info("\n[1/6] RSS 수집 중...")
        articles_by_section = fetch_ft_rss()
        if not articles_by_section:
            logger.error("수집된 기사가 없습니다.")
            return False
        logger.info(get_articles_summary(articles_by_section))

        # 2단계: Dislike 필터링
        logger.info("[2/6] Dislike 필터링 중...")
        ratings = load_ratings()
        if ratings:
            dislike_patterns = get_dislike_patterns(ratings)
            articles_by_section = filter_disliked_articles(articles_by_section, dislike_patterns)
        else:
            logger.info("  → 평가 데이터 없음 (필터링 스킵)")

        # 3단계: 캐시 확인
        logger.info("[3/6] 캐시 확인 중...")
        cache = load_cache()
        cached_sections, new_sections = apply_cache(articles_by_section, cache)

        # 4단계: 번역
        if new_sections:
            total_new = sum(len(v) for v in new_sections.values())
            logger.info(f"[4/6] 신규 {total_new}개 기사 번역 중...")
            translated_sections = translate_articles(new_sections)
        else:
            logger.info("[4/6] 신규 번역 대상 없음 (모두 캐시)")
            translated_sections = {}

        all_articles = merge_sections(cached_sections, translated_sections)

        # 5단계: 인사이트 생성 (비활성화 - API 비용 절약)
        logger.info("[5/6] 인사이트 생성 스킵")

        # 6단계: 웹페이지 생성
        logger.info("[6/6] 브리핑 웹페이지 생성 중...")
        page_path = generate_briefing_page(all_articles)
        if page_path:
            logger.info(f"✅ 웹페이지 생성 완료: {page_path}")

        save_cache(all_articles)

        logger.info("=" * 60)
        logger.info("✅ Daily News Brief 완료!")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"실행 실패: {str(e)}", exc_info=True)
        return False


def weekly_mode():
    """주간 리포트 생성 (일요일)"""
    try:
        logger.info("=" * 60)
        logger.info(f"주간 인사이트 리포트 생성 - {datetime.now(KST)}")
        logger.info("=" * 60)

        from src.insight_generator import run_weekly_insight
        run_weekly_insight()

        # 웹페이지 재생성 (인사이트 포함)
        logger.info("웹페이지 재생성 중...")
        cache = load_cache()
        if cache:
            # 캐시에서 기사 복원
            articles_by_section = {}
            for link, article in cache.items():
                section = article.get('section', '기타')
                if section not in articles_by_section:
                    articles_by_section[section] = []
                articles_by_section[section].append(article)
            generate_briefing_page(articles_by_section)

        logger.info("=" * 60)
        logger.info("✅ 주간 리포트 완료!")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"주간 리포트 실패: {str(e)}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(description="Daily News Brief 자동화 시스템")
    parser.add_argument('--mode', choices=['daily', 'weekly'], default='daily')
    args = parser.parse_args()

    from config.config import CLAUDE_API_KEY
    if not CLAUDE_API_KEY:
        logger.error("❌ CLAUDE_API_KEY 환경변수가 설정되지 않았습니다.")
        return False

    if args.mode == 'weekly':
        return weekly_mode()
    return daily_mode()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
