"""
Claude API를 사용한 번역 및 워치리스트 감지
"""
import os
import json
from anthropic import Anthropic
from typing import Dict, List
from config.config import CLAUDE_API_KEY
from config.watchlist import is_watchlist_item
from src.logger import setup_logger

logger = setup_logger(__name__)

if CLAUDE_API_KEY:
    os.environ['ANTHROPIC_API_KEY'] = CLAUDE_API_KEY


def _get_client():
    return Anthropic()


def translate_articles(articles_by_section: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    """
    기사 제목 + 요약을 한글로 번역 (한국 뉴스는 스킵)
    """
    try:
        logger.info("기사 번역 시작 (Claude API)")

        for section, articles in articles_by_section.items():
            for article in articles:
                if article.get('is_korean', False):
                    article['title_ko'] = article['title']
                    article['summary_ko'] = article.get('summary', '')
                else:
                    result = translate_title_and_summary(
                        article['title'],
                        article.get('summary', '')
                    )
                    article['title_ko'] = result.get('title_ko', article['title'])
                    article['summary_ko'] = result.get('summary_ko', '')

                has_watchlist, watchlist_item = is_watchlist_item(
                    article.get('title_ko', '') + " " + article['title']
                )
                article['has_watchlist'] = has_watchlist
                article['watchlist_item'] = watchlist_item

        logger.info(f"번역 완료: 전체 {sum(len(v) for v in articles_by_section.values())}개 기사")
        return articles_by_section

    except Exception as e:
        logger.error(f"번역 실패: {str(e)}", exc_info=True)
        return articles_by_section


def translate_title_and_summary(title: str, summary: str) -> dict:
    """
    제목과 요약을 한 번의 API 호출로 번역
    """
    try:
        client = _get_client()

        summary_clean = summary[:300].strip()
        if not summary_clean:
            # 요약이 없으면 제목만 번역
            title_ko = translate_text(title)
            return {'title_ko': title_ko, 'summary_ko': ''}

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""다음 영문 뉴스 제목과 요약을 한글로 번역해주세요.

제목: {title}
요약: {summary_clean}

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.
{{"title_ko": "번역된 제목", "summary_ko": "번역된 요약 (1~2문장으로 핵심만)"}}"""
                }
            ]
        )

        raw = message.content[0].text.strip()
        # JSON 파싱 시도
        try:
            result = json.loads(raw)
            return {
                'title_ko': result.get('title_ko', title),
                'summary_ko': result.get('summary_ko', ''),
            }
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 전체를 제목 번역으로 간주
            logger.warning(f"JSON 파싱 실패, 원문 응답 사용: {raw[:100]}")
            return {'title_ko': raw, 'summary_ko': ''}

    except Exception as e:
        logger.warning(f"번역 실패: {title[:50]}... → 원문 사용 ({str(e)})")
        return {'title_ko': title, 'summary_ko': ''}


def translate_text(text: str) -> str:
    """단일 텍스트 번역 (fallback용)"""
    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""다음 영문 텍스트를 자연스러운 한글로 번역해주세요.
번역문만 출력하세요.
영문 텍스트:
{text}"""
                }
            ]
        )
        return message.content[0].text.strip()
    except Exception as e:
        logger.warning(f"번역 실패: {text[:50]}... → 원문 사용 ({str(e)})")
        return text
