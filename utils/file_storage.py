import os
import uuid
import aiofiles
import aiofiles.os
from datetime import datetime
from PIL import Image
import io
from typing import Optional, Dict, Any
import logging
from config import UPLOAD_PATH, MAX_FILE_SIZE

logger = logging.getLogger(__name__)

class FileStorage:
    def __init__(self):
        self.upload_path = UPLOAD_PATH
        self.max_file_size = MAX_FILE_SIZE
        
        # Создаем необходимые папки
        os.makedirs(self.upload_path, exist_ok=True)
        os.makedirs(f"{self.upload_path}/tasks", exist_ok=True)
    
    async def save_file(self, file_data: bytes, file_name: str, 
                       content_type: str, task_id: str = None) -> Optional[Dict[str, Any]]:
        """Сохранение файла на диск"""
        try:
            # Проверяем размер файла
            if not self.validate_file_size(len(file_data)):
                logger.error(f"Файл {file_name} превышает максимальный размер")
                return None
            
            # Генерируем уникальное имя файла
            file_id = str(uuid.uuid4())
            file_extension = os.path.splitext(file_name)[1].lower()
            
            # Создаем путь к файлу
            if task_id:
                task_dir = f"{self.upload_path}/tasks/{task_id}"
                await aiofiles.os.makedirs(task_dir, exist_ok=True)
                file_path = f"{task_dir}/{file_id}{file_extension}"
                relative_path = f"tasks/{task_id}/{file_id}{file_extension}"
            else:
                temp_dir = f"{self.upload_path}/temp"
                await aiofiles.os.makedirs(temp_dir, exist_ok=True)
                file_path = f"{temp_dir}/{file_id}{file_extension}"
                relative_path = f"temp/{file_id}{file_extension}"
            
            # Сохраняем файл
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_data)
            
            # Создаем превью для изображений
            thumbnail_path = None
            if self.is_image(content_type):
                thumbnail_path = await self.create_thumbnail(file_data, file_path)
            
            return {
                'file_id': file_id,
                'file_path': relative_path,
                'thumbnail_path': thumbnail_path,
                'original_name': file_name,
                'content_type': content_type,
                'size': len(file_data),
                'full_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Ошибка сохранения файла {file_name}: {e}")
            return None
    
    async def create_thumbnail(self, file_data: bytes, original_path: str) -> Optional[str]:
        """Создание превью для изображения"""
        try:
            # Открываем изображение
            image = Image.open(io.BytesIO(file_data))
            
            # Создаем превью (максимум 300x300)
            image.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Генерируем путь для превью
            path_parts = original_path.rsplit('.', 1)
            if len(path_parts) == 2:
                thumbnail_path = f"{path_parts[0]}_thumb.{path_parts[1]}"
            else:
                thumbnail_path = f"{original_path}_thumb.jpg"
            
            # Сохраняем превью
            if image.format in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                save_format = image.format
            else:
                save_format = 'JPEG'
            
            image.save(thumbnail_path, format=save_format, quality=85)
            
            # Возвращаем относительный путь
            relative_thumbnail = thumbnail_path.replace(f"{self.upload_path}/", "")
            return relative_thumbnail
            
        except Exception as e:
            logger.error(f"Ошибка создания превью: {e}")
            return None
    
    def get_file_path(self, relative_path: str) -> str:
        """Получение полного пути к файлу"""
        return os.path.join(self.upload_path, relative_path)
    
    async def delete_file(self, relative_path: str) -> bool:
        """Удаление файла с диска"""
        try:
            full_path = self.get_file_path(relative_path)
            if os.path.exists(full_path):
                await aiofiles.os.remove(full_path)
                
                # Удаляем превью если есть
                thumbnail_path = self.get_thumbnail_path(relative_path)
                if thumbnail_path and os.path.exists(self.get_file_path(thumbnail_path)):
                    await aiofiles.os.remove(self.get_file_path(thumbnail_path))
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Ошибка удаления файла {relative_path}: {e}")
            return False
    
    def get_thumbnail_path(self, relative_path: str) -> Optional[str]:
        """Получение пути к превью"""
        try:
            path_parts = relative_path.rsplit('.', 1)
            if len(path_parts) == 2:
                return f"{path_parts[0]}_thumb.{path_parts[1]}"
            return None
        except:
            return None
    
    async def read_file(self, relative_path: str) -> Optional[bytes]:
        """Чтение файла с диска"""
        try:
            full_path = self.get_file_path(relative_path)
            if os.path.exists(full_path):
                async with aiofiles.open(full_path, 'rb') as f:
                    return await f.read()
            return None
            
        except Exception as e:
            logger.error(f"Ошибка чтения файла {relative_path}: {e}")
            return None
    
    def is_image(self, content_type: str) -> bool:
        """Проверка, является ли файл изображением"""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
        return content_type.lower() in image_types
    
    def validate_file_size(self, file_size: int) -> bool:
        """Проверка размера файла"""
        return file_size <= self.max_file_size
    
    async def get_file_info(self, relative_path: str) -> Optional[Dict[str, Any]]:
        """Получение информации о файле"""
        try:
            full_path = self.get_file_path(relative_path)
            if os.path.exists(full_path):
                stat = await aiofiles.os.stat(full_path)
                return {
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'exists': True
                }
            return {'exists': False}
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о файле {relative_path}: {e}")
            return {'exists': False}
    
    def get_allowed_extensions(self) -> Dict[str, str]:
        """Получение разрешенных расширений файлов"""
        return {
            # Изображения
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png', '.gif': 'image/gif',
            '.webp': 'image/webp', '.bmp': 'image/bmp',
            
            # Документы
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            
            # Текстовые файлы
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            
            # Архивы
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed'
        }
    
    def validate_file_extension(self, file_name: str) -> bool:
        """Проверка расширения файла"""
        extension = os.path.splitext(file_name)[1].lower()
        return extension in self.get_allowed_extensions()
    
    def get_content_type_by_extension(self, file_name: str) -> str:
        """Определение content-type по расширению файла"""
        extension = os.path.splitext(file_name)[1].lower()
        allowed_extensions = self.get_allowed_extensions()
        return allowed_extensions.get(extension, 'application/octet-stream')

# Глобальный экземпляр для использования
file_storage = FileStorage()