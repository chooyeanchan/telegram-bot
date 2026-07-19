import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])
TASKS_DIR = os.environ["TASKS_DIR"]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

TODO_FILE = os.path.join(TASKS_DIR, "1_to do list.md")
HEALTH_FILE = os.path.join(TASKS_DIR, "2_health check.md")
CLEAN_FILE = os.path.join(TASKS_DIR, "3_deep clean.md")

FILES = {
    "todo": (TODO_FILE, "📋 To Do List"),
    "health": (HEALTH_FILE, "🏥 Health Check"),
    "clean": (CLEAN_FILE, "🧹 Deep Clean"),
}
