from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from database.models import UserManager
from utils.keyboards import get_main_keyboard
import logging
from utils.decorators import smart_clear_chat

logger = logging.getLogger(__name__)

@smart_clear_chat
async def start_command(message: Message):
    """Обработчик команды /start"""
    try:
        logger.info(f"Команда /start от пользователя {message.from_user.id}")
        
        telegram_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        
        # Проверяем, существует ли пользователь
        existing_user = await UserManager.get_user_by_telegram_id(telegram_id)
        
        if existing_user:
            # Пользователь уже существует
            role = existing_user['role']
            logger.info(f"Пользователь {telegram_id} найден с ролью: {role}")
            
            role_names = {
                'director': "Директор",
                'manager': "Менеджер", 
                'main_admin': "Главный администратор",
                'admin': "Системный администратор"
            }
            
            role_text = role_names.get(role, "Неизвестная роль")
            
            response_text = f"Добро пожаловать обратно!\nВаша роль: {role_text}"
            
            await message.answer(
                message,
                response_text,
                reply_markup=get_main_keyboard(role)
            )
        else:
            logger.info(f"Создание нового пользователя: {telegram_id}")
            # Создаем нового пользователя
            users_count = await UserManager.get_users_count()
            logger.info(f"Общее количество пользователей: {users_count}")
            
            # Первый пользователь становится директором
            if users_count == 0:
                role = 'director'
                role_text = "Директор"
                welcome_text = (
                    f"🎉 Добро пожаловать в систему управления задачами!\n\n"
                    f"Вы первый пользователь и получили роль: {role_text}\n\n"
                    f"Ваши возможности:\n"
                    f"• Создавать компании\n"
                    f"• Ставить задачи\n"
                    f"• Управлять ролями сотрудников\n"
                    f"• Просматривать аналитику\n\n"
                    f"Используйте кнопки ниже для навигации."
                )
            else:
                role = 'admin'
                role_text = "Системный администратор"
                welcome_text = (
                    f"👋 Добро пожаловать в систему управления задачами!\n\n"
                    f"Ваша роль: {role_text}\n\n"
                    f"Ваши возможности:\n"
                    f"• Просматривать свои задачи\n"
                    f"• Изменять статус задач\n"
                    f"• Добавлять комментарии к задачам\n"
                    f"• Прикреплять файлы\n\n"
                    f"Директор может изменить вашу роль при необходимости."
                )
            
            # Создаем пользователя в базе
            user_id = await UserManager.create_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role
            )
            
            if user_id:
                logger.info(f"Пользователь {telegram_id} создан с ID: {user_id}")
                await message.answer(
                    message,
                    welcome_text,
                    reply_markup=get_main_keyboard(role)
                )
            else:
                logger.error(f"Ошибка создания пользователя {telegram_id}")
                await message.answer(
                    message,
                    "❌ Произошла ошибка при регистрации. Попробуйте позже."
                )
                
    except Exception as e:
        logger.error(f"Ошибка в start_command: {e}")
        await message.answer(
            message,
            "❌ Произошла ошибка. Попробуйте позже."
        )

def register_start_handlers(dp: Dispatcher):
    """Регистрация обработчиков команды start"""
    dp.message.register(start_command, Command("start"))