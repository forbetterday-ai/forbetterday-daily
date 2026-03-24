"""
데일리 뉴스 브리핑 웹페이지 생성 모듈 - 시간순 정렬 + 소스태그 + 별점 + 인사이트
"""
import os
import re
import json
import hashlib
from datetime import datetime
from config.config import KST
from src.logger import setup_logger
from src.rss_fetcher import get_feed_status

logger = setup_logger(__name__)

SOURCE_GROUPS = {
    'FT': ['FT Markets', 'FT Companies', 'FT Technology', 'FT World', 'FT US', 'FT Opinion', 'FT Global Economy'],
    'Bloomberg': ['BBG Markets', 'BBG Technology', 'BBG Politics', 'BBG Economics', 'BBG Industries'],
    'Reuters': ['Reuters Business', 'Reuters Markets'],
    'WSJ': ['WSJ US Business', 'WSJ Markets', 'WSJ Technology', 'WSJ Economy'],
    'TechCrunch': ['TechCrunch', 'TC Startups', 'TC AI', 'TC Venture'],
    'Space': ['SpaceNews', 'Space.com', 'Payload Space', 'Satellite Today'],
    'Defense': ['Breaking Defense', 'Defense News', 'Defense One', 'DefenseScoop', 'Air & Space Forces', 'Space & Defense'],
    'Ars Technica': ['Ars Technica'],
    'The Information': ['The Information'],
    'GlobeNewswire': ['GN Aerospace & Defense', 'GN Semiconductors', 'GN Energy'],
    'IR': ['IR NVIDIA', 'IR Broadcom', 'IR Marvell', 'IR Lumentum', 'IR Coherent', 'IR Palantir', 'IR Rocket Lab', 'IR Bloom Energy', 'IR Planet Labs', 'IR Tesla', 'IR Cheniere'],
}

WORKER_URL = 'https://news-ratings.forbetterday.workers.dev'
INSIGHTS_PATH = 'docs/insights.json'


def _make_article_id(link: str) -> str:
    return hashlib.md5(link.encode()).hexdigest()[:12]


def _extract_date_str(pub_date: str) -> str:
    match = re.search(r'(\d{4})년\s*(\d{2})월\s*(\d{2})일', pub_date)
    if match:
        return f"{match.group(1)}년 {match.group(2)}월 {match.group(3)}일"
    return ""


def _get_source_group(section_name: str) -> str:
    for group, sections in SOURCE_GROUPS.items():
        if section_name in sections:
            return group
    return "기타"


def _sort_key(article):
    """pub_date 기준 정렬 키 (최신순)"""
    pd = article.get('pub_date', '')
    m = re.search(r'(\d{4})년\s*(\d{2})월\s*(\d{2})일\s*(\d{2}):(\d{2})', pd)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}{m.group(5)}"
    return '0'


def _load_insights() -> dict:
    try:
        if os.path.exists(INSIGHTS_PATH):
            with open(INSIGHTS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"인사이트 로드 실패: {e}")
    return {'daily': [], 'weekly': []}


def _markdown_to_html(text: str) -> str:
    """간단한 마크다운 → HTML 변환"""
    lines = text.split('\n')
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<br>')
            continue

        if stripped.startswith('### '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h4 class="insight-h4">{stripped[4:]}</h4>')
        elif stripped.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3 class="insight-h3">{stripped[3:]}</h3>')
        elif stripped.startswith('# '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2 class="insight-h2">{stripped[2:]}</h2>')
        elif stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html_lines.append('<ul class="insight-list">')
                in_list = True
            content = stripped[2:]
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f'<li>{content}</li>')
        elif re.match(r'^\d+\.', stripped):
            if not in_list:
                html_lines.append('<ul class="insight-list">')
                in_list = True
            content = re.sub(r'^\d+\.\s*', '', stripped)
            content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
            html_lines.append(f'<li>{content}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            stripped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            html_lines.append(f'<p class="insight-p">{stripped}</p>')

    if in_list:
        html_lines.append('</ul>')

    return '\n'.join(html_lines)


def _generate_insights_html(insights: dict) -> str:
    daily_list = sorted(insights.get('daily', []), key=lambda x: x.get('date', ''), reverse=True)
    weekly_list = sorted(insights.get('weekly', []), key=lambda x: x.get('date', ''), reverse=True)

    if not daily_list and not weekly_list:
        return '<div class="insight-empty">📊 아직 인사이트가 없습니다.<br><span style="font-size:0.75rem">기사에 별점을 주면 자동으로 생성됩니다.</span></div>'

    html = ''

    if weekly_list:
        latest_weekly = weekly_list[0]
        html += f'''<div class="insight-card weekly">
<div class="insight-badge">📊 주간 리포트</div>
<div class="insight-date">{latest_weekly.get('date', '')} · {latest_weekly.get('article_count', 0)}개 기사 분석</div>
<div class="insight-content">{_markdown_to_html(latest_weekly.get('content', ''))}</div>
</div>'''

    for insight in daily_list[:7]:
        html += f'''<div class="insight-card daily">
<div class="insight-badge">💡 일간 트렌드</div>
<div class="insight-date">{insight.get('date', '')} {insight.get('time', '')} · {insight.get('article_count', 0)}개 ⭐ 기사</div>
<div class="insight-content">{_markdown_to_html(insight.get('content', ''))}</div>
</div>'''

    if len(weekly_list) > 1:
        html += '<div class="insight-divider">이전 주간 리포트</div>'
        for w in weekly_list[1:4]:
            html += f'''<div class="insight-card weekly old">
<div class="insight-badge">📊 주간 리포트</div>
<div class="insight-date">{w.get('date', '')} · {w.get('article_count', 0)}개 기사 분석</div>
<div class="insight-content">{_markdown_to_html(w.get('content', ''))}</div>
</div>'''

    return html


def generate_briefing_page(articles_by_section: dict):
    now = datetime.now(KST)
    date_str = now.strftime('%Y년 %m월 %d일')
    time_str = now.strftime('%H:%M')
    weekday_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
    weekday = weekday_map[now.weekday()]
    total_articles = sum(len(v) for v in articles_by_section.values())

    insights = _load_insights()
    insights_html = _generate_insights_html(insights)

    status = get_feed_status()
    unavailable_feeds = [k for k, v in status.items() if v in ('unavailable', 'error')]
    status_html = ""
    if unavailable_feeds:
        feeds_list = ", ".join(unavailable_feeds)
        status_html = f'<div class="status-alert">⚠️ 접속불가: {feeds_list}</div>'

    all_dates = set()
    for section, articles in articles_by_section.items():
        for article in articles:
            d = _extract_date_str(article.get('pub_date', ''))
            if d:
                all_dates.add(d)
    sorted_dates = sorted(all_dates, reverse=True)

    date_items = '<li><button class="sb-btn date-btn active" onclick="filterDate(\'all\')">전체</button></li>'
    for d in sorted_dates:
        date_items += f'<li><button class="sb-btn date-btn" onclick="filterDate(\'{d}\')">{d}</button></li>'

    source_items = '<li><button class="sb-btn source-btn active" onclick="filterSource(\'all\')">Show All</button></li>'
    for group_name, section_list in SOURCE_GROUPS.items():
        count = 0
        for s in section_list:
            if s in articles_by_section:
                count += len(articles_by_section[s])
        if count > 0:
            source_items += f'<li><button class="sb-btn source-btn" onclick="filterSource(\'{group_name}\')">{group_name} <span class="sb-count">{count}</span></button></li>'

    # 모든 기사를 하나의 리스트로 합치고 시간순 정렬
    all_articles_flat = []
    for section, articles in articles_by_section.items():
        for article in articles:
            article['_source_group'] = _get_source_group(section)
            if not article.get('section'):
                article['section'] = section
            all_articles_flat.append(article)

    all_articles_flat.sort(key=_sort_key, reverse=True)

    articles_html = '<div class="section-group">'
    for article in all_articles_flat:
            title = article.get('title', 'N/A')
            title_ko = article.get('title_ko', '')
            summary_ko = article.get('summary_ko', '')
            link = article.get('link', '#')
            pub_date = article.get('pub_date', '')
            has_watchlist = article.get('has_watchlist', False)
            watchlist_item = article.get('watchlist_item', '')
            article_date = _extract_date_str(pub_date)
            article_id = _make_article_id(link)
            source_group = article.get('_source_group', '기타')
            section = article.get('section', '')
            watchlist_badge = f'<span class="wl-badge">★ {watchlist_item}</span>' if has_watchlist else ''
            source_badge = f'<span class="source-tag">{section}</span>'

            if title_ko and title_ko != title:
                main_title = title_ko
                sub_html = f'<div class="art-orig">{title}</div>'
            else:
                main_title = title
                sub_html = ''

            summary_html = f'<div class="art-summary">{summary_ko}</div>' if summary_ko else ''

            rating_html = f'''<div class="rating-bar" data-article-id="{article_id}">
<button class="rate-btn" data-rating="star1" onclick="rateArticle(event, '{article_id}', 'star1', this)" title="⭐">⭐</button>
<button class="rate-btn" data-rating="star2" onclick="rateArticle(event, '{article_id}', 'star2', this)" title="⭐⭐">⭐⭐</button>
<button class="rate-btn" data-rating="star3" onclick="rateArticle(event, '{article_id}', 'star3', this)" title="⭐⭐⭐">⭐⭐⭐</button>
<button class="rate-btn dislike-btn" data-rating="dislike" onclick="rateArticle(event, '{article_id}', 'dislike', this)" title="관심없음">👎</button>
<span class="rate-status" id="status-{article_id}"></span>
</div>'''

            data_attrs = f'data-date="{article_date}" data-source="{source_group}" data-id="{article_id}" data-title="{main_title}" data-link="{link}" data-watchlist="{watchlist_item}"'

            soft_dislike_class = 'soft-dislike' if article.get('is_soft_dislike') else ''
            articles_html += f'''<div class="art-card {"watchlist" if has_watchlist else ""} {soft_dislike_class}" {data_attrs}>
<a href="{link}" target="_blank" class="art-link">
{watchlist_badge}{source_badge}
<div class="art-title">{main_title}</div>
{sub_html}
{summary_html}
<div class="art-meta"><span class="art-date">{pub_date}</span></div>
</a>
{rating_html}
</div>'''
    articles_html += '</div>'

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily News Brief - {date_str}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=Playfair+Display:wght@700;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #F8F7F4;
    --bg2: #1a1f36;
    --bg3: #EFEEEB;
    --bg4: #E8E6E1;
    --border: #D5D2CB;
    --txt: #2a2a2a;
    --txt2: #666;
    --txt3: #999;
    --accent: #a68532;
    --accent2: rgba(166,133,50,0.12);
    --wl: #c0392b;
    --wl-bg: rgba(192,57,43,0.06);
    --sidebar-w: 260px;
    --star1: #8b7355;
    --star2: #a68532;
    --star3: #d4a017;
    --dislike: #999;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: 'Noto Sans KR', sans-serif;
    background: var(--bg);
    color: var(--txt);
    line-height: 1.6;
}}
.sidebar {{
    position: fixed;
    top: 0; left: 0;
    width: var(--sidebar-w);
    height: 100vh;
    background: var(--bg2);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 1.5rem 1rem;
    z-index: 100;
}}
.sidebar::-webkit-scrollbar {{ width: 4px; }}
.sidebar::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}
.sb-brand {{
    font-family: 'Playfair Display', serif;
    font-size: 1.3rem;
    font-weight: 900;
    color: #d4a017;
    margin-bottom: 0.2rem;
}}
.sb-sub {{
    font-size: 0.6rem;
    color: #8890a4;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    line-height: 1.4;
}}
.sb-info {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #8890a4;
    margin-bottom: 0.3rem;
}}
.sb-total {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #d4a017;
    background: rgba(212,160,23,0.15);
    padding: 0.2rem 0.6rem;
    border-radius: 100px;
    display: inline-block;
    margin-bottom: 1rem;
}}
.sb-divider {{
    border: none;
    border-top: 1px solid rgba(255,255,255,0.1);
    margin: 0.8rem 0;
}}
.sb-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: #8890a4;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 0.4rem;
}}
.sb-list {{ list-style: none; margin-bottom: 0.5rem; }}
.sb-list li {{ margin-bottom: 0.2rem; }}
.sb-btn {{
    width: 100%;
    text-align: left;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 0.78rem;
    padding: 0.4rem 0.6rem;
    border: 1px solid transparent;
    border-radius: 5px;
    background: transparent;
    color: #a0a8bc;
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.sb-btn:hover {{ background: rgba(255,255,255,0.05); color: #e0e0e0; }}
.sb-btn.active {{
    background: rgba(212,160,23,0.15);
    border-color: #d4a017;
    color: #d4a017;
    font-weight: 500;
}}
.sb-count {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #d4a017;
}}
.sb-filter-count {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #d4a017;
    margin-top: 0.5rem;
}}
.sb-rating-stats {{
    margin-top: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: #8890a4;
    line-height: 1.6;
}}
.tab-bar {{
    display: flex;
    gap: 0.3rem;
    margin-bottom: 0.8rem;
}}
.tab-btn {{
    flex: 1;
    padding: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 5px;
    background: transparent;
    color: #8890a4;
    cursor: pointer;
    transition: all 0.15s ease;
    letter-spacing: 0.05em;
}}
.tab-btn:hover {{ background: rgba(255,255,255,0.05); color: #e0e0e0; }}
.tab-btn.active {{
    background: rgba(212,160,23,0.15);
    border-color: #d4a017;
    color: #d4a017;
}}
.status-alert {{
    margin-top: 0.8rem;
    padding: 0.5rem 0.6rem;
    background: rgba(192,57,43,0.1);
    border: 1px solid rgba(192,57,43,0.2);
    border-radius: 6px;
    font-size: 0.68rem;
    color: #e74c3c;
    line-height: 1.4;
}}
.main {{
    margin-left: var(--sidebar-w);
    padding: 1.5rem 2rem 4rem;
    min-height: 100vh;
}}
#newsView, #insightView {{ }}
#insightView {{ display: none; }}
.section-group {{ margin-bottom: 2rem; }}
.section-group.hidden {{ display: none; }}
.section-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 500;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.2em;
    padding: 0.4rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0.4rem;
}}
.art-card {{
    display: block;
    padding: 0.7rem 0.8rem;
    margin-bottom: 0.5rem;
    border-radius: 6px;
    transition: all 0.15s ease;
    border: 1px solid var(--border);
    background: var(--bg3);
}}
.art-card:hover {{
    background: var(--bg4);
    border-color: var(--border);
}}
.art-card.watchlist {{
}}
.art-card.hidden {{ display: none; }}
.art-card.rated-dislike {{ opacity: 0.35; }}
.art-card.soft-dislike {{
    opacity: 0.45;
    border-left: 3px solid var(--dislike);
}}
.art-link {{
    display: block;
    text-decoration: none;
    color: inherit;
    transition: transform 0.15s ease;
}}
.art-link:hover {{ transform: translateX(3px); }}
.art-title {{
    font-size: 0.98rem;
    font-weight: 500;
    line-height: 1.45;
    margin-top: 0.2rem;
}}
.art-orig {{
    font-size: 0.85rem;
    color: var(--txt3);
    margin-top: 0.2rem;
    padding-left: 0.6rem;
    border-left: 2px solid var(--border);
    font-style: italic;
}}
.art-summary {{
    font-size: 0.88rem;
    color: var(--txt2);
    margin-top: 0.3rem;
    line-height: 1.5;
    padding-left: 0.6rem;
    border-left: 2px solid var(--accent2);
}}
.wl-badge {{
    display: inline-block;
    font-size: 0.58rem;
    font-weight: 500;
    color: var(--wl);
    background: rgba(192,57,43,0.1);
    padding: 0.12rem 0.45rem;
    border-radius: 4px;
    white-space: nowrap;
    margin-right: 0.3rem;
}}
.source-tag {{
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.58rem;
    font-weight: 500;
    color: var(--accent);
    background: var(--accent2);
    padding: 0.12rem 0.45rem;
    border-radius: 4px;
    white-space: nowrap;
}}
.art-date {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.73rem;
    color: var(--txt3);
}}
/* Rating Bar */
.rating-bar {{
    display: flex;
    align-items: center;
    gap: 0.3rem;
    margin-top: 0.4rem;
    padding-top: 0.4rem;
    border-top: 1px solid var(--border);
}}
.rate-btn {{
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.2rem 0.5rem;
    font-size: 0.7rem;
    cursor: pointer;
    transition: all 0.15s ease;
    opacity: 0.6;
}}
.rate-btn:hover {{ opacity: 1; background: var(--bg4); border-color: var(--accent); transform: scale(1.05); }}
.rate-btn.active {{ opacity: 1; border-color: var(--accent); box-shadow: 0 0 8px rgba(166,133,50,0.25); }}
.rate-btn.active[data-rating="star1"] {{ background: rgba(139,115,85,0.15); }}
.rate-btn.active[data-rating="star2"] {{ background: rgba(166,133,50,0.15); }}
.rate-btn.active[data-rating="star3"] {{ background: rgba(212,160,23,0.2); }}
.rate-btn.dislike-btn.active {{ border-color: var(--dislike); background: rgba(153,153,153,0.15); box-shadow: 0 0 8px rgba(153,153,153,0.2); }}
.rate-status {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: var(--accent);
    margin-left: 0.3rem;
    opacity: 0;
    transition: opacity 0.3s ease;
}}
.rate-status.show {{ opacity: 1; }}
/* Insight Styles */
/* Archive Styles */
.archive-card {{
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.7rem 0.8rem;
    margin-bottom: 0.5rem;
}}
.archive-head {{
    display: flex;
    align-items: center;
    gap: 0.3rem;
    margin-bottom: 0.3rem;
}}
.archive-star {{ font-size: 0.75rem; }}
.archive-title {{
    display: block;
    font-size: 0.92rem;
    font-weight: 500;
    color: var(--txt);
    text-decoration: none;
    line-height: 1.45;
}}
.archive-title:hover {{ color: var(--accent); }}
.archive-meta {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 0.4rem;
}}
.archive-date {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--txt3);
}}
.archive-del {{
    font-size: 0.65rem;
    color: var(--dislike);
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.15rem 0.5rem;
    cursor: pointer;
}}
.archive-del:hover {{ background: rgba(153,153,153,0.15); color: var(--wl); border-color: var(--wl); }}
.insight-empty {{
    text-align: center;
    padding: 4rem 0;
    color: var(--txt3);
    font-size: 0.9rem;
}}
.insight-card {{
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1.2rem;
}}
.insight-card.weekly {{ border-left: 3px solid var(--accent); }}
.insight-card.daily {{ border-left: 3px solid var(--star2); }}
.insight-card.old {{ opacity: 0.7; }}
.insight-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    font-weight: 500;
    color: var(--accent);
    letter-spacing: 0.1em;
    margin-bottom: 0.3rem;
}}
.insight-date {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--txt3);
    margin-bottom: 0.8rem;
}}
.insight-content {{
    font-size: 0.82rem;
    line-height: 1.7;
    color: var(--txt);
}}
.insight-h2 {{
    font-size: 1rem;
    font-weight: 700;
    color: var(--accent);
    margin: 1rem 0 0.4rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--border);
}}
.insight-h3 {{
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--txt);
    margin: 0.8rem 0 0.3rem;
}}
.insight-h4 {{
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--txt2);
    margin: 0.6rem 0 0.2rem;
}}
.insight-p {{ margin-bottom: 0.4rem; }}
.insight-list {{
    list-style: none;
    margin: 0.3rem 0 0.6rem;
}}
.insight-list li {{
    padding: 0.2rem 0 0.2rem 1rem;
    position: relative;
    font-size: 0.8rem;
}}
.insight-list li::before {{
    content: '▸';
    position: absolute;
    left: 0;
    color: var(--accent);
}}
.insight-divider {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--txt3);
    text-transform: uppercase;
    letter-spacing: 0.15em;
    padding: 1rem 0 0.5rem;
    border-top: 1px solid var(--border);
    margin-top: 1rem;
}}
.footer {{
    margin-left: var(--sidebar-w);
    border-top: 1px solid var(--border);
    padding: 1.5rem 2rem;
    text-align: center;
}}
.footer-text {{ font-size: 0.68rem; color: var(--txt3); }}
@media (max-width: 768px) {{
    .sidebar {{
        position: static;
        width: 100%;
        height: auto;
        border-right: none;
        border-bottom: 1px solid var(--border);
        overflow-y: visible;
        padding: 1rem;
    }}
    .main {{ margin-left: 0; padding: 1rem; }}
    .footer {{ margin-left: 0; padding: 1rem; }}
    .rate-btn {{ padding: 0.25rem 0.4rem; font-size: 0.65rem; }}
}}
</style>
</head>
<body>
<aside class="sidebar">
    <div class="sb-brand">Daily News Brief</div>
    <div class="sb-sub">FT · Bloomberg · Reuters · WSJ<br>TechCrunch · Space · Defense</div>
    <div class="sb-info">{weekday}요일 · {date_str}</div>
    <div class="sb-info">업데이트 {time_str} KST</div>
    <span class="sb-total">총 {total_articles}개 기사</span>
    <hr class="sb-divider">
    <div class="tab-bar">
        <button class="tab-btn active" onclick="switchTab('news')">📰 뉴스</button>
        <button class="tab-btn" onclick="switchTab('insight')">💡 인사이트</button>
        <button class="tab-btn" onclick="switchTab('archive')">📌 보관함</button>
    </div>
    <div id="newsFilters">
        <div class="sb-label">날짜</div>
        <ul class="sb-list">{date_items}</ul>
        <hr class="sb-divider">
        <div class="sb-label">소스</div>
        <ul class="sb-list">{source_items}</ul>
        <div class="sb-filter-count" id="filterCount"></div>
        <hr class="sb-divider">
        <div class="sb-label">내 평가</div>
        <div class="sb-rating-stats" id="ratingStats">로딩 중...</div>
    </div>
    {status_html}
</aside>
<main class="main">
    <div id="newsView">
        {articles_html if total_articles > 0 else '<div style="text-align:center;padding:4rem 0;color:var(--txt3);">📭 수집된 기사가 없습니다.</div>'}
    </div>
    <div id="insightView">
        {insights_html}
    </div>
    <div id="archiveView" style="display:none;">
        <div id="archiveList"></div>
        <div id="archiveEmpty" style="text-align:center;padding:4rem 0;color:var(--txt3);">📌 아직 보관한 기사가 없습니다.<br><span style="font-size:0.75rem">기사에 별점을 주면 자동으로 보관됩니다.</span></div>
    </div>
</main>
<footer class="footer">
    <div class="footer-text">Daily News Brief · Premium: 매시간 (KST 7~23시) · Daily: KST 07:00 / 21:00 · 주간 리포트: 일요일 21:30</div>
</footer>
<script>
const WORKER_URL = '{WORKER_URL}';
let currentDate = 'all';
let currentSource = 'all';
let ratingsCache = {{}};

document.addEventListener('DOMContentLoaded', loadRatings);

function switchTab(tab) {{
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('newsView').style.display = 'none';
    document.getElementById('insightView').style.display = 'none';
    document.getElementById('archiveView').style.display = 'none';
    document.getElementById('newsFilters').style.display = 'none';
    if (tab === 'news') {{
        document.getElementById('newsView').style.display = '';
        document.getElementById('newsFilters').style.display = '';
    }} else if (tab === 'insight') {{
        document.getElementById('insightView').style.display = '';
    }} else if (tab === 'archive') {{
        document.getElementById('archiveView').style.display = '';
        renderArchive();
    }}
}}

function renderArchive() {{
    const list = document.getElementById('archiveList');
    const empty = document.getElementById('archiveEmpty');
    const rated = Object.entries(ratingsCache).filter(([id, info]) => info.rating !== 'dislike');
    if (rated.length === 0) {{
        list.innerHTML = '';
        empty.style.display = '';
        return;
    }}
    empty.style.display = 'none';
    const starMap = {{ star1: '⭐', star2: '⭐⭐', star3: '⭐⭐⭐' }};
    const sorted = rated.sort((a, b) => (b[1].ratedAt || '').localeCompare(a[1].ratedAt || ''));
    list.innerHTML = sorted.map(([id, info]) => `<div class="archive-card" id="arc-${{id}}">
<div class="archive-head">
<span class="archive-star">${{starMap[info.rating] || '⭐'}}</span>
<span class="source-tag">${{info.source || ''}}</span>
${{info.watchlistItem ? `<span class="wl-badge">★ ${{info.watchlistItem}}</span>` : ''}}
</div>
<a href="${{info.link || '#'}}" target="_blank" class="archive-title">${{info.title || '제목 없음'}}</a>
<div class="archive-meta">
<span class="archive-date">${{(info.ratedAt || '').slice(0, 10)}}</span>
<button class="archive-del" onclick="deleteRating('${{id}}')">삭제</button>
</div>
</div>`).join('');
}}

async function deleteRating(articleId) {{
    if (!confirm('이 기사를 보관함에서 삭제할까요?')) return;
    try {{
        const res = await fetch(WORKER_URL + '/delete-rate', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ articleId }}),
        }});
        if (res.ok) {{
            delete ratingsCache[articleId];
            const bar = document.querySelector(`.rating-bar[data-article-id="${{articleId}}"]`);
            if (bar) bar.querySelectorAll('.rate-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('arc-' + articleId)?.remove();
            updateRatingStats();
            const rated = Object.entries(ratingsCache).filter(([id, info]) => info.rating !== 'dislike');
            if (rated.length === 0) document.getElementById('archiveEmpty').style.display = '';
        }}
    }} catch (e) {{ alert('삭제 실패: ' + e.message); }}
}}

async function loadRatings() {{
    try {{
        const res = await fetch(WORKER_URL + '/ratings');
        const data = await res.json();
        ratingsCache = data.ratings || {{}};
        applyRatingsUI();
        updateRatingStats();
    }} catch (e) {{
        console.error('평가 데이터 로드 실패:', e);
        document.getElementById('ratingStats').textContent = '오프라인';
    }}
}}

function applyRatingsUI() {{
    for (const [articleId, info] of Object.entries(ratingsCache)) {{
        const bar = document.querySelector(`.rating-bar[data-article-id="${{articleId}}"]`);
        if (!bar) continue;
        const btn = bar.querySelector(`[data-rating="${{info.rating}}"]`);
        if (btn) btn.classList.add('active');
        if (info.rating === 'dislike') {{
            const card = bar.closest('.art-card');
            if (card) card.classList.add('rated-dislike');
        }}
    }}
}}

function updateRatingStats() {{
    const stats = {{ star1: 0, star2: 0, star3: 0, dislike: 0 }};
    for (const info of Object.values(ratingsCache)) {{
        if (stats.hasOwnProperty(info.rating)) stats[info.rating]++;
    }}
    const total = stats.star1 + stats.star2 + stats.star3 + stats.dislike;
    const el = document.getElementById('ratingStats');
    if (total === 0) {{
        el.textContent = '아직 평가 없음';
    }} else {{
        el.innerHTML = `⭐ ${{stats.star1}} · ⭐⭐ ${{stats.star2}} · ⭐⭐⭐ ${{stats.star3}}<br>👎 ${{stats.dislike}} · 총 ${{total}}개 평가`;
    }}
}}

async function rateArticle(event, articleId, rating, btn) {{
    event.preventDefault();
    event.stopPropagation();
    const bar = btn.closest('.rating-bar');
    const card = bar.closest('.art-card');
    const statusEl = document.getElementById('status-' + articleId);
    if (btn.classList.contains('active')) {{
        bar.querySelectorAll('.rate-btn').forEach(b => b.classList.remove('active'));
        card.classList.remove('rated-dislike');
        delete ratingsCache[articleId];
        statusEl.textContent = '해제됨';
        statusEl.classList.add('show');
        setTimeout(() => statusEl.classList.remove('show'), 1500);
        updateRatingStats();
        return;
    }}
    bar.querySelectorAll('.rate-btn').forEach(b => b.classList.remove('active'));
    card.classList.remove('rated-dislike');
    btn.classList.add('active');
    if (rating === 'dislike') {{ card.classList.add('rated-dislike'); }}
    statusEl.textContent = '저장 중...';
    statusEl.classList.add('show');
    try {{
        const res = await fetch(WORKER_URL + '/rate', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
                articleId, rating,
                title: card.dataset.title || '',
                source: card.dataset.source || '',
                link: card.dataset.link || '',
                watchlistItem: card.dataset.watchlist || '',
            }}),
        }});
        if (res.ok) {{
            ratingsCache[articleId] = {{ rating }};
            statusEl.textContent = '✓ 저장됨';
            updateRatingStats();
        }} else {{ statusEl.textContent = '✗ 실패'; btn.classList.remove('active'); }}
    }} catch (e) {{ statusEl.textContent = '✗ 오프라인'; btn.classList.remove('active'); }}
    setTimeout(() => statusEl.classList.remove('show'), 2000);
}}

function filterDate(date) {{
    currentDate = date;
    document.querySelectorAll('.date-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    applyFilters();
}}
function filterSource(source) {{
    currentSource = source;
    document.querySelectorAll('.source-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    applyFilters();
}}
function applyFilters() {{
    let n = 0;
    document.querySelectorAll('.art-card').forEach(c => {{
        const md = (currentDate === 'all' || c.getAttribute('data-date') === currentDate);
        const ms = (currentSource === 'all' || c.getAttribute('data-source') === currentSource);
        if (md && ms) {{ c.classList.remove('hidden'); n++; }}
        else {{ c.classList.add('hidden'); }}
    }});
    document.querySelectorAll('.section-group').forEach(g => {{
        const hv = g.querySelectorAll('.art-card:not(.hidden)').length > 0;
        if (hv) {{ g.classList.remove('hidden'); }}
        else {{ g.classList.add('hidden'); }}
    }});
    const el = document.getElementById('filterCount');
    if (currentDate === 'all' && currentSource === 'all') {{ el.textContent = ''; }}
    else {{ el.textContent = n + '개 기사 표시 중'; }}
}}
</script>
</body>
</html>'''

    docs_dir = 'docs'
    os.makedirs(docs_dir, exist_ok=True)
    output_path = os.path.join(docs_dir, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    logger.info(f"브리핑 웹페이지 생성 완료: {output_path}")
    return output_path
