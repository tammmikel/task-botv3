import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env файле")

# PostgreSQL Database
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'taskbot'),
    'user': os.getenv('DB_USER', 'botuser'),
    'password': os.getenv('DB_PASSWORD')
}

if not DB_CONFIG['password']:
    raise ValueError("DB_PASSWORD не установлен в .env файле")

# File Storage
UPLOAD_PATH = os.getenv('UPLOAD_PATH', '/opt/taskbot/uploads')
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 104857600))  # 100 MB

# Timezone
TIMEZONE_OFFSET = int(os.getenv('TIMEZONE_OFFSET', 5))  # UTC+5

# Создаем папки если их нет
os.makedirs(UPLOAD_PATH, exist_ok=True)
os.makedirs(f"{UPLOAD_PATH}/tasks", exist_ok=True)
os.makedirs("logs", exist_ok=True)