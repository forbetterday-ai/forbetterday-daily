"""
멀티 소스 RSS 수집 모듈
FT + Bloomberg + Reuters + TechCrunch + Space + Defense
"""
import feedparser
from datetime import datetime
from typing import Dict, List
from config.config import RSS_HOURS_LOOKBACK, KST
from src.logger import setup_logger
from src.utils import is_within_hours, format_publish_date

logger = setup_logger(__name__)

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
    'Reuters Business': 'https://feeds.reuters.com/reuters/businessNews',
    'Reuters Markets': 'https://feeds.reuters.com/reuters/marketsNews',
}

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
}

# 전체 피드
ALL_FEEDS = {
    **FT_FEEDS,
    **BLOOMBERG_FEEDS,
    **REUTERS_FEEDS,
    **TECHCRUNCH_FEEDS,
    **SPACE_FEEDS,
    **DEFENSE_FEEDS,
    **TECH_FEEDS,
}

# 피드 상태 추적
feed_status = {}


def get_feed_status() -> dict:
    """피드 상태 반환"""
    return feed_status


def fetch_ft_rss() -> Dict[str, List[dict]]:
    """
    전체 RSS 피드 수집 - 모든 소스에서 수집 및 중복 제거
    """
    global feed_status
    articles_by_section = {}
    seen_links = set()
    feed_status = {}

    for section_name, feed_url in ALL_FEEDS.items():
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
                }
                section_articles.append(article)

            if section_articles:
                articles_by_section[section_name] = section_articles
                feed_status[section_name] = 'ok'
                logger.info(f"  → {section_name}: {len(section_articles)}개 기사")
            else:
                feed_status[section_name] = 'empty'
                logger.info(f"  → {section_name}: 최근 24시간 기사 없음")

        except Exception as e:
            logger.error(f"RSS 수집 실패 ({section_name}): {str(e)}", exc_info=True)
            feed_status[section_name] = 'error'

    total = sum(len(v) for v in articles_by_section.values())
    logger.info(f"수집 완료: 총 {total}개 기사 ({len(articles_by_section)}개 섹션)")
    return articles_by_section


def get_articles_summary(articles_by_section: Dict[str, List[dict]]) -> str:
    """기사 수집 요약"""
    total_articles = sum(len(v) for v in articles_by_section.values())
    summary = f"총 {total_articles}개 기사 수집\n\n"

    for section, articles in articles_by_section.items():
        summary += f"- {section}: {len(articles)}개\n"

    unavailable = [k for k, v in feed_status.items() if v == 'unavailable']
    if unavailable:
        summary += f"\n⚠️ 접속 불가 피드: {', '.join(unavailable)}\n"

    return summary
