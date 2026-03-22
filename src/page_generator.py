"""
데일리 뉴스 브리핑 웹페이지 생성 모듈 - 사이드바 + 요약
"""
import os
import re
from datetime import datetime
from config.config import KST
from src.logger import setup_logger
from src.rss_fetcher import get_feed_status

logger = setup_logger(__name__)

SOURCE_GROUPS = {
    'FT': ['FT Markets', 'FT Companies', 'FT Technology', 'FT World', 'FT US', 'FT Opinion', 'FT Global Economy'],
    'Bloomberg': ['BBG Markets', 'BBG Technology', 'BBG Politics', 'BBG Economics', 'BBG Industries'],
    'Reuters': ['Reuters Business', 'Reuters Markets'],
    'TechCrunch': ['TechCrunch', 'TC Startups', 'TC AI', 'TC Venture'],
    'Space': ['SpaceNews', 'Space.com', 'Payload Space', 'Satellite Today'],
    'Defense': ['Breaking Defense', 'Defense News', 'Defense One', 'DefenseScoop', 'Air & Space Forces', 'Space & Defense'],
    'Ars Technica': ['Ars Technica'],
    '매경': ['MK 헤드라인', 'MK 경제', 'MK 금융', 'MK 기업', 'MK 증권', 'MK IT'],
    '한경': ['HK 경제', 'HK 산업', 'HK 금융', 'HK IT', 'HK 전체'],
    '조선': ['조선 헤드라인', '조선 정치', '조선 사회'],
}


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


def generate_briefing_page(articles_by_section: dict):
    now = datetime.now(KST)
    date_str = now.strftime('%Y년 %m월 %d일')
    time_str = now.strftime('%H:%M')
    weekday_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
    weekday = weekday_map[now.weekday()]
    total_articles = sum(len(v) for v in articles_by_section.values())

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

    articles_html = ""
    for section, articles in articles_by_section.items():
        source_group = _get_source_group(section)
        articles_html += f'<div class="section-group" data-source="{source_group}">'
        articles_html += f'<div class="section-label">{section}</div>'
        for article in articles:
            title = article.get('title', 'N/A')
            title_ko = article.get('title_ko', '')
            summary_ko = article.get('summary_ko', '')
            link = article.get('link', '#')
            pub_date = article.get('pub_date', '')
            has_watchlist = article.get('has_watchlist', False)
            watchlist_item = article.get('watchlist_item', '')
            article_date = _extract_date_str(pub_date)
            watchlist_badge = f'<span class="wl-badge">★ {watchlist_item}</span>' if has_watchlist else ''

            if title_ko and title_ko != title:
                main_title = title_ko
                sub_html = f'<div class="art-orig">{title}</div>'
            else:
                main_title = title
                sub_html = ''

            summary_html = f'<div class="art-summary">{summary_ko}</div>' if summary_ko else ''

            articles_html += f'''<a href="{link}" target="_blank" class="art-card {"watchlist" if has_watchlist else ""}" data-date="{article_date}" data-source="{source_group}">
<div class="art-head"><div class="art-title">{main_title}</div>{watchlist_badge}</div>
{sub_html}
{summary_html}
<div class="art-meta"><span class="art-date">{pub_date}</span></div>
</a>'''
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
    --bg: #0a0a0a;
    --bg2: #111;
    --bg3: #141414;
    --bg4: #1a1a1a;
    --border: #222;
    --txt: #e8e8e8;
    --txt2: #888;
    --txt3: #555;
    --accent: #c9a94e;
    --accent2: #6b5a2a;
    --wl: #d4442a;
    --wl-bg: rgba(212,68,42,0.08);
    --sidebar-w: 260px;
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
    color: var(--accent);
    margin-bottom: 0.2rem;
}}
.sb-sub {{
    font-size: 0.6rem;
    color: var(--txt3);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
    line-height: 1.4;
}}
.sb-info {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--txt2);
    margin-bottom: 0.3rem;
}}
.sb-total {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--accent);
    background: var(--accent2);
    padding: 0.2rem 0.6rem;
    border-radius: 100px;
    display: inline-block;
    margin-bottom: 1rem;
}}
.sb-divider {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 0.8rem 0;
}}
.sb-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: var(--txt3);
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
    color: var(--txt2);
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.sb-btn:hover {{ background: var(--bg3); color: var(--txt); }}
.sb-btn.active {{
    background: var(--accent2);
    border-color: var(--accent);
    color: var(--accent);
    font-weight: 500;
}}
.sb-count {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--accent);
}}
.sb-filter-count {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: var(--accent);
    margin-top: 0.5rem;
}}
.status-alert {{
    margin-top: 0.8rem;
    padding: 0.5rem 0.6rem;
    background: var(--wl-bg);
    border: 1px solid rgba(212,68,42,0.2);
    border-radius: 6px;
    font-size: 0.68rem;
    color: var(--wl);
    line-height: 1.4;
}}
.main {{
    margin-left: var(--sidebar-w);
    padding: 1.5rem 2rem 4rem;
    min-height: 100vh;
}}
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
    text-decoration: none;
    color: inherit;
    padding: 0.7rem 0.8rem;
    margin-bottom: 0.1rem;
    border-radius: 6px;
    transition: all 0.15s ease;
    border: 1px solid transparent;
}}
.art-card:hover {{
    background: var(--bg4);
    border-color: var(--border);
    transform: translateX(3px);
}}
.art-card.watchlist {{
    background: var(--wl-bg);
    border-left: 3px solid var(--wl);
}}
.art-card.hidden {{ display: none; }}
.art-head {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.6rem;
}}
.art-title {{
    font-size: 0.88rem;
    font-weight: 500;
    line-height: 1.45;
}}
.art-orig {{
    font-size: 0.75rem;
    color: var(--txt3);
    margin-top: 0.2rem;
    padding-left: 0.6rem;
    border-left: 2px solid var(--border);
    font-style: italic;
}}
.art-summary {{
    font-size: 0.78rem;
    color: var(--txt2);
    margin-top: 0.3rem;
    line-height: 1.5;
    padding-left: 0.6rem;
    border-left: 2px solid var(--accent2);
}}
.wl-badge {{
    flex-shrink: 0;
    font-size: 0.58rem;
    font-weight: 500;
    color: var(--wl);
    background: rgba(212,68,42,0.15);
    padding: 0.12rem 0.45rem;
    border-radius: 4px;
    white-space: nowrap;
}}
.art-date {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.63rem;
    color: var(--txt3);
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
    .art-head {{ flex-direction: column; gap: 0.2rem; }}
}}
</style>
</head>
<body>
<aside class="sidebar">
    <div class="sb-brand">Daily News Brief</div>
    <div class="sb-sub">FT · Bloomberg · Reuters · TechCrunch<br>Space · Defense · 매경 · 한경 · 조선</div>
    <div class="sb-info">{weekday}요일 · {date_str}</div>
    <div class="sb-info">업데이트 {time_str} KST</div>
    <span class="sb-total">총 {total_articles}개 기사</span>
    <hr class="sb-divider">
    <div class="sb-label">날짜</div>
    <ul class="sb-list">{date_items}</ul>
    <hr class="sb-divider">
    <div class="sb-label">소스</div>
    <ul class="sb-list">{source_items}</ul>
    <div class="sb-filter-count" id="filterCount"></div>
    {status_html}
</aside>
<main class="main">
    {articles_html if total_articles > 0 else '<div style="text-align:center;padding:4rem 0;color:var(--txt3);">📭 수집된 기사가 없습니다.</div>'}
</main>
<footer class="footer">
    <div class="footer-text">Daily News Brief · KST 07:00 / 12:00 / 20:00 / 21:00 자동 업데이트</div>
</footer>
<script>
let currentDate = 'all';
let currentSource = 'all';
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
        const ms = (currentSource === 'all' || g.getAttribute('data-source') === currentSource);
        const hv = g.querySelectorAll('.art-card:not(.hidden)').length > 0;
        if (ms && hv) {{ g.classList.remove('hidden'); }}
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
