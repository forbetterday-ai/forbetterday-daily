"""
투자 인사이트 자동 생성 모듈
- 매일: ⭐2~3 기사 기반 섹터별 트렌드 요약
- 주간: 섹터별 분석 + TOP 10 기사 + 공통 테마
"""
import os
import json
from datetime import datetime, timedelta
from anthropic import Anthropic
from config.config import CLAUDE_API_KEY, KST
from src.logger import setup_logger

logger = setup_logger(__name__)

RATINGS_PATH = 'docs/ratings.json'
INSIGHTS_PATH = 'docs/insights.json'

if CLAUDE_API_KEY:
    os.environ['ANTHROPIC_API_KEY'] = CLAUDE_API_KEY


def _get_client():
    return Anthropic()


def load_ratings() -> dict:
    try:
        if os.path.exists(RATINGS_PATH):
            with open(RATINGS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('ratings', {})
    except Exception as e:
        logger.warning(f"평가 데이터 로드 실패: {e}")
    return {}


def load_insights() -> dict:
    try:
        if os.path.exists(INSIGHTS_PATH):
            with open(INSIGHTS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"인사이트 데이터 로드 실패: {e}")
    return {'daily': [], 'weekly': []}


def save_insights(insights: dict):
    try:
        os.makedirs('docs', exist_ok=True)
        with open(INSIGHTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(insights, f, ensure_ascii=False, indent=2)
        logger.info("인사이트 저장 완료")
    except Exception as e:
        logger.warning(f"인사이트 저장 실패: {e}")


def get_starred_articles(ratings: dict, days: int = 1) -> list:
    """⭐2~3 기사 추출 (최근 N일)"""
    cutoff = datetime.now(KST) - timedelta(days=days)
    starred = []

    for article_id, info in ratings.items():
        rating = info.get('rating', '')
        if rating not in ('star2', 'star3'):
            continue

        rated_at = info.get('ratedAt', '')
        if rated_at:
            try:
                rated_time = datetime.fromisoformat(rated_at.replace('Z', '+00:00'))
                if rated_time.timestamp() < cutoff.timestamp():
                    continue
            except Exception:
                pass

        starred.append({
            'id': article_id,
            'rating': rating,
            'title': info.get('title', ''),
            'source': info.get('source', ''),
            'link': info.get('link', ''),
            'watchlistItem': info.get('watchlistItem', ''),
        })

    return starred


def get_all_rated_articles(ratings: dict, days: int = 7) -> dict:
    """최근 N일간 모든 평가된 기사 (주간용)"""
    cutoff = datetime.now(KST) - timedelta(days=days)
    result = {'star1': [], 'star2': [], 'star3': [], 'dislike': []}

    for article_id, info in ratings.items():
        rating = info.get('rating', '')
        if rating not in result:
            continue

        rated_at = info.get('ratedAt', '')
        if rated_at:
            try:
                rated_time = datetime.fromisoformat(rated_at.replace('Z', '+00:00'))
                if rated_time.timestamp() < cutoff.timestamp():
                    continue
            except Exception:
                pass

        result[rating].append({
            'id': article_id,
            'title': info.get('title', ''),
            'source': info.get('source', ''),
            'link': info.get('link', ''),
            'watchlistItem': info.get('watchlistItem', ''),
        })

    return result


def generate_daily_insight(ratings: dict) -> dict:
    """매일 ⭐2~3 기사 기반 섹터별 트렌드 요약"""
    starred = get_starred_articles(ratings, days=1)

    if not starred:
        logger.info("오늘 ⭐2~3 평가 기사 없음 → 인사이트 스킵")
        return None

    # 섹터별 그룹핑
    by_source = {}
    for article in starred:
        source = article.get('source', '기타')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(article)

    # Claude API로 트렌드 요약 생성
    articles_text = ""
    for source, articles in by_source.items():
        articles_text += f"\n[{source}]\n"
        for a in articles:
            star = '⭐⭐⭐' if a['rating'] == 'star3' else '⭐⭐'
            wl = f" ({a['watchlistItem']})" if a.get('watchlistItem') else ''
            articles_text += f"- {star} {a['title']}{wl}\n"

    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"""다음은 투자자가 오늘 높게 평가한 뉴스 기사 목록입니다.

{articles_text}

위 기사들을 기반으로 다음을 한글로 작성해주세요:

1. **오늘의 섹터별 트렌드** (각 섹터 2~3줄)
   - 어떤 섹터에서 주요 움직임이 있는지
   - 투자자가 주목하고 있는 방향성

2. **주목할 연결고리** (1~2줄)
   - 서로 다른 섹터 간 연결되는 테마가 있다면

간결하고 핵심만 써주세요. 마크다운 형식으로 작성하세요."""
            }]
        )

        content = message.content[0].text
        now = datetime.now(KST)

        return {
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M'),
            'type': 'daily',
            'article_count': len(starred),
            'content': content,
            'sources': list(by_source.keys()),
        }

    except Exception as e:
        logger.error(f"일간 인사이트 생성 실패: {e}")
        return None


def generate_weekly_insight(ratings: dict) -> dict:
    """주간 리포트: 섹터별 분석 + TOP 10 + 공통 테마"""
    all_rated = get_all_rated_articles(ratings, days=7)

    top_articles = all_rated['star3'] + all_rated['star2']
    if not top_articles:
        logger.info("이번 주 ⭐2~3 평가 기사 없음 → 주간 리포트 스킵")
        return None

    # TOP 10 (star3 우선)
    top10 = top_articles[:10]

    # 워치리스트 언급 빈도
    watchlist_count = {}
    for rating_type in ['star1', 'star2', 'star3']:
        for article in all_rated[rating_type]:
            wl = article.get('watchlistItem', '')
            if wl:
                watchlist_count[wl] = watchlist_count.get(wl, 0) + 1

    # 소스별 분포
    source_count = {}
    for rating_type in ['star1', 'star2', 'star3']:
        for article in all_rated[rating_type]:
            src = article.get('source', '기타')
            source_count[src] = source_count.get(src, 0) + 1

    # Claude API로 주간 리포트 생성
    top10_text = ""
    for i, a in enumerate(top10, 1):
        star = '⭐⭐⭐' if a in all_rated['star3'] else '⭐⭐'
        wl = f" ({a['watchlistItem']})" if a.get('watchlistItem') else ''
        top10_text += f"{i}. {star} [{a.get('source', '')}] {a['title']}{wl}\n"

    watchlist_text = ""
    for item, count in sorted(watchlist_count.items(), key=lambda x: -x[1]):
        watchlist_text += f"- {item}: {count}회 언급\n"

    stats_text = f"""총 평가: ⭐ {len(all_rated['star1'])}개 · ⭐⭐ {len(all_rated['star2'])}개 · ⭐⭐⭐ {len(all_rated['star3'])}개 · 👎 {len(all_rated['dislike'])}개"""

    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": f"""다음은 투자자의 이번 주 뉴스 평가 데이터입니다.

{stats_text}

**TOP 10 기사:**
{top10_text}

**워치리스트 종목 언급 빈도:**
{watchlist_text if watchlist_text else '(데이터 없음)'}

위 데이터를 기반으로 다음을 한글로 작성해주세요:

1. **이번 주 섹터별 주요 움직임** (방산/우주, 반도체/AI, 에너지, 지정학 등)
   - 각 섹터 3~4줄로 핵심만

2. **워치리스트 분석**
   - 자주 언급된 종목의 의미
   - 언급 빈도 변화에서 읽을 수 있는 신호

3. **TOP 10 기사의 공통 테마**
   - 이번 주 투자자가 가장 주목한 방향성
   - 서로 다른 기사 간 연결고리

4. **다음 주 주목할 포인트** (2~3줄)

간결하고 핵심만 써주세요. 마크다운 형식으로 작성하세요."""
            }]
        )

        content = message.content[0].text
        now = datetime.now(KST)

        return {
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M'),
            'type': 'weekly',
            'article_count': len(top_articles),
            'dislike_count': len(all_rated['dislike']),
            'top10': [{'title': a['title'], 'source': a.get('source', ''), 'link': a.get('link', '')} for a in top10],
            'watchlist_frequency': watchlist_count,
            'content': content,
        }

    except Exception as e:
        logger.error(f"주간 인사이트 생성 실패: {e}")
        return None


def run_daily_insight():
    """매일 인사이트 생성"""
    ratings = load_ratings()
    if not ratings:
        logger.info("평가 데이터 없음 → 인사이트 스킵")
        return

    insight = generate_daily_insight(ratings)
    if not insight:
        return

    all_insights = load_insights()

    # 같은 날짜 기존 인사이트 교체
    all_insights['daily'] = [
        i for i in all_insights.get('daily', [])
        if i.get('date') != insight['date']
    ]
    all_insights['daily'].append(insight)

    # 최근 14일만 유지
    cutoff = (datetime.now(KST) - timedelta(days=14)).strftime('%Y-%m-%d')
    all_insights['daily'] = [
        i for i in all_insights['daily']
        if i.get('date', '') >= cutoff
    ]

    save_insights(all_insights)
    logger.info(f"일간 인사이트 생성 완료: {insight['article_count']}개 기사 기반")


def run_weekly_insight():
    """주간 인사이트 생성"""
    ratings = load_ratings()
    if not ratings:
        logger.info("평가 데이터 없음 → 주간 리포트 스킵")
        return

    insight = generate_weekly_insight(ratings)
    if not insight:
        return

    all_insights = load_insights()

    all_insights['weekly'] = all_insights.get('weekly', [])
    all_insights['weekly'].append(insight)

    # 최근 8주만 유지
    all_insights['weekly'] = all_insights['weekly'][-8:]

    save_insights(all_insights)
    logger.info(f"주간 인사이트 생성 완료: {insight['article_count']}개 기사 기반")
