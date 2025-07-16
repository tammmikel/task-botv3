import functools
from aiogram.types import Message, CallbackQuery
from .chat_cleaner import chat_cleaner
import logging

logger = logging.getLogger(__name__)

def smart_clear_chat(func):
    """Декоратор для автоматической очистки чата"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Находим объект Message в аргументах
        message = None
        for arg in args:
            if isinstance(arg, Message):
                message = arg
                break
        
        if message is None:
            # Если Message не найден, выполняем функцию как обычно
            return await func(*args, **kwargs)
        
        # Создаем обертку для функции, которая будет перехватывать вызовы
        class MessageWrapper:
            def __init__(self, original_message):
                self.original_message = original_message
                self._first_answer = True
            
            def __getattr__(self, name):
                return getattr(self.original_message, name)
            
            async def answer(self, text, **kwargs):
                if self._first_answer:
                    self._first_answer = False
                    return await chat_cleaner.clear_and_send(self.original_message, text, **kwargs)
                else:
                    return await self.original_message.answer(text, **kwargs)
        
        # Заменяем message в аргументах
        new_args = []
        for arg in args:
            if isinstance(arg, Message):
                new_args.append(MessageWrapper(arg))
            else:
                new_args.append(arg)
        
        # Выполняем функцию с обернутым message
        return await func(*new_args, **kwargs)
    
    return wrapper