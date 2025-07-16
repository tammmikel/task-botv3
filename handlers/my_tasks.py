from aiogram import Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F
from database.models import UserManager, TaskManager, FileManager
from utils.keyboards import get_main_keyboard, get_task_status_keyboard
from datetime import datetime
import logging
from utils.chat_cleaner import chat_cleaner
from utils.decorators import smart_clear_chat

logger = logging.getLogger(__name__)

# Глобальные названия статусов для переиспользования
STATUS_NAMES = {
    'new': 'Новая',
    'in_progress': 'В работе', 
    'completed': 'Выполнена',
    'overdue': 'Просрочена',
    'cancelled': 'Отменена'
}

@smart_clear_chat
async def my_tasks_handler(message: Message):
    """Обработчик кнопки 'Мои задачи'"""
    try:
        logger.info(f"Просмотр задач от пользователя {message.from_user.id}")
        
        # Получаем пользователя
        user = await UserManager.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден.")
            return
        
        # Получаем задачи пользователя
        tasks = await TaskManager.get_user_tasks(user['user_id'], user['role'])
        
        if not tasks:
            await message.answer(
                "📝 У вас пока нет задач",
                reply_markup=get_main_keyboard(user['role'])
            )
            return
        
        # Формируем кнопки управления
        control_buttons = [
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_tasks"),
             InlineKeyboardButton(text="🏢 Фильтр по компаниям", callback_data="filter_companies")]
        ]
        
        # Формируем кнопки с задачами
        task_buttons = []
        for task in tasks[:15]:  # Показываем первые 15 задач
            # Формируем текст кнопки
            urgent_emoji = "🔥" if task.get('is_urgent', False) else ""
            
            # Ограничиваем длину названия для кнопки
            title_short = task['title'][:30] + "..." if len(task['title']) > 30 else task['title']
            company_short = task['company_name'][:15] + "..." if len(task['company_name']) > 15 else task['company_name']
            
            button_text = f"{task['status_emoji']}{urgent_emoji} {title_short} | {company_short} | {task.get('deadline_short', '')}"
            
            task_buttons.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"task_{task['task_id']}"
            )])
        
        # Объединяем все кнопки
        keyboard = control_buttons + task_buttons
        
        tasks_text = f"📝 Ваши задачи ({len(tasks)}):"
        if len(tasks) > 15:
            tasks_text += f"\n\nПоказано первые 15 из {len(tasks)} задач"
        
        # Отправляем список (декоратор автоматически очистит чат)
        await message.answer(
            tasks_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в my_tasks_handler: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def process_task_callback(callback: CallbackQuery):
    """Обработчик нажатий на задачи"""
    try:
        data = callback.data
        logger.info(f"Callback задачи: {data} от пользователя {callback.from_user.id}")
        
        if data.startswith("task_"):
            task_id = data.replace("task_", "")
            
            # Получаем детали задачи
            task = await TaskManager.get_task_by_id(task_id)
            if not task:
                await callback.answer("❌ Задача не найдена")
                return
            
            # Получаем файлы задачи
            files = await FileManager.get_task_files(task_id)
            
            # Получаем пользователя для определения прав
            user = await UserManager.get_user_by_telegram_id(callback.from_user.id)
            
            # Формируем детальное описание
            detail_text = f"📋 {task['title']}\n\n"
            detail_text += f"📝 Описание: {task['description']}\n"
            detail_text += f"🏢 Компания: {task['company_name']}\n"
            
            if task.get('is_urgent', False):
                detail_text += f"⚡ Приоритет: 🔥 Срочная\n"
            else:
                detail_text += f"⚡ Приоритет: 📝 Обычная\n"
            
            status_name = STATUS_NAMES.get(task['status'], task['status'])
            detail_text += f"📊 Статус: {task.get('status_emoji', '❓')} {status_name}\n"
            detail_text += f"📅 Дедлайн: {task['deadline_str']}\n"
            detail_text += f"📞 Инициатор: {task['initiator_name']}\n"
            detail_text += f"☎️ Телефон: {task['initiator_phone']}\n"
            
            if files:
                detail_text += f"\n📎 Файлы ({len(files)}):\n"
                for file in files:
                    # Получаем размер файла в читаемом формате
                    size_mb = file['file_size'] / (1024 * 1024)
                    if size_mb < 1:
                        size_str = f"{file['file_size'] / 1024:.1f} КБ"
                    else:
                        size_str = f"{size_mb:.1f} МБ"
                    
                    detail_text += f"• {file['file_name']} ({size_str})\n"
                    detail_text += f"  👤 Загрузил: {file['uploader_name']}\n"
            
            # Создаем кнопки действий
            action_buttons = []
            
            # Кнопка изменения статуса (только для исполнителей и руководства)
            task_assignee_id = task.get('assignee_id')
            if user and (user['user_id'] == task_assignee_id or user['role'] in ['director', 'manager']):
                action_buttons.append([InlineKeyboardButton(
                    text="🔄 Изменить статус", 
                    callback_data=f"status_{task_id}"
                )])
            
            # Кнопка комментариев
            action_buttons.append([InlineKeyboardButton(
                text="💬 Комментарии", 
                callback_data=f"comments_{task_id}"
            )])
            
            # Кнопка файлов
            if files:
                action_buttons.append([InlineKeyboardButton(
                    text="📎 Скачать файлы", 
                    callback_data=f"files_{task_id}"
                )])
            
            action_buttons.append([InlineKeyboardButton(
                text="🔙 Назад к списку", 
                callback_data="back_to_tasks"
            )])
            
            await callback.message.edit_text(
                detail_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=action_buttons)
            )
            
        elif data.startswith("status_"):
            task_id = data.replace("status_", "")
            
            # Получаем задачу и пользователя
            task = await TaskManager.get_task_by_id(task_id)
            user = await UserManager.get_user_by_telegram_id(callback.from_user.id)
            
            if not task or not user:
                await callback.answer("❌ Ошибка доступа")
                return
            
            # Формируем кнопки статусов
            status_buttons = []
            current_status = task['status']
            
            # Логика для всех пользователей кто может менять статус
            if current_status == 'new':
                status_buttons.append([InlineKeyboardButton(text="⏳ Взять в работу", callback_data=f"set_status_{task_id}_in_progress")])
            elif current_status == 'in_progress':
                status_buttons.append([InlineKeyboardButton(text="✅ Завершить", callback_data=f"set_status_{task_id}_completed")])
                # Можно вернуть обратно в новые
                status_buttons.append([InlineKeyboardButton(text="🆕 Вернуть в новые", callback_data=f"set_status_{task_id}_new")])
            elif current_status == 'overdue':
                # Просроченную можно завершить или вернуть в работу
                status_buttons.append([InlineKeyboardButton(text="✅ Завершить", callback_data=f"set_status_{task_id}_completed")])
                status_buttons.append([InlineKeyboardButton(text="⏳ Вернуть в работу", callback_data=f"set_status_{task_id}_in_progress")])
            
            # Директор и менеджер могут:
            if user['role'] in ['director', 'manager']:
                # Вернуть выполненную задачу в работу
                if current_status == 'completed':
                    status_buttons.append([InlineKeyboardButton(text="⏳ Вернуть в работу", callback_data=f"set_status_{task_id}_in_progress")])
                
                # Отменить любую незавершенную задачу
                if current_status not in ['cancelled', 'completed']:
                    status_buttons.append([InlineKeyboardButton(text="❌ Отменить задачу", callback_data=f"set_status_{task_id}_cancelled")])
            
            status_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"task_{task_id}")])
            
            current_status_name = STATUS_NAMES.get(current_status, current_status)
            await callback.message.edit_text(
                f"📊 Изменение статуса задачи\n\n"
                f"📋 Задача: {task['title']}\n"
                f"📊 Текущий статус: {current_status_name}\n\n"
                f"Выберите новый статус:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=status_buttons)
            )
            
        elif data.startswith("set_status_"):
            # Изменение статуса
            parts = data.split("_", 3)  # Ограничиваем разделение
            task_id = parts[2]
            new_status = parts[3]
            
            # Получаем пользователя
            user = await UserManager.get_user_by_telegram_id(callback.from_user.id)
            
            if not user:
                await callback.answer("❌ Ошибка доступа")
                return
            
            # Обновляем статус
            if await TaskManager.update_task_status(task_id, new_status):
                status_name = STATUS_NAMES.get(new_status, new_status)
                
                await callback.answer(f"✅ Статус изменен на: {status_name}")
                
                # Возвращаемся к детальному просмотру задачи
                await process_task_callback_by_id(callback, task_id)
                
                logger.info(f"Статус задачи {task_id} изменен на {new_status} пользователем {user['user_id']}")
            else:
                await callback.answer("❌ Ошибка изменения статуса")
            
        elif data == "filter_companies":
            # Показываем фильтр по компаниям
            telegram_id = callback.from_user.id
            user = await UserManager.get_user_by_telegram_id(telegram_id)
            companies = await TaskManager.get_companies_with_tasks(user['user_id'], user['role'])
            
            keyboard = []
            for company in companies:
                keyboard.append([InlineKeyboardButton(
                    text=f"{company['name']} ({company['task_count']})",
                    callback_data=f"company_{company['company_id']}"
                )])
            
            keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_tasks")])
            
            await callback.message.edit_text(
                "🏢 Выберите компанию для фильтрации:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
            
        elif data == "back_to_tasks":
            # Возвращаемся к списку задач
            await show_tasks_list(callback)
            
        elif data == "refresh_tasks":
            # Получаем обновленный список задач
            await show_tasks_list(callback, "✅ Список обновлен")

        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в process_task_callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await callback.answer("❌ Произошла ошибка")

async def process_task_callback_by_id(callback: CallbackQuery, task_id: str):
    """Показать детали задачи по ID"""
    # Вызываем напрямую код обработки задачи
    try:
        # Получаем детали задачи
        task = await TaskManager.get_task_by_id(task_id)
        if not task:
            await callback.answer("❌ Задача не найдена")
            return
        
        # Получаем файлы задачи
        files = await FileManager.get_task_files(task_id)
        
        # Получаем пользователя для определения прав
        user = await UserManager.get_user_by_telegram_id(callback.from_user.id)
        
        # Формируем детальное описание
        detail_text = f"📋 {task['title']}\n\n"
        detail_text += f"📝 Описание: {task['description']}\n"
        detail_text += f"🏢 Компания: {task['company_name']}\n"
        
        if task.get('is_urgent', False):
            detail_text += f"⚡ Приоритет: 🔥 Срочная\n"
        else:
            detail_text += f"⚡ Приоритет: 📝 Обычная\n"
        
        status_name = STATUS_NAMES.get(task['status'], task['status'])
        detail_text += f"📊 Статус: {task.get('status_emoji', '❓')} {status_name}\n"
        detail_text += f"📅 Дедлайн: {task['deadline_str']}\n"
        detail_text += f"📞 Инициатор: {task['initiator_name']}\n"
        detail_text += f"☎️ Телефон: {task['initiator_phone']}\n"
        
        if files:
            detail_text += f"\n📎 Файлы ({len(files)}):\n"
            for file in files:
                # Получаем размер файла в читаемом формате
                size_mb = file['file_size'] / (1024 * 1024)
                if size_mb < 1:
                    size_str = f"{file['file_size'] / 1024:.1f} КБ"
                else:
                    size_str = f"{size_mb:.1f} МБ"
                
                detail_text += f"• {file['file_name']} ({size_str})\n"
                detail_text += f"  👤 Загрузил: {file['uploader_name']}\n"
        
        # Создаем кнопки действий
        action_buttons = []
        
        # Кнопка изменения статуса (только для исполнителей и руководства)
        task_assignee_id = task.get('assignee_id')
        if user and (user['user_id'] == task_assignee_id or user['role'] in ['director', 'manager']):
            action_buttons.append([InlineKeyboardButton(
                text="🔄 Изменить статус", 
                callback_data=f"status_{task_id}"
            )])
        
        # Кнопка комментариев
        action_buttons.append([InlineKeyboardButton(
            text="💬 Комментарии", 
            callback_data=f"comments_{task_id}"
        )])
        
        # Кнопка файлов
        if files:
            action_buttons.append([InlineKeyboardButton(
                text="📎 Скачать файлы", 
                callback_data=f"files_{task_id}"
            )])
        
        action_buttons.append([InlineKeyboardButton(
            text="🔙 Назад к списку", 
            callback_data="back_to_tasks"
        )])
        
        await callback.message.edit_text(
            detail_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=action_buttons)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_task_callback_by_id: {e}")
        await callback.answer("❌ Произошла ошибка")

async def show_tasks_list(callback: CallbackQuery, message_prefix: str = ""):
    """Показать список задач"""
    try:
        telegram_id = callback.from_user.id
        user = await UserManager.get_user_by_telegram_id(telegram_id)
        tasks = await TaskManager.get_user_tasks(user['user_id'], user['role'])
        
        if not tasks:
            await callback.message.edit_text("📝 У вас пока нет задач")
            return
        
        # Формируем кнопки как в основном обработчике
        control_buttons = [
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_tasks"),
             InlineKeyboardButton(text="🏢 Фильтр по компаниям", callback_data="filter_companies")]
        ]
        
        task_buttons = []
        for task in tasks[:15]:
            urgent_emoji = "🔥" if task.get('is_urgent', False) else ""
            
            status_name = STATUS_NAMES.get(task['status'], task['status'])
            title_short = task['title'][:30] + "..." if len(task['title']) > 30 else task['title']
            company_short = task['company_name'][:15] + "..." if len(task['company_name']) > 15 else task['company_name']
            
            # Отладка - посмотрим что точно в task['status']
            print(f"DEBUG: task status = '{task['status']}'")
            status_name = STATUS_NAMES.get(task['status'], task['status'])
            button_text = f"{task['status_emoji']}{urgent_emoji} {title_short} | {company_short} | {task.get('deadline_short', '')}"
            
            task_buttons.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"task_{task['task_id']}"
            )])
        
        keyboard = control_buttons + task_buttons
        
        # Добавляем временную метку если это обновление
        tasks_text = f"📝 Ваши задачи ({len(tasks)})"
        if message_prefix:
            current_time = datetime.now().strftime("%H:%M:%S")
            tasks_text += f" - обновлено {current_time}"
        
        if len(tasks) > 15:
            tasks_text += f"\n\nПоказано первые 15 из {len(tasks)} задач"
        
        await callback.message.edit_text(
            tasks_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в show_tasks_list: {e}")

def register_my_tasks_handlers(dp: Dispatcher):
    """Регистрация обработчиков просмотра задач"""
    dp.message.register(my_tasks_handler, F.text == "📝 Мои задачи")
    dp.callback_query.register(process_task_callback, F.data.startswith("task_"))
    dp.callback_query.register(process_task_callback, F.data.startswith("status_"))
    dp.callback_query.register(process_task_callback, F.data.startswith("set_status_"))
    dp.callback_query.register(process_task_callback, F.data == "filter_companies")
    dp.callback_query.register(process_task_callback, F.data == "back_to_tasks")
    dp.callback_query.register(process_task_callback, F.data.startswith("company_"))
    dp.callback_query.register(process_task_callback, F.data == "refresh_tasks")