"""
멀티 소스 RSS 수집 모듈
Premium: FT + Bloomberg + Reuters + WSJ + GlobeNewswire + 개별기업 IR → KST 7~23시 매시간
Daily: TechCrunch + Space + Defense + Tech → KST 7시, 21시만
"""
import os
import json
import feedparser
from datetime import datetime
from typing import Dict, List
from config.config import RSS_HOURS_LOOKBACK, KST
from src.logger import setup_logger
from src.utils import is_within_hours, format_publish_date

logger = setup_logger(__name__)

# ===================================
# 그룹1: Premium (매시간 업데이트)
# ===================================

# ===== FT =====
FT_FEEDS = {
    'FT Markets': 'https://www.ft.com/markets?format=rss',
    'FT Companies': 'https://www.ft.com/companies?format=rss',
    'FT Technology': 'https://www.ft.com/technology?format=rss',
    'FT World': 'https://www.ft.com/world?format=rss',
    'FT US': 'https://www.ft.com/world/us?format=rss',
    'FT Opinion': 'https://www.ft.com/opinion?format=rss',
    'FT Global Economy': 'https://www.ft.com/global-economy?format=rss',
}

# ===== Bloomberg =====
BLOOMBERG_FEEDS = {
    'BBG Markets': 'https://feeds.bloomberg.com/markets/news.rss',
    'BBG Technology': 'https://feeds.bloomberg.com/technology/news.rss',
    'BBG Politics': 'https://feeds.bloomberg.com/politics/news.rss',
    'BBG Economics': 'https://feeds.bloomberg.com/economics/news.rss',
    'BBG Industries': 'https://feeds.bloomberg.com/industries/news.rss',
}

# ===== Reuters =====
REUTERS_FEEDS = {
    'Reuters Business': 'https://rss.app/feeds/26v2BmTDY6p2UAci.xml',
    'Reuters Markets': 'https://rss.app/feeds/ll09owyV9vLoceC6.xml',
}

# ===== WSJ =====
WSJ_FEEDS = {
    'WSJ US Business': 'https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness',
    'WSJ Markets': 'https://feeds.content.dowjones.io/public/rss/RSSMarketsMain',
    'WSJ Technology': 'https://feeds.content.dowjones.io/public/rss/RSSWSJD',
    'WSJ Economy': 'https://feeds.content.dowjones.io/public/rss/socialeconomyfeed',
}

# ===== GlobeNewswire 산업별 =====
GLOBENEWSWIRE_FEEDS = {
    'GN Aerospace & Defense': 'https://www.globenewswire.com/RssFeed/industry/5001-Aerospace%20and%20Defense/feedTitle/GlobeNewswire%20-%20Aerospace%20and%20Defense',
    'GN Semiconductors': 'https://www.globenewswire.com/RssFeed/industry/5009-Semiconductors/feedTitle/GlobeNewswire%20-%20Semiconductors',
    'GN Energy': 'https://www.globenewswire.com/RssFeed/industry/5004-Energy/feedTitle/GlobeNewswire%20-%20Energy',
}

# ===== 개별 기업 IR RSS =====
IR_FEEDS = {
    # NVIDIA (Q4 Inc 플랫폼)
    'IR NVIDIA': 'https://investor.nvidia.com/rss/news-releases.xml',
    # Broadcom (Q4 Inc 플랫폼)
    'IR Broadcom': 'https://investors.broadcom.com/rss/news-releases.xml',
    # Marvell (QuoteMedia 플랫폼)
    'IR Marvell': 'https://investor.marvell.com/rss/news-releases.xml',
    # Lumentum (Q4 Inc 플랫폼)
    'IR Lumentum': 'https://investor.lumentum.com/rss/news-releases.xml',
    # Coherent (자체 사이트 - GlobeNewswire 배포)
    'IR Coherent': 'https://www.coherent.com/company/investor-relations/rss/news-releases.xml',
    # Palantir (Q4 Inc 플랫폼)
    'IR Palantir': 'https://investors.palantir.com/rss/news-releases.xml',
    # Rocket Lab (Q4 Inc 플랫폼)
    'IR Rocket Lab': 'https://investors.rocketlabcorp.com/rss/news-releases.xml',
    # Bloom Energy (Q4 Inc 플랫폼)
    'IR Bloom Energy': 'https://investor.bloomenergy.com/rss/news-releases.xml',
    # Planet Labs (Q4 Inc 플랫폼)
    'IR Planet Labs': 'https://investors.planet.com/rss/news-releases.xml',
    # Tesla (Business Wire 배포)
    'IR Tesla': 'https://ir.tesla.com/rss/news-releases.xml',
    # Cheniere Energy (Q4 Inc 플랫폼)
    'IR Cheniere': 'https://lngir.cheniere.com/rss/news-releases.xml',
}

# ===================================
# 그룹2: Daily (7시, 21시만 업데이트)
# ===================================

# ===== TechCrunch =====
TECHCRUNCH_FEEDS = {
    'TechCrunch': 'https://techcrunch.com/feed/',
    'TC Startups': 'https://techcrunch.com/category/startups/feed/',
    'TC AI': 'https://techcrunch.com/category/artificial-intelligence/feed/',
    'TC Venture': 'https://techcrunch.com/category/venture/feed/',
}

# ===== Space =====
SPACE_FEEDS = {
    'SpaceNews': 'https://spacenews.com/feed/',
    'Space.com': 'https://www.space.com/feeds.xml',
    'Payload Space': 'https://payloadspace.com/feed/',
    'Satellite Today': 'https://www.satellitetoday.com/feed/',
}

# ===== Defense =====
DEFENSE_FEEDS = {
    'Breaking Defense': 'https://breakingdefense.com/feed/',
    'Defense News': 'https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml',
    'Defense One': 'https://www.defenseone.com/rss/all/',
    'DefenseScoop': 'https://defensescoop.com/feed/',
    'Air & Space Forces': 'https://www.airandspaceforces.com/feed/',
    'Space & Defense': 'https://spaceanddefense.io/feed/',
}

# ===== Tech =====
TECH_FEEDS = {
    'Ars Technica': 'https://feeds.arstechnica.com/arstechnica/index',
    'The Information': 'https://rss.app/feeds/WHiQ80N8WLtalVfX.xml',
}

# ===================================
# 피드 그룹 정의
# ===================================

PREMIUM_FEEDS = {
    **FT_FEEDS,
    **BLOOMBERG_FEEDS,
    **REUTERS_FEEDS,
    **WSJ_FEEDS,
    **GLOBENEWSWIRE_FEEDS,
    **IR_FEEDS,
}

DAILY_FEEDS = {
    **TECHCRUNCH_FEEDS,
    **SPACE_FEEDS,
    **DEFENSE_FEEDS,
    **TECH_FEEDS,
}

ALL_FEEDS = {
    **PREMIUM_FEEDS,
    **DAILY_FEEDS,
}

# 캐시 파일 경로 (Daily 그룹 기사를 저장)
DAILY_CACHE_FILE = 'docs/daily_cache.json'

# 피드 상태 추적
feed_status = {}


def get_feed_status() -> dict:
    """피드 상태 반환"""
    return feed_status


def is_korean_feed(section_name: str) -> bool:
    """한국 뉴스 피드인지 확인 (번역 불필요) - 현재 한국 피드 없음"""
    return False


def _get_feed_group() -> str:
    """
    FEED_GROUP 환경변수에 따라 피드 그룹 결정
    - 'premium': Premium만 (매시간)
    - 'all': 전체 피드 (KST 7시, 21시)
    """
    return os.getenv('FEED_GROUP', 'all')


def _get_active_feeds() -> dict:
    """현재 실행에서 수집할 피드 목록 반환"""
    feed_group = _get_feed_group()
    logger.info(f"피드 그룹: {feed_group}")

    if feed_group == 'premium':
        return PREMIUM_FEEDS
    else:
        return ALL_FEEDS


def _save_daily_cache(articles_by_section: Dict[str, List[dict]]) -> None:
    """Daily 그룹 기사를 캐시 파일에 저장"""
    daily_articles = {k: v for k, v in articles_by_section.items() if k in DAILY_FEEDS}
    if not daily_articles:
        return
    try:
        os.makedirs(os.path.dirname(DAILY_CACHE_FILE), exist_ok=True)
        with open(DAILY_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(daily_articles, f, ensure_ascii=False, indent=2)
        logger.info(f"Daily 캐시 저장: {sum(len(v) for v in daily_articles.values())}개 기사")
    except Exception as e:
        logger.warning(f"Daily 캐시 저장 실패: {e}")


def _load_daily_cache() -> Dict[str, List[dict]]:
    """저장된 Daily 그룹 기사 캐시 로드"""
    try:
        if os.path.exists(DAILY_CACHE_FILE):
            with open(DAILY_CACHE_FILE, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            total = sum(len(v) for v in cached.values())
            logger.info(f"Daily 캐시 로드: {total}개 기사 ({len(cached)}개 섹션)")
            return cached
        else:
            logger.info("Daily 캐시 파일 없음 (첫 실행)")
    except Exception as e:
        logger.warning(f"Daily 캐시 로드 실패: {e}")
    return {}


def fetch_ft_rss() -> Dict[str, List[dict]]:
    """
    RSS 피드 수집 - FEED_GROUP에 따라 선택적 수집 + 캐시 병합

    - FEED_GROUP=all: 전체 피드 수집 → Daily 캐시 저장
    - FEED_GROUP=premium: Premium만 수집 → Daily 캐시에서 로드하여 병합
    """
    global feed_status
    articles_by_section = {}
    seen_links = set()
    feed_status = {}

    feed_group = _get_feed_group()
    active_feeds = _get_active_feeds()

    for section_name, feed_url in active_feeds.items():
        try:
            logger.info(f"RSS 수집: {section_name} ({feed_url})")
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                logger.warning(f"  → {section_name}: 접속 실패, 건너뜀 ({feed.bozo_exception})")
                feed_status[section_name] = 'unavailable'
                continue

            section_articles = []

            for entry in feed.entries:
                link = entry.get('link', '')
                if link in seen_links:
                    continue
                seen_links.add(link)

                pub_date = entry.get('published', entry.get('updated', ''))
                if not is_within_hours(pub_date, RSS_HOURS_LOOKBACK):
                    continue

                article = {
                    'title': entry.get('title', 'N/A'),
                    'link': link,
                    'pub_date': format_publish_date(pub_date),
                    'summary': entry.get('summary', '')[:300],
                    'section': section_name,
                    'is_korean': False,
                }
                section_articles.append(article)

            if section_articles:
                articles_by_section[section_name] = section_articles
                feed_status[section_name] = 'ok'
                logger.info(f"  → {section_name}: {len(section_articles)}개 기사")
            else:
                feed_status[section_name] = 'empty'
                logger.info(f"  → {section_name}: 최근 기사 없음")

        except Exception as e:
            logger.error(f"RSS 수집 실패 ({section_name}): {str(e)}", exc_info=True)
            feed_status[section_name] = 'error'

    # 캐시 처리
    if feed_group == 'all':
        # 전체 실행 시 Daily 기사를 캐시에 저장
        _save_daily_cache(articles_by_section)
    elif feed_group == 'premium':
        # Premium만 실행 시 Daily 캐시를 로드하여 병합
        cached_daily = _load_daily_cache()
        for section_name, cached_articles in cached_daily.items():
            if section_name not in articles_by_section:
                articles_by_section[section_name] = cached_articles
                feed_status[section_name] = 'cached'
                # 캐시된 기사의 링크도 seen에 추가 (중복 방지)
                for article in cached_articles:
                    seen_links.add(article.get('link', ''))

    total = sum(len(v) for v in articles_by_section.values())
    logger.info(f"수집 완료: 총 {total}개 기사 ({len(articles_by_section)}개 섹션) [그룹: {feed_group}]")
    return articles_by_section


def get_articles_summary(articles_by_section: Dict[str, List[dict]]) -> str:
    """기사 수집 요약"""
    total_articles = sum(len(v) for v in articles_by_section.values())
    feed_group = _get_feed_group()
    summary = f"총 {total_articles}개 기사 수집 (모드: {feed_group})\n\n"

    for section, articles in articles_by_section.items():
        status = feed_status.get(section, '')
        cached_mark = ' (캐시)' if status == 'cached' else ''
        summary += f"- {section}: {len(articles)}개{cached_mark}\n"

    unavailable = [k for k, v in feed_status.items() if v == 'unavailable']
    if unavailable:
        summary += f"\n⚠️ 접속 불가 피드: {', '.join(unavailable)}\n"

    return summary
