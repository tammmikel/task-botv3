from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(role: str):
    """Главная клавиатура в зависимости от роли пользователя"""
    
    if role == 'director':
        buttons = [
            [KeyboardButton(text="📋 Создать задачу"), KeyboardButton(text="🏢 Управление компаниями")],
            [KeyboardButton(text="👥 Управление сотрудниками"), KeyboardButton(text="📊 Аналитика")],
            [KeyboardButton(text="📝 Мои задачи"), KeyboardButton(text="💬 Комментарии")]
        ]
    
    elif role == 'manager':
        buttons = [
            [KeyboardButton(text="📋 Создать задачу"), KeyboardButton(text="🏢 Управление компаниями")],
            [KeyboardButton(text="📝 Мои задачи"), KeyboardButton(text="💬 Комментарии")]
        ]
    
    elif role == 'main_admin':
        buttons = [
            [KeyboardButton(text="📝 Мои задачи"), KeyboardButton(text="💬 Комментарии")],
            [KeyboardButton(text="⚙️ Админ панель")]
        ]
    
    else:  # admin
        buttons = [
            [KeyboardButton(text="📝 Мои задачи"), KeyboardButton(text="💬 Комментарии")]
        ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_company_management_keyboard():
    """Клавиатура для управления компаниями"""
    buttons = [
        [KeyboardButton(text="➕ Добавить компанию"), KeyboardButton(text="📋 Список компаний")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_staff_management_keyboard():
    """Клавиатура для управления сотрудниками (только для директора)"""
    buttons = [
        [KeyboardButton(text="👤 Изменить роль сотрудника"), KeyboardButton(text="📋 Список сотрудников")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_task_urgent_keyboard():
    """Клавиатура для выбора срочности задачи"""
    buttons = [
        [KeyboardButton(text="🔥 Срочная"), KeyboardButton(text="📝 Обычная")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_task_deadline_keyboard():
    """Клавиатура для выбора дедлайна задачи"""
    buttons = [
        [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="📅 Завтра")],
        [KeyboardButton(text="📅 Через 3 дня"), KeyboardButton(text="📅 Выбрать дату")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_task_status_keyboard(current_status: str, user_role: str):
    """Клавиатура для изменения статуса задачи"""
    buttons = []
    
    # Исполнитель может менять статус
    if current_status == 'new':
        buttons.append([KeyboardButton(text="⏳ Взять в работу")])
    elif current_status == 'in_progress':
        buttons.append([KeyboardButton(text="✅ Завершить")])
        buttons.append([KeyboardButton(text="🆕 Вернуть в новые")])
    
    # Директор и менеджер могут менять с "Выполнено" обратно в работу
    if user_role in ['director', 'manager'] and current_status == 'completed':
        buttons.append([KeyboardButton(text="⏳ Вернуть в работу")])
    
    # Директор и менеджер могут отменять задачи
    if user_role in ['director', 'manager'] and current_status != 'cancelled':
        buttons.append([KeyboardButton(text="❌ Отменить задачу")])
    
    buttons.append([KeyboardButton(text="🔙 Назад")])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_analytics_keyboard():
    """Клавиатура для аналитики (только для директора)"""
    buttons = [
        [KeyboardButton(text="📊 За день"), KeyboardButton(text="📊 За неделю")],
        [KeyboardButton(text="📊 За месяц"), KeyboardButton(text="📈 Графики")],
        [KeyboardButton(text="⏱️ Время выполнения"), KeyboardButton(text="👥 По исполнителям")],
        [KeyboardButton(text="🏢 По компаниям"), KeyboardButton(text="🔙 Назад")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_role_selection_keyboard():
    """Клавиатура для выбора роли (только для директора)"""
    buttons = [
        [KeyboardButton(text="👔 Менеджер"), KeyboardButton(text="⚙️ Главный админ")],
        [KeyboardButton(text="🔧 Системный админ"), KeyboardButton(text="🔙 Назад")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_back_keyboard():
    """Простая клавиатура с кнопкой назад"""
    buttons = [
        [KeyboardButton(text="🔙 Назад")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_skip_keyboard():
    """Клавиатура с кнопками 'Пропустить' и 'Назад'"""
    buttons = [
        [KeyboardButton(text="⏭️ Пропустить")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_task_status_keyboard(current_status: str, user_role: str):
    """Клавиатура для изменения статуса задачи"""
    buttons = []
    
    # Исполнитель может менять статус
    if current_status == 'new':
        buttons.append([KeyboardButton(text="⏳ Взять в работу")])
    elif current_status == 'in_progress':
        buttons.append([KeyboardButton(text="✅ Завершить")])
        buttons.append([KeyboardButton(text="🆕 Вернуть в новые")])
    
    # Директор и менеджер могут менять с "Выполнено" обратно в работу
    if user_role in ['director', 'manager'] and current_status == 'completed':
        buttons.append([KeyboardButton(text="⏳ Вернуть в работу")])
    
    # Директор и менеджер могут отменять задачи
    if user_role in ['director', 'manager'] and current_status != 'cancelled':
        buttons.append([KeyboardButton(text="❌ Отменить задачу")])
    
    buttons.append([KeyboardButton(text="🔙 Назад")])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )