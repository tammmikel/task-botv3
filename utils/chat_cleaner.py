import asyncio
import logging
from typing import Dict, List, Optional
from aiogram.types import Message

logger = logging.getLogger(__name__)

class ChatCleaner:
    def __init__(self):
        # Храним ID всех сообщений бота для каждого пользователя
        self.bot_messages: Dict[int, List[int]] = {}
        # Запоминаем ID сообщения с основной клавиатурой
        self.keyboard_messages: Dict[int, int] = {}
        
    async def clear_and_send(self, message: Message, text: str, **kwargs) -> Message:
        """Очищает чат и отправляет новое сообщение"""
        user_id = message.from_user.id
        
        # Удаляем сообщение пользователя
        try:
            await message.delete()
        except:
            pass
        
        # Удаляем все предыдущие сообщения бота (КРОМЕ сообщения с основной клавиатурой)
        if user_id in self.bot_messages:
            keyboard_msg_id = self.keyboard_messages.get(user_id)
            
            for msg_id in self.bot_messages[user_id]:
                # НЕ удаляем сообщение с основной клавиатурой
                if msg_id != keyboard_msg_id:
                    try:
                        await message.bot.delete_message(user_id, msg_id)
                    except:
                        pass
            
            # Очищаем список (оставляем только сообщение с клавиатурой)
            if keyboard_msg_id:
                self.bot_messages[user_id] = [keyboard_msg_id]
            else:
                self.bot_messages[user_id] = []
        
        # Отправляем новое сообщение
        bot_message = await message.answer(text, **kwargs)
        
        # Сохраняем ID нового сообщения
        if user_id not in self.bot_messages:
            self.bot_messages[user_id] = []
        self.bot_messages[user_id].append(bot_message.message_id)
        
        # Если это сообщение с ReplyKeyboardMarkup, запоминаем его как основное
        if 'reply_markup' in kwargs and hasattr(kwargs['reply_markup'], 'keyboard'):
            self.keyboard_messages[user_id] = bot_message.message_id
        
        return bot_message
    
    async def edit_last_message(self, callback_query, text: str, **kwargs) -> None:
        """Редактирует последнее сообщение (для callback-ов)"""
        await callback_query.message.edit_text(text, **kwargs)

# Глобальный экземпляр
chat_cleaner = ChatCleaner()