"""
데일리 뉴스 브리핑 웹페이지 생성 모듈 - 사이드바 + 요약 + 별점 시스템
"""
import os
import re
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
}

WORKER_URL = 'https://news-ratings.forbetterday.workers.dev'


def _make_article_id(link: str) -> str:
    """기사 링크로 고유 ID 생성"""
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
            article_id = _make_article_id(link)
            watchlist_badge = f'<span class="wl-badge">★ {watchlist_item}</span>' if has_watchlist else ''

            if title_ko and title_ko != title:
                main_title = title_ko
                sub_html = f'<div class="art-orig">{title}</div>'
            else:
                main_title = title
                sub_html = ''

            summary_html = f'<div class="art-summary">{summary_ko}</div>' if summary_ko else ''

            # 별점 UI
            rating_html = f'''<div class="rating-bar" data-article-id="{article_id}">
<button class="rate-btn" data-rating="star1" onclick="rateArticle(event, '{article_id}', 'star1', this)" title="⭐">⭐</button>
<button class="rate-btn" data-rating="star2" onclick="rateArticle(event, '{article_id}', 'star2', this)" title="⭐⭐">⭐⭐</button>
<button class="rate-btn" data-rating="star3" onclick="rateArticle(event, '{article_id}', 'star3', this)" title="⭐⭐⭐">⭐⭐⭐</button>
<button class="rate-btn dislike-btn" data-rating="dislike" onclick="rateArticle(event, '{article_id}', 'dislike', this)" title="관심없음">👎</button>
<span class="rate-status" id="status-{article_id}"></span>
</div>'''

            # data 속성에 메타 정보 저장 (별점 저장 시 함께 전송)
            data_attrs = f'data-date="{article_date}" data-source="{source_group}" data-id="{article_id}" data-title="{main_title}" data-link="{link}" data-watchlist="{watchlist_item}"'

            articles_html += f'''<div class="art-card {"watchlist" if has_watchlist else ""}" {data_attrs}>
<a href="{link}" target="_blank" class="art-link">
<div class="art-head"><div class="art-title">{main_title}</div>{watchlist_badge}</div>
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
    --star1: #8b7355;
    --star2: #c9a94e;
    --star3: #f5c518;
    --dislike: #555;
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
.sb-rating-stats {{
    margin-top: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem;
    color: var(--txt3);
    line-height: 1.6;
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
    padding: 0.7rem 0.8rem;
    margin-bottom: 0.1rem;
    border-radius: 6px;
    transition: all 0.15s ease;
    border: 1px solid transparent;
}}
.art-card:hover {{
    background: var(--bg4);
    border-color: var(--border);
}}
.art-card.watchlist {{
    background: var(--wl-bg);
    border-left: 3px solid var(--wl);
}}
.art-card.hidden {{ display: none; }}
.art-card.rated-dislike {{
    opacity: 0.35;
}}
.art-link {{
    display: block;
    text-decoration: none;
    color: inherit;
    transition: transform 0.15s ease;
}}
.art-link:hover {{
    transform: translateX(3px);
}}
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
/* ===== Rating Bar ===== */
.rating-bar {{
    display: flex;
    align-items: center;
    gap: 0.3rem;
    margin-top: 0.4rem;
    padding-top: 0.4rem;
    border-top: 1px solid rgba(255,255,255,0.04);
}}
.rate-btn {{
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.2rem 0.5rem;
    font-size: 0.7rem;
    cursor: pointer;
    transition: all 0.15s ease;
    opacity: 0.6;
}}
.rate-btn:hover {{
    opacity: 1;
    background: var(--bg4);
    border-color: var(--accent);
    transform: scale(1.05);
}}
.rate-btn.active {{
    opacity: 1;
    border-color: var(--accent);
    box-shadow: 0 0 8px rgba(201,169,78,0.25);
}}
.rate-btn.active[data-rating="star1"] {{ background: rgba(139,115,85,0.3); }}
.rate-btn.active[data-rating="star2"] {{ background: rgba(201,169,78,0.3); }}
.rate-btn.active[data-rating="star3"] {{ background: rgba(245,197,24,0.3); }}
.rate-btn.dislike-btn.active {{
    border-color: var(--dislike);
    background: rgba(85,85,85,0.3);
    box-shadow: 0 0 8px rgba(85,85,85,0.25);
}}
.rate-status {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6rem;
    color: var(--accent);
    margin-left: 0.3rem;
    opacity: 0;
    transition: opacity 0.3s ease;
}}
.rate-status.show {{
    opacity: 1;
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
    <div class="sb-label">날짜</div>
    <ul class="sb-list">{date_items}</ul>
    <hr class="sb-divider">
    <div class="sb-label">소스</div>
    <ul class="sb-list">{source_items}</ul>
    <div class="sb-filter-count" id="filterCount"></div>
    <hr class="sb-divider">
    <div class="sb-label">내 평가</div>
    <div class="sb-rating-stats" id="ratingStats">로딩 중...</div>
    {status_html}
</aside>
<main class="main">
    {articles_html if total_articles > 0 else '<div style="text-align:center;padding:4rem 0;color:var(--txt3);">📭 수집된 기사가 없습니다.</div>'}
</main>
<footer class="footer">
    <div class="footer-text">Daily News Brief · Premium: 매시간 (KST 7~23시) · Daily: KST 07:00 / 21:00</div>
</footer>
<script>
const WORKER_URL = '{WORKER_URL}';
let currentDate = 'all';
let currentSource = 'all';
let ratingsCache = {{}};

// 페이지 로드 시 기존 평가 불러오기
document.addEventListener('DOMContentLoaded', loadRatings);

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

    // 이미 같은 평가가 선택되어 있으면 해제 (토글)
    if (btn.classList.contains('active')) {{
        bar.querySelectorAll('.rate-btn').forEach(b => b.classList.remove('active'));
        card.classList.remove('rated-dislike');
        delete ratingsCache[articleId];
        statusEl.textContent = '해제됨';
        statusEl.classList.add('show');
        setTimeout(() => statusEl.classList.remove('show'), 1500);
        // TODO: 서버에서도 삭제 (현재는 캐시만)
        updateRatingStats();
        return;
    }}

    // 기존 선택 해제
    bar.querySelectorAll('.rate-btn').forEach(b => b.classList.remove('active'));
    card.classList.remove('rated-dislike');
    btn.classList.add('active');

    if (rating === 'dislike') {{
        card.classList.add('rated-dislike');
    }}

    // 서버에 저장
    statusEl.textContent = '저장 중...';
    statusEl.classList.add('show');

    try {{
        const res = await fetch(WORKER_URL + '/rate', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
                articleId,
                rating,
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
        }} else {{
            statusEl.textContent = '✗ 실패';
            btn.classList.remove('active');
        }}
    }} catch (e) {{
        statusEl.textContent = '✗ 오프라인';
        btn.classList.remove('active');
    }}

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
