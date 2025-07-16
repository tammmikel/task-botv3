import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from database.connection import db_connection
from database.models import get_current_time
from config import BOT_TOKEN, TIMEZONE_OFFSET
from typing import List, Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
        self.check_interval = 30 * 60  # 30 минут
        
    async def start(self):
        """Запуск планировщика"""
        logger.info("Запуск планировщика задач...")
        
        # Подключение к базе данных
        if not await db_connection.connect():
            logger.error("Не удалось подключиться к базе данных")
            return
        
        # Основной цикл
        while True:
            try:
                await self.check_deadlines()
                await self.check_overdue_tasks()
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                await asyncio.sleep(60)  # Подождать минуту перед повтором
    
    async def check_deadlines(self):
        """Проверка приближающихся дедлайнов (за 2 часа)"""
        try:
            now = get_current_time()
            deadline_threshold = now + timedelta(hours=2)
            
            query = """
            SELECT t.task_id, t.title, t.deadline, t.assignee_id, c.name as company_name,
                   u.telegram_id, u.first_name, u.last_name
            FROM tasks t
            JOIN companies c ON t.company_id = c.company_id
            JOIN users u ON t.assignee_id = u.user_id
            WHERE t.status IN ('new', 'in_progress')
            AND t.deadline <= $1
            AND t.deadline > $2
            """
            
            tasks = await db_connection.execute_query(
                query, deadline_threshold, now
            )
            
            for task in tasks:
                await self.send_deadline_notification(task)
                
            if tasks:
                logger.info(f"Отправлено {len(tasks)} уведомлений о приближающихся дедлайнах")
                
        except Exception as e:
            logger.error(f"Ошибка проверки дедлайнов: {e}")
    
    async def check_overdue_tasks(self):
        """Проверка и обновление просроченных задач"""
        try:
            now = get_current_time()
            
            # Находим задачи которые просрочены но еще не помечены как просроченные
            query = """
            UPDATE tasks 
            SET status = 'overdue', updated_at = NOW()
            WHERE deadline < $1 
            AND status IN ('new', 'in_progress')
            RETURNING task_id, title, assignee_id
            """
            
            overdue_tasks = await db_connection.execute_query(query, now)
            
            # Уведомляем исполнителей о просроченных задачах
            for task in overdue_tasks:
                await self.send_overdue_notification(task)
            
            if overdue_tasks:
                logger.info(f"Обновлено {len(overdue_tasks)} просроченных задач")
                
        except Exception as e:
            logger.error(f"Ошибка обновления просроченных задач: {e}")
    
    async def send_deadline_notification(self, task: Dict[str, Any]):
        """Отправка уведомления о приближающемся дедлайне"""
        try:
            telegram_id = task['telegram_id']
            name = f"{task['first_name'] or ''} {task['last_name'] or ''}".strip()
            if not name:
                name = "Исполнитель"
            
            deadline_str = task['deadline'].strftime('%d.%m.%Y %H:%M')
            
            message = (
                f"⏰ Напоминание о дедлайне!\n\n"
                f"📋 Задача: {task['title']}\n"
                f"🏢 Компания: {task['company_name']}\n"
                f"📅 Дедлайн: {deadline_str}\n\n"
                f"До дедлайна осталось менее 2 часов!"
            )
            
            await self.bot.send_message(telegram_id, message)
            logger.info(f"Уведомление о дедлайне отправлено пользователю {telegram_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о дедлайне: {e}")
    
    async def send_overdue_notification(self, task: Dict[str, Any]):
        """Отправка уведомления о просроченной задаче"""
        try:
            # Получаем telegram_id исполнителя
            query = "SELECT telegram_id, first_name, last_name FROM users WHERE user_id = $1"
            user = await db_connection.execute_one(query, task['assignee_id'])
            
            if user:
                telegram_id = user['telegram_id']
                name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
                if not name:
                    name = "Исполнитель"
                
                message = (
                    f"⚠️ Задача просрочена!\n\n"
                    f"📋 Задача: {task['title']}\n"
                    f"❗ Статус изменен на 'Просрочена'\n\n"
                    f"Пожалуйста, завершите задачу как можно скорее."
                )
                
                await self.bot.send_message(telegram_id, message)
                logger.info(f"Уведомление о просрочке отправлено пользователю {telegram_id}")
                
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о просрочке: {e}")
    
    async def send_status_change_notification(self, task_id: str, new_status: str, 
                                            changed_by_id: str):
        """Отправка уведомлений об изменении статуса задачи"""
        try:
            # Получаем информацию о задаче
            query = """
            SELECT t.title, t.assignee_id, t.created_by, c.name as company_name,
                   assignee.telegram_id as assignee_telegram,
                   creator.telegram_id as creator_telegram
            FROM tasks t
            JOIN companies c ON t.company_id = c.company_id
            JOIN users assignee ON t.assignee_id = assignee.user_id
            JOIN users creator ON t.created_by = creator.user_id
            WHERE t.task_id = $1
            """
            
            task = await db_connection.execute_one(query, task_id)
            if not task:
                return
            
            status_names = {
                'new': 'Новая',
                'in_progress': 'В работе',
                'completed': 'Выполнена',
                'overdue': 'Просрочена',
                'cancelled': 'Отменена'
            }
            
            status_text = status_names.get(new_status, new_status)
            
            message = (
                f"📋 Изменение статуса задачи\n\n"
                f"Задача: {task['title']}\n"
                f"🏢 Компания: {task['company_name']}\n"
                f"📊 Новый статус: {status_text}"
            )
            
            # Уведомляем всех участников кроме того кто изменил
            recipients = set()
            recipients.add(task['assignee_telegram'])
            recipients.add(task['creator_telegram'])
            
            # Исключаем того кто изменил статус
            changer_query = "SELECT telegram_id FROM users WHERE user_id = $1"
            changer = await db_connection.execute_one(changer_query, changed_by_id)
            if changer:
                recipients.discard(changer['telegram_id'])
            
            for telegram_id in recipients:
                try:
                    await self.bot.send_message(telegram_id, message)
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления пользователю {telegram_id}: {e}")
            
            logger.info(f"Уведомления об изменении статуса отправлены ({len(recipients)} получателей)")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомлений об изменении статуса: {e}")
    
    async def stop(self):
        """Остановка планировщика"""
        logger.info("Остановка планировщика...")
        await self.bot.session.close()
        await db_connection.close()

async def main():
    """Основная функция планировщика"""
    scheduler = TaskScheduler()
    
    try:
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Планировщик остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка планировщика: {e}")
    finally:
        await scheduler.stop()

if __name__ == "__main__":
    asyncio.run(main())