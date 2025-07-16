from aiogram import Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F
from aiogram.fsm.context import FSMContext
from database.models import UserManager, CompanyManager, TaskManager
from utils.keyboards import get_main_keyboard, get_back_keyboard, get_task_urgent_keyboard, get_task_deadline_keyboard
from utils.states import TaskStates
from utils.file_storage import file_storage
from datetime import datetime, timedelta
import calendar
import logging
from utils.decorators import smart_clear_chat

logger = logging.getLogger(__name__)

@smart_clear_chat
async def create_task_handler(message: Message, state: FSMContext):
    """Обработчик кнопки 'Создать задачу'"""
    try:
        logger.info(f"Создание задачи от пользователя {message.from_user.id}")
        telegram_id = message.from_user.id
        
        # Проверяем права пользователя
        user = await UserManager.get_user_by_telegram_id(telegram_id)
        if not user or user['role'] not in ['director', 'manager']:
            await message.answer(
                "❌ У вас нет прав для создания задач.",
                reply_markup=get_main_keyboard(user['role'] if user else 'admin')
            )
            return
        
        # Сохраняем данные пользователя в состоянии
        await state.update_data(created_by=user['user_id'])
        
        # Переходим в состояние ожидания названия
        await state.set_state(TaskStates.waiting_for_title)
        
        await message.answer(
            "📋 Создание новой задачи\n\n"
            "**Шаг 1/7:** Введите название задачи:",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в create_task_handler: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_task_title(message: Message, state: FSMContext):
    """Обработчик ввода названия задачи"""
    try:
        logger.info(f"Обработка названия задачи от пользователя {message.from_user.id}")
        
        # Проверяем корректность названия
        task_title = message.text.strip()
        if len(task_title) < 3:
            await message.answer(
                "❌ Название задачи слишком короткое!\n\n"
                "Введите название задачи (минимум 3 символа):",
                reply_markup=get_back_keyboard()
            )
            return
        
        if len(task_title) > 500:
            await message.answer(
                "❌ Название задачи слишком длинное!\n\n"
                "Введите название задачи (максимум 500 символов):",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Сохраняем название
        await state.update_data(task_title=task_title)
        
        # Переходим к описанию
        await state.set_state(TaskStates.waiting_for_description)
        
        await message.answer(
            f"✅ Название: {task_title}\n\n"
            f"Шаг 2/7: Введите описание задачи:\n\n"
            f"💡 Можете также прикрепить файлы или фото к описанию.",
            reply_markup=get_back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_task_title: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_task_description(message: Message, state: FSMContext):
    """Обработчик ввода описания задачи (текст или файлы)"""
    try:
        logger.info(f"Обработка описания задачи от пользователя {message.from_user.id}")
        
        task_description = ""
        task_files = []
        
        # Обрабатываем текст
        if message.text:
            task_description = message.text.strip()
            if len(task_description) > 2000:
                await message.answer(
                    "❌ Описание задачи слишком длинное!\n\n"
                    "Введите описание задачи (максимум 2000 символов):",
                    reply_markup=get_back_keyboard()
                )
                return
        
        # Обрабатываем подпись к фото/файлу
        elif message.caption:
            task_description = message.caption.strip()
            if len(task_description) > 2000:
                await message.answer(
                    "❌ Описание задачи слишком длинное!\n\n"
                    "Введите описание задачи (максимум 2000 символов):",
                    reply_markup=get_back_keyboard()
                )
                return
        
        # Обрабатываем фото
        if message.photo:
            # Берем фото наибольшего размера
            photo = message.photo[-1]
            await message.answer("📷 Фото получено! Обрабатываем...")
            
            # Скачиваем файл
            from main import bot
            file_obj = await bot.get_file(photo.file_id)
            file_data = await bot.download_file(file_obj.file_path)
            
            # Читаем данные
            file_content = file_data.read()
            
            # Проверяем размер
            if not file_storage.validate_file_size(len(file_content)):
                await message.answer(
                    "❌ Файл слишком большой! Максимальный размер: 100 МБ",
                    reply_markup=get_back_keyboard()
                )
                return
            
            task_files.append({
                'type': 'photo',
                'file_id': photo.file_id,
                'file_size': len(file_content),
                'file_name': f"photo_{photo.file_id}.jpg",
                'content_type': 'image/jpeg',
                'file_data': file_content
            })
        
        # Обрабатываем документы
        elif message.document:
            document = message.document
            
            # Проверяем размер файла
            if not file_storage.validate_file_size(document.file_size):
                await message.answer(
                    "❌ Файл слишком большой! Максимальный размер: 100 МБ",
                    reply_markup=get_back_keyboard()
                )
                return
            
            # Проверяем расширение файла
            if not file_storage.validate_file_extension(document.file_name):
                await message.answer(
                    "❌ Неподдерживаемый тип файла!\n\n"
                    "Поддерживаются: изображения, документы PDF/DOC/XLS, архивы ZIP/RAR",
                    reply_markup=get_back_keyboard()
                )
                return
            
            await message.answer("📎 Файл получен! Обрабатываем...")
            
            # Скачиваем файл
            from main import bot
            file_obj = await bot.get_file(document.file_id)
            file_data = await bot.download_file(file_obj.file_path)
            
            # Читаем данные
            file_content = file_data.read()
            
            task_files.append({
                'type': 'document',
                'file_id': document.file_id,
                'file_name': document.file_name,
                'file_size': len(file_content),
                'content_type': file_storage.get_content_type_by_extension(document.file_name),
                'file_data': file_content
            })
        
        # Если нет ни текста, ни подписи, ни файлов
        if not task_description and not task_files:
            await message.answer(
                "❌ Пожалуйста, введите описание задачи или отправьте файл с подписью:",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Если только файлы без описания
        if not task_description:
            task_description = "Файл без описания"
        
        # Сохраняем описание и файлы
        await state.update_data(
            task_description=task_description,
            task_files=task_files
        )
        
        # Получаем список компаний для выбора
        companies = await CompanyManager.get_all_companies()
        
        if not companies:
            await message.answer(
                "❌ В системе нет ни одной компании!\n\n"
                "Сначала создайте компанию через меню 'Управление компаниями'.",
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return
        
        # Создаем клавиатуру с компаниями
        company_keyboard = create_company_keyboard(companies)
        
        # Переходим к выбору компании
        await state.set_state(TaskStates.waiting_for_company)
        
        success_text = "✅ Описание сохранено"
        if task_files:
            success_text += f" (+ {len(task_files)} файл(ов))"
        
        await message.answer(
            f"{success_text}\n\n"
            f"Шаг 3/7: Выберите компанию для задачи:",
            reply_markup=company_keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_task_description: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_company_selection(message: Message, state: FSMContext):
    """Обработчик выбора компании"""
    try:
        logger.info(f"Выбор компании от пользователя {message.from_user.id}")
        
        # Получаем список компаний
        companies = await CompanyManager.get_all_companies()
        selected_company = None
        
        # Ищем выбранную компанию
        for company in companies:
            if company['name'] == message.text:
                selected_company = company
                break
        
        if not selected_company:
            await message.answer(
                "❌ Компания не найдена! Выберите компанию из списка:",
                reply_markup=create_company_keyboard(companies)
            )
            return
        
        # Сохраняем выбранную компанию
        await state.update_data(
            company_id=selected_company['company_id'],
            company_name=selected_company['name']
        )
        
        # Переходим к вводу инициатора
        await state.set_state(TaskStates.waiting_for_initiator_name)
        
        await message.answer(
            f"✅ Компания: **{selected_company['name']}**\n\n"
            f"**Шаг 4/7:** Введите имя инициатора задачи:",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_company_selection: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_initiator_name(message: Message, state: FSMContext):
    """Обработчик ввода имени инициатора"""
    try:
        logger.info(f"Ввод инициатора от пользователя {message.from_user.id}")
        
        initiator_name = message.text.strip()
        if len(initiator_name) < 2:
            await message.answer(
                "❌ Имя инициатора слишком короткое!\n\n"
                "Введите имя инициатора (минимум 2 символа):",
                reply_markup=get_back_keyboard()
            )
            return
        
        if len(initiator_name) > 255:
            await message.answer(
                "❌ Имя инициатора слишком длинное!\n\n"
                "Введите имя инициатора (максимум 255 символов):",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Сохраняем имя инициатора
        await state.update_data(initiator_name=initiator_name)
        
        # Переходим к вводу телефона
        await state.set_state(TaskStates.waiting_for_initiator_phone)
        
        await message.answer(
            f"✅ Инициатор: **{initiator_name}**\n\n"
            f"**Шаг 5/7:** Введите номер телефона инициатора:",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_initiator_name: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_initiator_phone(message: Message, state: FSMContext):
    """Обработчик ввода телефона инициатора"""
    try:
        logger.info(f"Ввод телефона инициатора от пользователя {message.from_user.id}")
        
        phone = message.text.strip()
        
        # Простая валидация телефона
        if len(phone) < 10:
            await message.answer(
                "❌ Номер телефона слишком короткий!\n\n"
                "Введите корректный номер телефона:",
                reply_markup=get_back_keyboard()
            )
            return
        
        if len(phone) > 20:
            await message.answer(
                "❌ Номер телефона слишком длинный!\n\n"
                "Введите корректный номер телефона:",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Сохраняем телефон
        await state.update_data(initiator_phone=phone)
        
        # Получаем список исполнителей
        assignees = await UserManager.get_assignees()
        
        if not assignees:
            await message.answer(
                "❌ В системе нет доступных исполнителей!\n\n"
                "Обратитесь к администратору.",
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return
        
        # Создаем клавиатуру с исполнителями
        assignee_keyboard = create_assignee_keyboard(assignees)
        
        # Переходим к выбору исполнителя
        await state.set_state(TaskStates.waiting_for_assignee)
        
        await message.answer(
            f"✅ Телефон: **{phone}**\n\n"
            f"**Шаг 6/7:** Выберите исполнителя задачи:",
            reply_markup=assignee_keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_initiator_phone: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

def create_company_keyboard(companies):
    """Создает клавиатуру с компаниями"""
    buttons = []
    for company in companies:
        buttons.append([KeyboardButton(text=company['name'])])
    buttons.append([KeyboardButton(text="🔙 Назад")])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def create_assignee_keyboard(assignees):
    """Создает клавиатуру с исполнителями"""
    buttons = []
    for assignee in assignees:
        name = f"{assignee['first_name'] or ''} {assignee['last_name'] or ''}".strip()
        if not name:
            name = assignee['username'] or f"ID: {assignee['telegram_id']}"
        buttons.append([KeyboardButton(text=name)])
    buttons.append([KeyboardButton(text="🔙 Назад")])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def register_task_handlers(dp: Dispatcher):
    """Регистрация обработчиков для управления задачами"""
    # Основные обработчики
    dp.message.register(create_task_handler, F.text == "📋 Создать задачу")
    
    # Обработчики состояний FSM
    dp.message.register(process_task_title, TaskStates.waiting_for_title)
    dp.message.register(process_task_description, TaskStates.waiting_for_description)
    dp.message.register(process_company_selection, TaskStates.waiting_for_company)
    dp.message.register(process_initiator_name, TaskStates.waiting_for_initiator_name)
    dp.message.register(process_initiator_phone, TaskStates.waiting_for_initiator_phone)
    dp.message.register(process_assignee_selection, TaskStates.waiting_for_assignee)
    dp.message.register(process_priority_selection, TaskStates.waiting_for_priority)
    dp.message.register(process_deadline_selection, TaskStates.waiting_for_deadline)
    dp.message.register(process_custom_date, TaskStates.waiting_for_custom_date)
    dp.callback_query.register(process_calendar_callback, F.data.startswith("cal_"))

@smart_clear_chat
async def process_assignee_selection(message: Message, state: FSMContext):
    """Обработчик выбора исполнителя"""
    try:
        logger.info(f"Выбор исполнителя от пользователя {message.from_user.id}")
        
        # Получаем список исполнителей
        assignees = await UserManager.get_assignees()
        selected_assignee = None
        
        # Ищем выбранного исполнителя по имени
        for assignee in assignees:
            name = f"{assignee['first_name'] or ''} {assignee['last_name'] or ''}".strip()
            if not name:
                name = assignee['username'] or f"ID: {assignee['telegram_id']}"
            
            if name == message.text:
                selected_assignee = assignee
                break
        
        if not selected_assignee:
            await message.answer(
                "❌ Исполнитель не найден! Выберите исполнителя из списка:",
                reply_markup=create_assignee_keyboard(assignees)
            )
            return
        
        # Сохраняем выбранного исполнителя
        await state.update_data(
            assignee_id=selected_assignee['user_id'],
            assignee_name=f"{selected_assignee['first_name'] or ''} {selected_assignee['last_name'] or ''}".strip() or selected_assignee['username']
        )
        
        # Переходим к выбору приоритета
        await state.set_state(TaskStates.waiting_for_priority)
        
        await message.answer(
            f"✅ Исполнитель: **{message.text}**\n\n"
            f"**Шаг 7/8:** Выберите приоритет задачи:",
            reply_markup=get_task_urgent_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_assignee_selection: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_priority_selection(message: Message, state: FSMContext):
    """Обработчик выбора приоритета"""
    try:
        logger.info(f"Выбор приоритета от пользователя {message.from_user.id}")
        
        if message.text == "🔥 Срочная":
            # Сохраняем срочную задачу
            await state.update_data(is_urgent=True)
            priority_text = "🔥 Срочная"
            
        elif message.text == "📝 Обычная":
            # Сохраняем обычную задачу
            await state.update_data(is_urgent=False)
            priority_text = "📝 Обычная"
            
        else:
            await message.answer(
                "❌ Выберите приоритет из предложенных:",
                reply_markup=get_task_urgent_keyboard()
            )
            return
        
        # Переходим к выбору дедлайна
        await state.set_state(TaskStates.waiting_for_deadline)
        
        await message.answer(
            f"✅ Приоритет: **{priority_text}**\n\n"
            f"**Шаг 8/8:** Выберите дедлайн задачи:",
            reply_markup=get_task_deadline_keyboard(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_priority_selection: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_deadline_selection(message: Message, state: FSMContext):
    """Обработчик выбора дедлайна"""
    try:
        logger.info(f"Выбор дедлайна от пользователя {message.from_user.id}")
        
        # Определяем дедлайн
        from datetime import datetime, timedelta
        from config import TIMEZONE_OFFSET
        from datetime import timezone
        
        tz = timezone(timedelta(hours=TIMEZONE_OFFSET))
        now = datetime.now(tz)
        deadline = None
        
        if message.text == "📅 Сегодня":
            deadline = now.replace(hour=23, minute=59, second=59)
        elif message.text == "📅 Завтра":
            deadline = (now + timedelta(days=1)).replace(hour=23, minute=59, second=59)
        elif message.text == "📅 Через 3 дня":
            deadline = (now + timedelta(days=3)).replace(hour=23, minute=59, second=59)
        elif message.text == "📅 Выбрать дату":
            # Показываем календарь
            await message.answer(
                "📅 Выберите дату дедлайна:",
                reply_markup=create_calendar_keyboard(now.year, now.month)
            )
            return
        else:
            await message.answer(
                "❌ Выберите дедлайн из предложенных:",
                reply_markup=get_task_deadline_keyboard()
            )
            return
        
        # Создаем задачу в БД
        await create_final_task(message, state, deadline)
        
    except Exception as e:
        logger.error(f"Ошибка в process_deadline_selection: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def process_custom_date(message: Message, state: FSMContext):
    """Обработчик ввода пользовательской даты"""
    try:
        logger.info(f"Ввод пользовательской даты от пользователя {message.from_user.id}")
        
        from datetime import datetime, timedelta
        from config import TIMEZONE_OFFSET
        from datetime import timezone
        import re
        
        tz = timezone(timedelta(hours=TIMEZONE_OFFSET))
        user_input = message.text.strip()
        deadline = None
        
        # Парсим "через N дней"
        days_match = re.match(r'через\s+(\d+)\s+д(?:ней|ня|ень)', user_input.lower())
        if days_match:
            days = int(days_match.group(1))
            deadline = (datetime.now(tz) + timedelta(days=days)).replace(hour=23, minute=59, second=59)
        
        # Парсим формат ДД.ММ.ГГГГ
        elif re.match(r'\d{2}\.\d{2}\.\d{4}', user_input):
            try:
                deadline = datetime.strptime(user_input + " 23:59:59", "%d.%m.%Y %H:%M:%S")
                deadline = deadline.replace(tzinfo=tz)
            except ValueError:
                pass
        
        # Парсим формат ДД.ММ (текущий год)
        elif re.match(r'\d{2}\.\d{2}', user_input):
            try:
                current_year = datetime.now().year
                deadline = datetime.strptime(f"{user_input}.{current_year} 23:59:59", "%d.%m.%Y %H:%M:%S")
                deadline = deadline.replace(tzinfo=tz)
            except ValueError:
                pass
        
        if not deadline:
            await message.answer(
                "❌ Неверный формат даты!\n\n"
                "Введите дату в одном из форматов:\n"
                "• ДД.ММ.ГГГГ (например: 20.07.2025)\n"
                "• ДД.ММ (например: 20.07) - текущий год\n"
                "• через N дней (например: через 5 дней)",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Проверяем что дата не в прошлом
        if deadline < datetime.now(tz):
            await message.answer(
                "❌ Дедлайн не может быть в прошлом!\n\n"
                "Введите корректную дату:",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Создаем задачу в БД
        await create_final_task(message, state, deadline)
        
    except Exception as e:
        logger.error(f"Ошибка в process_custom_date: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

@smart_clear_chat
async def create_final_task(message: Message, state: FSMContext, deadline: datetime):
    """Финальное создание задачи в БД"""
    try:
        logger.info(f"Создание финальной задачи от пользователя {message.from_user.id}")
        
        # Получаем роль пользователя для клавиатуры СРАЗУ
        telegram_id = message.from_user.id
        user = await UserManager.get_user_by_telegram_id(telegram_id)
        role = user['role'] if user else 'admin'
        
        # Получаем все данные из состояния
        data = await state.get_data()
        
        # Создаем задачу
        task_id = await TaskManager.create_task(
            title=data['task_title'],
            description=data['task_description'],
            company_id=data['company_id'],
            initiator_name=data['initiator_name'],
            initiator_phone=data['initiator_phone'],
            assignee_id=data['assignee_id'],
            created_by=data['created_by'],
            is_urgent=data.get('is_urgent', False),
            deadline=deadline
        )
        
        # Очищаем состояние
        await state.clear()
        
        if task_id:
            # Сохраняем файлы если есть
            uploaded_files = []
            task_files = data.get('task_files', [])
            
            if task_files:
                for file_info in task_files:
                    try:
                        # Сохраняем файл
                        save_result = await file_storage.save_file(
                            file_data=file_info['file_data'],
                            file_name=file_info['file_name'],
                            content_type=file_info['content_type'],
                            task_id=task_id
                        )
                        
                        if save_result:
                            # Сохраняем информацию о файле в БД
                            from database.models import FileManager
                            if await FileManager.save_file_info(
                                task_id=task_id,
                                user_id=data['created_by'],
                                file_name=save_result['original_name'],
                                file_path=save_result['file_path'],
                                file_size=save_result['size'],
                                content_type=save_result['content_type'],
                                thumbnail_path=save_result['thumbnail_path']
                            ):
                                uploaded_files.append(save_result['original_name'])
                                logger.info(f"Файл {file_info['file_name']} успешно сохранен")
                            else:
                                logger.error(f"Ошибка сохранения файла {file_info['file_name']} в БД")
                        else:
                            logger.error(f"Ошибка сохранения файла {file_info['file_name']}")
                            
                    except Exception as e:
                        logger.error(f"Ошибка обработки файла: {e}")
            
            # Формируем сообщение об успехе (убираем Markdown чтобы избежать ошибок парсинга)
            success_text = "✅ Задача успешно создана!\n\n"
            success_text += f"📋 Название: {data['task_title']}\n"
            success_text += f"🏢 Компания: {data['company_name']}\n"
            success_text += f"👤 Исполнитель: {data['assignee_name']}\n"
            
            is_urgent = data.get('is_urgent', False)
            if is_urgent:
                success_text += f"⚡ Приоритет: 🔥 Срочная\n"
            else:
                success_text += f"⚡ Приоритет: 📝 Обычная\n"
            
            success_text += f"📅 Дедлайн: {deadline.strftime('%d.%m.%Y %H:%M')}\n"
            success_text += f"📞 Инициатор: {data['initiator_name']} ({data['initiator_phone']})\n"
            success_text += f"🆔 ID задачи: {task_id}"

            if uploaded_files:
                success_text += f"\n📎 Файлы: {', '.join(uploaded_files)}"
            
            await message.answer(
                success_text,
                reply_markup=get_main_keyboard(role)
            )
            
            # Уведомляем исполнителя о новой задаче
            try:
                assignee_telegram_id = None
                assignees = await UserManager.get_assignees()
                for assignee in assignees:
                    if assignee['user_id'] == data['assignee_id']:
                        assignee_telegram_id = assignee['telegram_id']
                        break
                
                if assignee_telegram_id and assignee_telegram_id != telegram_id:
                    from main import bot
                    priority_text = "🔥 Срочная" if is_urgent else "📝 Обычная"
                    notification_text = f"📋 Вам назначена новая задача!\n\n"
                    notification_text += f"Название: {data['task_title']}\n"
                    notification_text += f"Компания: {data['company_name']}\n"
                    notification_text += f"Приоритет: {priority_text}\n"
                    notification_text += f"Дедлайн: {deadline.strftime('%d.%m.%Y %H:%M')}\n"
                    notification_text += f"Инициатор: {data['initiator_name']}"
                    
                    await bot.send_message(assignee_telegram_id, notification_text)
                    logger.info(f"Уведомление о новой задаче отправлено пользователю {assignee_telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления: {e}")
            
        else:
            await message.answer(
                "❌ Ошибка создания задачи. Попробуйте позже.",
                reply_markup=get_main_keyboard(role)
            )
        
    except Exception as e:
        logger.error(f"Ошибка в create_final_task: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

def create_calendar_keyboard(year: int, month: int):
    """Создает календарь для выбора даты"""
    keyboard = []
    
    # Заголовок с названием месяца
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    header = f"{month_names[month-1]} {year}"
    keyboard.append([InlineKeyboardButton(text=header, callback_data="ignore")])
    
    # Дни недели
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days])
    
    # Получаем календарь месяца
    cal = calendar.monthcalendar(year, month)
    
    for week in cal:
        week_buttons = []
        for day in week:
            if day == 0:
                week_buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                # Проверяем, не в прошлом ли дата
                from datetime import datetime
                date_obj = datetime(year, month, day)
                if date_obj.date() < datetime.now().date():
                    week_buttons.append(InlineKeyboardButton(text=str(day), callback_data="ignore"))
                else:
                    callback_data = f"cal_{year}_{month}_{day}"
                    week_buttons.append(InlineKeyboardButton(text=str(day), callback_data=callback_data))
        keyboard.append(week_buttons)
    
    # Навигация
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    navigation = []
    navigation.append(InlineKeyboardButton(text="◀ Пред", callback_data=f"cal_nav_{prev_year}_{prev_month}"))
    navigation.append(InlineKeyboardButton(text="Сегодня", callback_data="cal_today"))
    navigation.append(InlineKeyboardButton(text="След ▶", callback_data=f"cal_nav_{next_year}_{next_month}"))
    keyboard.append(navigation)
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cal_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@smart_clear_chat
async def process_calendar_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатий на календарь"""
    try:
        data = callback.data
        
        if data == "ignore":
            await callback.answer()
            return
        
        elif data == "cal_back":
            await callback.message.edit_text(
                "❌ Выбор даты отменен.\n\n"
                "Выберите дедлайн задачи:"
            )
            await callback.message.answer(
                "Выберите дедлайн задачи:",
                reply_markup=get_task_deadline_keyboard()
            )
            await callback.answer()
            return
        
        elif data == "cal_today":
            from datetime import datetime, timedelta
            from config import TIMEZONE_OFFSET
            from datetime import timezone
            
            tz = timezone(timedelta(hours=TIMEZONE_OFFSET))
            deadline = datetime.now(tz).replace(hour=23, minute=59, second=59)
            
            await callback.message.edit_text(
                f"✅ Выбрана дата: {deadline.strftime('%d.%m.%Y')}"
            )
            await create_final_task_from_callback(callback, state, deadline)
            return
        
        elif data.startswith("cal_nav_"):
            # Навигация по месяцам
            _, _, year, month = data.split("_")
            year, month = int(year), int(month)
            
            await callback.message.edit_text(
                "📅 Выберите дату дедлайна:",
                reply_markup=create_calendar_keyboard(year, month)
            )
            await callback.answer()
            return
        
        elif data.startswith("cal_"):
            # Выбор конкретной даты
            _, year, month, day = data.split("_")
            year, month, day = int(year), int(month), int(day)
            
            from datetime import datetime, timedelta
            from config import TIMEZONE_OFFSET
            from datetime import timezone
            
            tz = timezone(timedelta(hours=TIMEZONE_OFFSET))
            deadline = datetime(year, month, day, 23, 59, 59, tzinfo=tz)
            
            await callback.message.edit_text(
                f"✅ Выбрана дата: {deadline.strftime('%d.%m.%Y')}"
            )
            await create_final_task_from_callback(callback, state, deadline)
            return
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в process_calendar_callback: {e}")
        await callback.answer("Произошла ошибка")


async def create_final_task_from_callback(callback: CallbackQuery, state: FSMContext, deadline: datetime):
    """Создание задачи из callback календаря"""
    try:
        # Используем тот же код что и в create_final_task, но с callback
        message = callback.message
        await create_final_task(message, state, deadline)
        
    except Exception as e:
        logger.error(f"Ошибка в create_final_task_from_callback: {e}")
        await callback.answer("Произошла ошибка")