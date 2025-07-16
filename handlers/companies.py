from aiogram import Dispatcher
from aiogram.types import Message
from aiogram import F
from aiogram.fsm.context import FSMContext
from database.models import UserManager, CompanyManager
from utils.keyboards import get_main_keyboard, get_company_management_keyboard, get_back_keyboard, get_skip_keyboard
from utils.states import CompanyStates
import logging
from utils.decorators import smart_clear_chat

logger = logging.getLogger(__name__)

@smart_clear_chat
async def company_management_handler(message: Message):
    """Обработчик кнопки 'Управление компаниями'"""
    try:
        logger.info(f"Управление компаниями от пользователя {message.from_user.id}")
        telegram_id = message.from_user.id
        
        # Проверяем права пользователя
        user = await UserManager.get_user_by_telegram_id(telegram_id)
        if not user or user['role'] not in ['director', 'manager']:
            await message.answer(
                message,
                "❌ У вас нет прав для управления компаниями.",
                reply_markup=get_main_keyboard(user['role'] if user else 'admin')
            )
            return
        
        await message.answer(
            message,
            "🏢 Управление компаниями\n\n"
            "Выберите действие:",
            reply_markup=get_company_management_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в company_management_handler: {e}")
        await chat_cleaner.clear_and_send(message, "❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def add_company_handler(message: Message, state: FSMContext):
    """Обработчик кнопки 'Добавить компанию'"""
    try:
        logger.info(f"Добавление компании от пользователя {message.from_user.id}")
        telegram_id = message.from_user.id
        
        # Проверяем права пользователя
        user = await UserManager.get_user_by_telegram_id(telegram_id)
        if not user or user['role'] not in ['director', 'manager']:
            await message.answer("❌ У вас нет прав для добавления компаний.")
            return
        
        # Сохраняем данные пользователя в состоянии
        await state.update_data(created_by=user['user_id'])
        
        # Переходим в состояние ожидания названия
        await state.set_state(CompanyStates.waiting_for_name)
        
        await message.answer(
            "📝 Добавление новой компании\n\n"
            "Введите название компании:",
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в add_company_handler: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def list_companies_handler(message: Message):
    """Обработчик кнопки 'Список компаний'"""
    try:
        logger.info(f"Список компаний от пользователя {message.from_user.id}")
        telegram_id = message.from_user.id
        
        # Проверяем права пользователя
        user = await UserManager.get_user_by_telegram_id(telegram_id)
        if not user or user['role'] not in ['director', 'manager']:
            await message.answer("❌ У вас нет прав для просмотра компаний.")
            return
        
        # Получаем список компаний
        companies = await CompanyManager.get_all_companies()
        
        if not companies:
            await message.answer(
                "📋 Список компаний пуст\n\n"
                "Добавьте первую компанию с помощью кнопки 'Добавить компанию'.",
                reply_markup=get_company_management_keyboard()
            )
        else:
            company_list = "📋 Список компаний:\n\n"
            for i, company in enumerate(companies, 1):
                company_list += f"{i}. **{company['name']}**\n"
                if company['description']:
                    company_list += f"   📝 {company['description']}\n"
                company_list += f"   📅 Создана: {company['created_at'].strftime('%d.%m.%Y')}\n\n"
            
            # Разбиваем длинные сообщения
            if len(company_list) > 4000:
                parts = []
                current_part = "📋 Список компаний:\n\n"
                
                for i, company in enumerate(companies, 1):
                    company_text = f"{i}. **{company['name']}**\n"
                    if company['description']:
                        company_text += f"   📝 {company['description']}\n"
                    company_text += f"   📅 Создана: {company['created_at'].strftime('%d.%m.%Y')}\n\n"
                    
                    if len(current_part + company_text) > 4000:
                        parts.append(current_part)
                        current_part = company_text
                    else:
                        current_part += company_text
                
                if current_part:
                    parts.append(current_part)
                
                # Отправляем по частям
                for part in parts:
                    await message.answer(part, parse_mode="Markdown")
                
                await message.answer(
                    "📋 Это все компании.",
                    reply_markup=get_company_management_keyboard()
                )
            else:
                await message.answer(
                    company_list,
                    reply_markup=get_company_management_keyboard(),
                    parse_mode="Markdown"
                )
        
    except Exception as e:
        logger.error(f"Ошибка в list_companies_handler: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def back_to_main_handler(message: Message, state: FSMContext):
    """Обработчик кнопки 'Назад' - возврат в главное меню"""
    try:
        logger.info(f"Возврат в главное меню от пользователя {message.from_user.id}")
        
        # Очищаем состояние
        await state.clear()
        
        telegram_id = message.from_user.id
        
        # Получаем пользователя для определения роли
        user = await UserManager.get_user_by_telegram_id(telegram_id)
        role = user['role'] if user else 'admin'
        
        role_names = {
            'director': "Директор",
            'manager': "Менеджер",
            'main_admin': "Главный администратор", 
            'admin': "Системный администратор"
        }
        
        role_text = role_names.get(role, "Неизвестная роль")
        
        await message.answer(
            f"🏠 Главное меню\n"
            f"Ваша роль: {role_text}",
            reply_markup=get_main_keyboard(role)
        )
        
    except Exception as e:
        logger.error(f"Ошибка в back_to_main_handler: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_company_name(message: Message, state: FSMContext):
    """Обработчик ввода названия компании"""
    try:
        logger.info(f"Обработка названия компании от пользователя {message.from_user.id}")
        
        # Проверяем корректность названия
        company_name = message.text.strip()
        if len(company_name) < 2:
            await message.answer(
                "❌ Название компании слишком короткое!\n\n"
                "Введите название компании (минимум 2 символа):",
                reply_markup=get_back_keyboard()
            )
            return
        
        if len(company_name) > 255:
            await message.answer(
                "❌ Название компании слишком длинное!\n\n"
                "Введите название компании (максимум 255 символов):",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Сохраняем название
        await state.update_data(company_name=company_name)
        
        # Переходим к описанию
        await state.set_state(CompanyStates.waiting_for_description)
        
        await message.answer(
            f"✅ Название: **{company_name}**\n\n"
            f"📝 Теперь введите описание компании (необязательно):\n\n"
            f"Или нажмите 'Пропустить', чтобы создать компанию без описания.",
            reply_markup=get_skip_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_company_name: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_company_description(message: Message, state: FSMContext):
    """Обработчик ввода описания компании"""
    try:
        logger.info(f"Обработка описания компании от пользователя {message.from_user.id}")
        
        # Получаем данные из состояния
        data = await state.get_data()
        company_name = data.get('company_name')
        created_by = data.get('created_by')
        
        description = None
        if message.text != "⏭️ Пропустить":
            description = message.text.strip()
            if len(description) > 1000:
                await message.answer(
                    "❌ Описание слишком длинное!\n\n"
                    "Введите описание компании (максимум 1000 символов):",
                    reply_markup=get_skip_keyboard()
                )
                return
        
        # Создаем компанию
        company_id = await CompanyManager.create_company(
            name=company_name,
            description=description,
            created_by=created_by
        )
        
        # Очищаем состояние
        await state.clear()
        
        if company_id:
            result_text = f"✅ Компания успешно создана!\n\n"
            result_text += f"📌 Название: **{company_name}**\n"
            if description:
                result_text += f"📝 Описание: {description}\n"
            result_text += f"🆔 ID: `{company_id}`"
            
            await message.answer(
                result_text,
                reply_markup=get_company_management_keyboard(),
                parse_mode="Markdown"
            )
            
            logger.info(f"Компания '{company_name}' создана с ID: {company_id}")
        else:
            await message.answer(
                "❌ Ошибка при создании компании. Попробуйте позже.",
                reply_markup=get_company_management_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Ошибка в process_company_description: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def skip_description_handler(message: Message, state: FSMContext):
    """Обработчик кнопки 'Пропустить' для описания"""
    await process_company_description(message, state)

def register_company_handlers(dp: Dispatcher):
    """Регистрация обработчиков для управления компаниями"""
    # Основные обработчики
    dp.message.register(company_management_handler, F.text == "🏢 Управление компаниями")
    dp.message.register(add_company_handler, F.text == "➕ Добавить компанию")
    dp.message.register(list_companies_handler, F.text == "📋 Список компаний")
    dp.message.register(back_to_main_handler, F.text == "🔙 Назад")
    
    # Обработчики состояний FSM
    dp.message.register(process_company_name, CompanyStates.waiting_for_name)
    dp.message.register(process_company_description, CompanyStates.waiting_for_description)
    dp.message.register(skip_description_handler, F.text == "⏭️ Пропустить")