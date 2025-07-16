from aiogram.fsm.state import State, StatesGroup

class CompanyStates(StatesGroup):
    """Состояния для создания компании"""
    waiting_for_name = State()
    waiting_for_description = State()

class TaskStates(StatesGroup):
    """Состояния для создания задачи"""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_company = State()
    waiting_for_initiator_name = State()
    waiting_for_initiator_phone = State()
    waiting_for_assignee = State()
    waiting_for_priority = State()
    waiting_for_deadline = State()
    waiting_for_custom_date = State()

class RoleStates(StatesGroup):
    """Состояния для изменения ролей"""
    waiting_for_user_selection = State()
    waiting_for_role_selection = State()

class CommentStates(StatesGroup):
    """Состояния для добавления комментариев"""
    waiting_for_task_selection = State()
    waiting_for_comment_text = State()