import os
from dotenv import load_dotenv
import pytz

# .env 파일 로드
load_dotenv()

# Claude API
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

# Gmail SMTP 설정
GMAIL_ADDRESS = os.getenv('GMAIL_ADDRESS')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD')
GMAIL_SMTP_SERVER = 'smtp.gmail.com'
GMAIL_SMTP_PORT = 587

# RSS 설정
FT_RSS_URL = os.getenv('FT_RSS_URL', 'https://www.ft.com/?format=rss')
RSS_HOURS_LOOKBACK = 24  # 최근 24시간

# 분석 리포트 수신자
ANALYSIS_RECIPIENT_EMAIL = os.getenv('ANALYSIS_RECIPIENT_EMAIL')

# 로깅
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 타임존
KST = pytz.timezone('Asia/Seoul')
UTC = pytz.UTC

# 출력 디렉토리
OUTPUT_DIR = 'output'
