import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

# 옵시디언 볼트 경로
VAULT_PATH = os.path.expanduser(
    os.environ.get(
        "VAULT_PATH",
        "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/chooyeanchan_icloud",
    )
)

# 인덱싱에서 제외할 폴더 (볼트 기준 상대경로, 쉼표 구분)
# 1.6_credentials 는 비밀정보가 있으므로 항상 제외한다.
_ALWAYS_EXCLUDE = {"1.6_credentials", ".obsidian", ".trash"}
_extra = {p.strip() for p in os.environ.get("EXCLUDE_DIRS", "").split(",") if p.strip()}
EXCLUDE_DIRS = _ALWAYS_EXCLUDE | _extra

# Ollama
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen3:8b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")

# 검색 설정
CHUNK_CHARS = 800      # 청크 최대 길이(문자)
TOP_K = 5              # 답변에 넘길 청크 수
DB_PATH = os.path.join(BASE_DIR, "data", "index.db")

# 텔레그램 (봇 실행 시에만 필요)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0") or 0)
REINDEX_MINUTES = int(os.environ.get("REINDEX_MINUTES", "30"))
