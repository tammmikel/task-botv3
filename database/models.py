import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from .connection import db_connection
import logging

logger = logging.getLogger(__name__)

# Часовой пояс UTC+5
TIMEZONE = timezone(timedelta(hours=5))

def generate_uuid() -> str:
    """Генерация UUID строки"""
    return str(uuid.uuid4())

def get_current_time() -> datetime:
    """Получение текущего времени в UTC+5"""
    return datetime.now(TIMEZONE)

def format_datetime(dt: datetime) -> str:
    """Форматирование datetime для отображения"""
    if not dt:
        return 'Нет данных'
    
    try:
        # Если datetime без timezone, добавляем UTC+5
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TIMEZONE)
        
        return dt.strftime('%d.%m.%Y %H:%M')
    except Exception as e:
        logger.error(f"Ошибка форматирования даты {dt}: {e}")
        return 'Дата некорректна'

class DatabaseManager:
    
    @staticmethod
    async def create_tables():
        """Создание всех таблиц в базе данных"""
        
        # Таблица пользователей
        users_table = """
        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            telegram_id BIGINT UNIQUE NOT NULL,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            role VARCHAR(50) NOT NULL DEFAULT 'admin',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
        """
        
        # Таблица компаний
        companies_table = """
        CREATE TABLE IF NOT EXISTS companies (
            company_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_by UUID NOT NULL REFERENCES users(user_id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_companies_created_by ON companies(created_by);
        """
        
        # Таблица задач
        tasks_table = """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(500) NOT NULL,
            description TEXT,
            company_id UUID NOT NULL REFERENCES companies(company_id),
            initiator_name VARCHAR(255) NOT NULL,
            initiator_phone VARCHAR(50) NOT NULL,
            assignee_id UUID NOT NULL REFERENCES users(user_id),
            created_by UUID NOT NULL REFERENCES users(user_id),
            is_urgent BOOLEAN DEFAULT FALSE,
            status VARCHAR(50) DEFAULT 'new',
            deadline TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_tasks_assignee_id ON tasks(assignee_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_company_id ON tasks(company_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
        CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline);
        CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
        """
        
        # Таблица комментариев
        comments_table = """
        CREATE TABLE IF NOT EXISTS task_comments (
            comment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(user_id),
            comment_text TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_comments_task_id ON task_comments(task_id);
        CREATE INDEX IF NOT EXISTS idx_comments_user_id ON task_comments(user_id);
        """
        
        # Таблица файлов
        files_table = """
        CREATE TABLE IF NOT EXISTS task_files (
            file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(user_id),
            file_name VARCHAR(500) NOT NULL,
            file_path VARCHAR(1000) NOT NULL,
            file_size BIGINT NOT NULL,
            content_type VARCHAR(255) NOT NULL,
            thumbnail_path VARCHAR(1000),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_files_task_id ON task_files(task_id);
        CREATE INDEX IF NOT EXISTS idx_files_user_id ON task_files(user_id);
        """
        
        tables = [
            ("users", users_table),
            ("companies", companies_table), 
            ("tasks", tasks_table),
            ("task_comments", comments_table),
            ("task_files", files_table)
        ]
        
        for table_name, table_sql in tables:
            try:
                await db_connection.execute_command(table_sql)
                logger.info(f"Таблица {table_name} создана/проверена")
            except Exception as e:
                logger.error(f"Ошибка создания таблицы {table_name}: {e}")
                raise e

class UserManager:
    
    @staticmethod
    async def create_user(telegram_id: int, username: str = None, 
                         first_name: str = None, last_name: str = None, 
                         role: str = 'admin') -> Optional[str]:
        """Создание нового пользователя"""
        try:
            query = """
            INSERT INTO users (telegram_id, username, first_name, last_name, role)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING user_id
            """
            
            result = await db_connection.execute_one(
                query, telegram_id, username, first_name, last_name, role
            )
            
            if result:
                return str(result['user_id'])
            return None
            
        except Exception as e:
            logger.error(f"Ошибка создания пользователя: {e}")
            return None
    
    @staticmethod
    async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по telegram_id"""
        try:
            query = """
            SELECT user_id, telegram_id, username, first_name, last_name, role, created_at
            FROM users 
            WHERE telegram_id = $1
            """
            
            result = await db_connection.execute_one(query, telegram_id)
            
            if result:
                return {
                    'user_id': str(result['user_id']),
                    'telegram_id': result['telegram_id'],
                    'username': result['username'],
                    'first_name': result['first_name'],
                    'last_name': result['last_name'],
                    'role': result['role'],
                    'created_at': result['created_at']
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
    
    @staticmethod
    async def get_users_count() -> int:
        """Получение общего количества пользователей"""
        try:
            query = "SELECT COUNT(*) as count FROM users"
            result = await db_connection.execute_one(query)
            return result['count'] if result else 0
            
        except Exception as e:
            logger.error(f"Ошибка получения количества пользователей: {e}")
            return 0
    
    @staticmethod
    async def update_user_role(user_id: str, new_role: str) -> bool:
        """Изменение роли пользователя"""
        try:
            query = "UPDATE users SET role = $1 WHERE user_id = $2"
            await db_connection.execute_command(query, new_role, user_id)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка изменения роли пользователя: {e}")
            return False
    
    @staticmethod
    async def get_assignees() -> List[Dict[str, Any]]:
        """Получение списка исполнителей"""
        try:
            query = """
            SELECT user_id, telegram_id, username, first_name, last_name, role
            FROM users
            WHERE role IN ('director', 'manager', 'main_admin', 'admin')
            ORDER BY first_name, last_name
            """
            
            results = await db_connection.execute_query(query)
            assignees = []
            
            for row in results:
                assignees.append({
                    'user_id': str(row['user_id']),
                    'telegram_id': row['telegram_id'],
                    'username': row['username'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'role': row['role']
                })
            
            return assignees
            
        except Exception as e:
            logger.error(f"Ошибка получения исполнителей: {e}")
            return []

class CompanyManager:
    
    @staticmethod
    async def create_company(name: str, description: str = None, 
                           created_by: str = None) -> Optional[str]:
        """Создание новой компании"""
        try:
            query = """
            INSERT INTO companies (name, description, created_by)
            VALUES ($1, $2, $3)
            RETURNING company_id
            """
            
            result = await db_connection.execute_one(
                query, name, description, created_by
            )
            
            if result:
                return str(result['company_id'])
            return None
            
        except Exception as e:
            logger.error(f"Ошибка создания компании: {e}")
            return None
    
    @staticmethod
    async def get_all_companies() -> List[Dict[str, Any]]:
        """Получение всех компаний"""
        try:
            query = """
            SELECT company_id, name, description, created_by, created_at
            FROM companies
            ORDER BY created_at DESC
            """
            
            results = await db_connection.execute_query(query)
            companies = []
            
            for row in results:
                companies.append({
                    'company_id': str(row['company_id']),
                    'name': row['name'],
                    'description': row['description'],
                    'created_by': str(row['created_by']),
                    'created_at': row['created_at']
                })
            
            return companies
            
        except Exception as e:
            logger.error(f"Ошибка получения компаний: {e}")
            return []
    
    @staticmethod
    async def get_company_by_id(company_id: str) -> Optional[Dict[str, Any]]:
        """Получение компании по ID"""
        try:
            query = """
            SELECT company_id, name, description, created_by, created_at
            FROM companies
            WHERE company_id = $1
            """
            
            result = await db_connection.execute_one(query, company_id)
            
            if result:
                return {
                    'company_id': str(result['company_id']),
                    'name': result['name'],
                    'description': result['description'],
                    'created_by': str(result['created_by']),
                    'created_at': result['created_at']
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения компании: {e}")
            return None

class TaskManager:
    
    @staticmethod
    async def create_task(title: str, description: str, company_id: str,
                         initiator_name: str, initiator_phone: str,
                         assignee_id: str, created_by: str, is_urgent: bool,
                         deadline: datetime) -> Optional[str]:
        """Создание новой задачи"""
        try:
            query = """
            INSERT INTO tasks (title, description, company_id, initiator_name,
                              initiator_phone, assignee_id, created_by, is_urgent,
                              deadline)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING task_id
            """
            
            result = await db_connection.execute_one(
                query, title, description, company_id, initiator_name,
                initiator_phone, assignee_id, created_by, is_urgent, deadline
            )
            
            if result:
                return str(result['task_id'])
            return None
            
        except Exception as e:
            logger.error(f"Ошибка создания задачи: {e}")
            return None
    
    @staticmethod
    async def get_user_tasks(user_id: str, role: str) -> List[Dict[str, Any]]:
        """Получение задач пользователя в зависимости от роли"""
        try:
            if role in ['director', 'manager']:
                # Директор и менеджер видят все задачи
                query = """
                SELECT t.task_id, t.title, t.description, t.is_urgent, t.status, 
                       t.deadline, t.created_at, c.name as company_name
                FROM tasks t
                INNER JOIN companies c ON t.company_id = c.company_id
                ORDER BY t.created_at DESC
                """
                results = await db_connection.execute_query(query)
            else:
                # Админы видят только свои задачи
                query = """
                SELECT t.task_id, t.title, t.description, t.is_urgent, t.status,
                       t.deadline, t.created_at, c.name as company_name
                FROM tasks t
                INNER JOIN companies c ON t.company_id = c.company_id
                WHERE t.assignee_id = $1
                ORDER BY t.created_at DESC
                """
                results = await db_connection.execute_query(query, user_id)
            
            tasks = []
            status_emoji = {
                'new': '🆕',
                'in_progress': '⏳',
                'completed': '✅',
                'overdue': '⚠️',
                'cancelled': '❌'
            }
            
            for row in results:
                deadline_str = format_datetime(row['deadline'])
                deadline_short = row['deadline'].strftime('%d.%m') if row['deadline'] else 'Нет'
                
                tasks.append({
                    'task_id': str(row['task_id']),
                    'title': row['title'],
                    'description': row['description'],
                    'is_urgent': row['is_urgent'],
                    'status': row['status'],
                    'deadline_str': deadline_str,
                    'deadline_short': deadline_short,
                    'created_at': row['created_at'],
                    'company_name': row['company_name'],
                    'status_emoji': status_emoji.get(row['status'], '❓')
                })
            
            return tasks
            
        except Exception as e:
            logger.error(f"Ошибка получения задач: {e}")
            return []
    
    @staticmethod
    async def get_companies_with_tasks(user_id: str, role: str) -> List[Dict[str, Any]]:
        """Получение компаний с количеством задач"""
        try:
            if role in ['director', 'manager']:
                query = """
                SELECT c.company_id, c.name, COUNT(t.task_id) as task_count
                FROM companies c
                LEFT JOIN tasks t ON c.company_id = t.company_id
                GROUP BY c.company_id, c.name
                HAVING COUNT(t.task_id) > 0
                ORDER BY c.name
                """
                results = await db_connection.execute_query(query)
            else:
                query = """
                SELECT c.company_id, c.name, COUNT(t.task_id) as task_count
                FROM companies c
                LEFT JOIN tasks t ON c.company_id = t.company_id
                WHERE t.assignee_id = $1
                GROUP BY c.company_id, c.name
                HAVING COUNT(t.task_id) > 0
                ORDER BY c.name
                """
                results = await db_connection.execute_query(query, user_id)
            
            companies = []
            for row in results:
                companies.append({
                    'company_id': str(row['company_id']),
                    'name': row['name'],
                    'task_count': row['task_count']
                })
            
            return companies
            
        except Exception as e:
            logger.error(f"Ошибка получения компаний: {e}")
            return []
    
    @staticmethod
    async def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
        """Получение подробной информации о задаче"""
        try:
            query = """
            SELECT t.task_id, t.title, t.description, t.is_urgent, t.status,
                   t.deadline, t.created_at, c.name as company_name,
                   t.initiator_name, t.initiator_phone, t.assignee_id
            FROM tasks t
            INNER JOIN companies c ON t.company_id = c.company_id
            WHERE t.task_id = $1
            """
            
            result = await db_connection.execute_one(query, task_id)
            
            if result:
                # Добавляем эмодзи статуса
                status_emoji = {
                    'new': '🆕',
                    'in_progress': '⏳',
                    'completed': '✅',
                    'overdue': '⚠️',
                    'cancelled': '❌'
                }
                
                return {
                    'task_id': str(result['task_id']),
                    'title': result['title'],
                    'description': result['description'],
                    'is_urgent': result['is_urgent'],
                    'status': result['status'],
                    'status_emoji': status_emoji.get(result['status'], '❓'),
                    'deadline_str': format_datetime(result['deadline']),
                    'created_at': result['created_at'],
                    'company_name': result['company_name'],
                    'initiator_name': result['initiator_name'],
                    'initiator_phone': result['initiator_phone'],
                    'assignee_id': str(result['assignee_id'])
                }
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения задачи: {e}")
            return None
    
    @staticmethod
    async def update_task_status(task_id: str, new_status: str) -> bool:
        """Изменение статуса задачи"""
        try:
            query = """
            UPDATE tasks 
            SET status = $1, updated_at = NOW()
            WHERE task_id = $2
            """
            
            await db_connection.execute_command(query, new_status, task_id)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка изменения статуса задачи: {e}")
            return False

class FileManager:
    
    @staticmethod
    async def save_file_info(task_id: str, user_id: str, file_name: str,
                           file_path: str, file_size: int, content_type: str,
                           thumbnail_path: str = None) -> bool:
        """Сохранение информации о файле в БД"""
        try:
            query = """
            INSERT INTO task_files (task_id, user_id, file_name, file_path,
                                  file_size, content_type, thumbnail_path)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            await db_connection.execute_command(
                query, task_id, user_id, file_name, file_path,
                file_size, content_type, thumbnail_path
            )
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            return False
    
    @staticmethod
    async def get_task_files(task_id: str) -> List[Dict[str, Any]]:
        """Получение всех файлов задачи"""
        try:
            query = """
            SELECT f.file_id, f.file_name, f.file_path, f.file_size,
                   f.content_type, f.thumbnail_path, f.created_at,
                   u.first_name, u.last_name, u.username
            FROM task_files f
            JOIN users u ON f.user_id = u.user_id
            WHERE f.task_id = $1
            ORDER BY f.created_at DESC
            """
            
            results = await db_connection.execute_query(query, task_id)
            files = []
            
            for row in results:
                uploader_name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip()
                if not uploader_name:
                    uploader_name = row['username'] or "Неизвестный"
                
                files.append({
                    'file_id': str(row['file_id']),
                    'file_name': row['file_name'],
                    'file_path': row['file_path'],
                    'file_size': row['file_size'],
                    'content_type': row['content_type'],
                    'thumbnail_path': row['thumbnail_path'],
                    'created_at': row['created_at'],
                    'uploader_name': uploader_name
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Ошибка получения файлов: {e}")
            return []