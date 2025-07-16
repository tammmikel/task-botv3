import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.memory import MemoryStorage
from database.connection import db_connection
from database.models import DatabaseManager
from handlers.start import register_start_handlers
from handlers.companies import register_company_handlers
from handlers.tasks import register_task_handlers
from handlers.my_tasks import register_my_tasks_handlers
from config import BOT_TOKEN

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Настройки webhook
WEBHOOK_HOST = "apps.zakrepi.ru"  # Твой домен через прокси
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Настройки веб-сервера (слушаем на свободном порту)
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 8080  # Свободный порт

# Создание экземпляров бота и диспетчера
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

async def init_database():
    """Инициализация базы данных"""
    try:
        # Подключение к базе
        if not await db_connection.connect():
            raise Exception("Не удалось подключиться к базе данных")
        
        # Создание таблиц
        await DatabaseManager.create_tables()
        logger.info("База данных инициализирована успешно")
        
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        raise e

def register_handlers():
    """Регистрация всех обработчиков"""
    register_start_handlers(dp)
    register_company_handlers(dp)
    register_task_handlers(dp)
    register_my_tasks_handlers(dp)
    logger.info("Обработчики зарегистрированы")

async def on_startup():
    """Действия при запуске"""
    try:
        # Инициализация базы данных
        await init_database()
        
        # Регистрация обработчиков
        register_handlers()
        
        # Установка webhook
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook установлен: {WEBHOOK_URL}")
        
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
        raise e

async def on_shutdown():
    """Действия при остановке"""
    try:
        # Удаление webhook
        await bot.delete_webhook()
        logger.info("Webhook удален")
        
        # Закрытие соединений
        await db_connection.close()
        await bot.session.close()
        logger.info("Соединения закрыты")
        
    except Exception as e:
        logger.error(f"Ошибка при остановке: {e}")

def create_app():
    """Создание веб-приложения"""
    app = web.Application()
    
    # Настройка webhook обработчика
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Настройка приложения
    setup_application(app, dp, bot=bot)
    
    # Добавляем обработчики событий
    app.on_startup.append(lambda app: asyncio.create_task(on_startup()))
    app.on_cleanup.append(lambda app: asyncio.create_task(on_shutdown()))
    
    return app

async def main():
    """Основная функция запуска"""
    try:
        logger.info("Запуск webhook сервера...")
        
        # Создание приложения
        app = create_app()
        
        # Запуск веб-сервера
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
        await site.start()
        
        logger.info(f"Webhook сервер запущен на {WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
        logger.info(f"Webhook URL: {WEBHOOK_URL}")
        
        # Ожидание завершения
        try:
            await asyncio.Future()  # Ждем бесконечно
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        finally:
            await runner.cleanup()
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise e

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        exit(1)