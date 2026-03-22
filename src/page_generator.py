"""
FT 데일리 브리핑 웹페이지 생성 모듈
"""
import os
from datetime import datetime
from config.config import KST
from src.logger import setup_logger

logger = setup_logger(__name__)


def generate_briefing_page(articles_by_section: dict):
    """
    브리핑 데이터를 정적 HTML 페이지로 생성
    """
    now = datetime.now(KST)
    date_str = now.strftime('%Y년 %m월 %d일')
    time_str = now.strftime('%H:%M')
    weekday_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
    weekday = weekday_map[now.weekday()]

    total_articles = sum(len(v) for v in articles_by_section.values())

    # 기사 HTML 생성
    articles_html = ""
    for section, articles in articles_by_section.items():
        articles_html += f'<div class="section-group">'
        articles_html += f'<div class="section-label">{section}</div>'

        for article in articles:
            title = article.get('title', 'N/A')
            title_ko = article.get('title_ko', '')
            link = article.get('link', '#')
            pub_date = article.get('pub_date', '')
            has_watchlist = article.get('has_watchlist', False)
            watchlist_item = article.get('watchlist_item', '')

            watchlist_badge = f'<span class="watchlist-badge">★ {watchlist_item}</span>' if has_watchlist else ''
            # 한글 번역이 있고 원문과 다르면 표시
            translated_html = f'<div class="article-translated">{title_ko}</div>' if title_ko and title_ko != title else ''

            articles_html += f'''
            <a href="{link}" target="_blank" class="article-card {"watchlist" if has_watchlist else ""}">
                <div class="article-header">
                    <div class="article-title">{title}</div>
                    {watchlist_badge}
                </div>
                {translated_html}
                <div class="article-meta">
                    <span class="article-date">{pub_date}</span>
                </div>
            </a>
            '''

        articles_html += '</div>'

    # 섹션 통계
    section_stats = ""
    for section, articles in articles_by_section.items():
        section_stats += f'<span class="stat-pill">{section} <strong>{len(articles)}</strong></span>'

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FT 데일리 브리핑 - {date_str}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=Playfair+Display:wght@700;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0a0a;
            --bg-card: #141414;
            --bg-card-hover: #1a1a1a;
            --border: #222;
            --text-primary: #e8e8e8;
            --text-secondary: #888;
            --text-muted: #555;
            --accent: #c9a94e;
            --accent-dim: #6b5a2a;
            --watchlist: #d4442a;
            --watchlist-bg: rgba(212, 68, 42, 0.08);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.7;
            min-height: 100vh;
        }}
        .header {{
            border-bottom: 1px solid var(--border);
            padding: 2rem 0;
            background: linear-gradient(180deg, #111 0%, var(--bg-primary) 100%);
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 0 1.5rem;
        }}
        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1.5rem;
        }}
        .brand {{
            font-family: 'Playfair Display', serif;
            font-size: 2rem;
            font-weight: 900;
            color: var(--accent);
            letter-spacing: -0.02em;
        }}
        .brand-sub {{
            font-size: 0.75rem;
            font-weight: 300;
            color: var(--text-muted);
            letter-spacing: 0.15em;
            text-transform: uppercase;
            margin-top: 0.3rem;
        }}
        .date-block {{ text-align: right; }}
        .date-main {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        .date-weekday {{
            font-size: 1.8rem;
            font-weight: 900;
            color: var(--text-primary);
            line-height: 1;
        }}
        .stats-bar {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            align-items: center;
        }}
        .stat-pill {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            background: var(--bg-card);
            border: 1px solid var(--border);
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
        }}
        .stat-pill strong {{
            color: var(--accent);
            margin-left: 0.25rem;
        }}
        .total-count {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--accent);
            background: var(--accent-dim);
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
        }}
        .main {{ padding: 2rem 0 4rem; }}
        .section-group {{ margin-bottom: 2.5rem; }}
        .section-label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            font-weight: 500;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.2em;
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 0.75rem;
        }}
        .article-card {{
            display: block;
            text-decoration: none;
            color: inherit;
            padding: 1rem;
            margin-bottom: 0.25rem;
            border-radius: 8px;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }}
        .article-card:hover {{
            background: var(--bg-card-hover);
            border-color: var(--border);
            transform: translateX(4px);
        }}
        .article-card.watchlist {{
            background: var(--watchlist-bg);
            border-left: 3px solid var(--watchlist);
        }}
        .article-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.75rem;
        }}
        .article-title {{
            font-size: 0.95rem;
            font-weight: 500;
            line-height: 1.5;
        }}
        .article-translated {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 0.35rem;
            padding-left: 0.75rem;
            border-left: 2px solid var(--accent-dim);
        }}
        .watchlist-badge {{
            flex-shrink: 0;
            font-size: 0.65rem;
            font-weight: 500;
            color: var(--watchlist);
            background: rgba(212, 68, 42, 0.15);
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            white-space: nowrap;
        }}
        .article-date {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            color: var(--text-muted);
        }}
        .footer {{
            border-top: 1px solid var(--border);
            padding: 2rem 0;
            text-align: center;
        }}
        .footer-text {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
        .footer-text a {{
            color: var(--accent-dim);
            text-decoration: none;
        }}
        .empty-state {{
            text-align: center;
            padding: 4rem 0;
            color: var(--text-muted);
        }}
        .update-time {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }}
        @media (max-width: 640px) {{
            .brand {{ font-size: 1.5rem; }}
            .date-weekday {{ font-size: 1.3rem; }}
            .header-top {{ flex-direction: column; gap: 1rem; }}
            .date-block {{ text-align: left; }}
            .article-header {{ flex-direction: column; gap: 0.25rem; }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="container">
            <div class="header-top">
                <div>
                    <div class="brand">FT Daily Brief</div>
                    <div class="brand-sub">Financial Times 데일리 브리핑</div>
                </div>
                <div class="date-block">
                    <div class="date-weekday">{weekday}요일</div>
                    <div class="date-main">{date_str}</div>
                    <div class="update-time">업데이트 {time_str} KST</div>
                </div>
            </div>
            <div class="stats-bar">
                <span class="total-count">총 {total_articles}개 기사</span>
                {section_stats}
            </div>
        </div>
    </header>
    <main class="main">
        <div class="container">
            {articles_html if total_articles > 0 else '<div class="empty-state">📭 오늘 수집된 기사가 없습니다.</div>'}
        </div>
    </main>
    <footer class="footer">
        <div class="container">
            <div class="footer-text">
                FT Daily Brief Automation · 매일 KST 08:00 자동 업데이트<br>
                Powered by <a href="https://www.ft.com" target="_blank">Financial Times</a> RSS
            </div>
        </div>
    </footer>
</body>
</html>'''

    docs_dir = 'docs'
    os.makedirs(docs_dir, exist_ok=True)
    output_path = os.path.join(docs_dir, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    logger.info(f"브리핑 웹페이지 생성 완료: {output_path}")
    return output_path
