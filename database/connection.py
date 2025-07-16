import asyncpg
import asyncio
from typing import Optional, Any, List, Dict
import logging
from config import DB_CONFIG

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self) -> bool:
        """Создание пула соединений с PostgreSQL"""
        try:
            self.pool = await asyncpg.create_pool(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                min_size=2,
                max_size=10,
                command_timeout=60,
                server_settings={
                    'application_name': 'taskbot',
                }
            )
            
            # Проверяем подключение
            async with self.pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            logger.info("Подключение к PostgreSQL установлено")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            return False
    
    async def execute_query(self, query: str, *args) -> List[asyncpg.Record]:
        """Выполнение SELECT запроса"""
        if not self.pool:
            raise Exception("Нет подключения к базе данных")
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetch(query, *args)
                return result
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            logger.error(f"Запрос: {query}")
            raise e
    
    async def execute_one(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Выполнение SELECT запроса с получением одной записи"""
        if not self.pool:
            raise Exception("Нет подключения к базе данных")
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchrow(query, *args)
                return result
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            logger.error(f"Запрос: {query}")
            raise e
    
    async def execute_command(self, query: str, *args) -> str:
        """Выполнение INSERT/UPDATE/DELETE запроса"""
        if not self.pool:
            raise Exception("Нет подключения к базе данных")
        
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *args)
                return result
        except Exception as e:
            logger.error(f"Ошибка выполнения команды: {e}")
            logger.error(f"Запрос: {query}")
            raise e
    
    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """Выполнение нескольких запросов в транзакции"""
        if not self.pool:
            raise Exception("Нет подключения к базе данных")
        
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for query, args in queries:
                        await conn.execute(query, *args)
            return True
        except Exception as e:
            logger.error(f"Ошибка выполнения транзакции: {e}")
            return False
    
    async def close(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()
            logger.info("Соединения с PostgreSQL закрыты")

# Глобальный экземпляр подключения
db_connection = DatabaseConnection()