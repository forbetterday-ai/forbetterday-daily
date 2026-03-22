"""
Claude API를 사용한 번역 및 워치리스트 감지
"""
import os
from anthropic import Anthropic
from typing import Dict, List, Tuple
from config.config import CLAUDE_API_KEY
from config.watchlist import is_watchlist_item
from src.logger import setup_logger

logger = setup_logger(__name__)

# 환경변수에 API 키 설정 (Anthropic이 자동으로 읽도록)
if CLAUDE_API_KEY:
    os.environ['ANTHROPIC_API_KEY'] = CLAUDE_API_KEY


def _get_client():
    """Anthropic 클라이언트 지연 초기화"""
    return Anthropic()


def translate_articles(articles_by_section: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    """
    기사 제목 및 요약을 한글로 번역 (한국 뉴스는 번역 스킵)
    """
    try:
        logger.info("기사 번역 시작 (Claude API)")

        for section, articles in articles_by_section.items():
            for article in articles:
                # 한국 뉴스는 번역 스킵
                if article.get('is_korean', False):
                    article['title_ko'] = article['title']
                else:
                    title_ko = translate_text(article['title'])
                    article['title_ko'] = title_ko

                # 워치리스트 종목 감지
                has_watchlist, watchlist_item = is_watchlist_item(
                    article.get('title_ko', '') + " " + article['title']
                )
                article['has_watchlist'] = has_watchlist
                article['watchlist_item'] = watchlist_item

                logger.debug(f"처리 완료: {article.get('title_ko', '')}")

        logger.info(f"번역 완료: 전체 {sum(len(v) for v in articles_by_section.values())}개 기사")
        return articles_by_section

    except Exception as e:
        logger.error(f"번역 실패: {str(e)}", exc_info=True)
        return articles_by_section


def translate_text(text: str) -> str:
    """
    텍스트를 한글로 번역
    """
    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""다음 영문 텍스트를 자연스러운 한글로 번역해주세요.
전문 용어는 [한글 풀이] (영문원어) 형식으로 표기해주세요.
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


def translate_for_analysis(article_text: str) -> str:
    """
    상세 분석용 번역 (더 긴 텍스트)
    """
    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": f"""다음 영문 뉴스 기사를 한글로 번역해주세요.
논리적 흐름을 유지하며 자연스럽게 번역하세요.
전문 용어는 [한글 풀이] (영문원어) 형식으로 표기해주세요.
번역문만 출력하세요.
기사:
{article_text}"""
                }
            ]
        )
        return message.content[0].text.strip()

    except Exception as e:
        logger.warning(f"상세 번역 실패: {str(e)}")
        return article_text
