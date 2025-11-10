# app/core/database.py
import aiosqlite
import logging
from typing import Dict, Any, List
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


async def init_db(db_path: str = DATABASE_PATH):
    """
    Инициализирует базу данных, создавая таблицы ads и stat, если они не существуют.
    """
    logger.info(f"Инициализация базы данных: {db_path}")
    async with aiosqlite.connect(db_path) as db:
        # Создаём таблицу ads, если она не существует
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ads (
                ad_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                ratings_count INTEGER DEFAULT 0,
                processed INTEGER DEFAULT 0, -- 0: не требует, 1: требует, 2: обработано
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        # Индекс для ускорения поиска по статусу processed
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_ads_processed ON ads (processed);
        ''')
        # Индекс для ускорения поиска по seller_id
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_ads_seller_id ON ads (seller_id);
        ''')

        # Создаём таблицу stat для статистики по аккаунтам
        await db.execute('''
            CREATE TABLE IF NOT EXISTS stat (
                account_email TEXT PRIMARY KEY,
                processed INTEGER DEFAULT 0
            );
        ''')

        await db.commit()
        logger.info("База данных инициализирована.")


async def add_ad_if_new(ad_id: str, title: str, seller_id: str, ratings_count: int, db_path: str = DATABASE_PATH) -> bool:
    """
    Добавляет объявление в базу данных, если его ещё нет.
    Возвращает True, если объявление было добавлено как новое.
    Объявление не требует обработки (processed = 0), если seller_id уже существует в БД.
    """
    logger.debug(f"Проверка объявления {ad_id} на наличие в БД.")
    async with aiosqlite.connect(db_path) as db:
        # Проверяем, существует ли другой продавец с таким seller_id
        cursor = await db.execute("SELECT 1 FROM ads WHERE seller_id = ? AND ad_id != ?", (seller_id, ad_id))
        seller_exists = await cursor.fetchone()
        if seller_exists:
            logger.debug(f"Объявление {ad_id} от продавца {seller_id}, чьи объявления уже обрабатываются. Установлен processed = 0.")
            processed_status = 0  # Не требует обработки
        else:
            # Проверяем, подходит ли объявление под критерии (0 отзывов) и продавец новый
            if ratings_count == 0:
                processed_status = 1  # Требует обработки
            else:
                processed_status = 0  # Не требует обработки

        await db.execute('''
            INSERT INTO ads (ad_id, title, seller_id, ratings_count, processed)
            VALUES (?, ?, ?, ?, ?)
        ''', (ad_id, title, seller_id, ratings_count, processed_status))
        await db.commit()
        logger.debug(f"Объявление {ad_id} добавлено в БД с processed = {processed_status}.")
        return True


async def get_unprocessed_ads(limit: int = 10, db_path: str = DATABASE_PATH) -> List[Dict[str, Any]]:
    """
    Возвращает список объявлений, которые требуют обработки (processed = 1).
    Ограничивает количество возвращаемых записей.
    """
    logger.debug(f"Поиск необработанных объявлений (processed = 1), лимит: {limit}.")
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute('''
            SELECT ad_id, title, seller_id FROM ads WHERE processed = 1 LIMIT ?
        ''', (limit,))
        rows = await cursor.fetchall()
        ads = [{"ad_id": row[0], "title": row[1], "seller_id": row[2]} for row in rows]
        logger.debug(f"Найдено {len(ads)} необработанных объявлений.")
        return ads


async def mark_ad_as_processed(ad_id: str, db_path: str = DATABASE_PATH) -> bool:
    """
    Помечает объявление как обработанное (processed = 2).
    Возвращает True, если обновление прошло успешно.
    """
    logger.debug(f"Пометка объявления {ad_id} как обработанного (processed = 2).")
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute('''
            UPDATE ads SET processed = 2 WHERE ad_id = ?
        ''', (ad_id,))
        if cursor.rowcount == 0:
            logger.warning(f"Объявление {ad_id} не найдено в БД для обновления статуса.")
            return False
        await db.commit()
        return True


async def is_ad_exists(ad_id: str, db_path: str = DATABASE_PATH) -> bool:
    try:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute("SELECT 1 FROM ads WHERE ad_id = ?", (ad_id,))
            exists = await cursor.fetchone()
            return exists is not None
    except Exception as e:
        logger.error(f"Ошибка {e.__class__.__name__} при проверке объявления {ad_id} в базе: {e}")
        return False


async def increment_processed_counter(account_email: str, db_path: str = DATABASE_PATH) -> bool:
    """
    Увеличивает счётчик processed для указанного аккаунта.
    Создаёт запись для аккаунта, если её не существует.
    """
    logger.debug(f"Увеличение счётчика processed для аккаунта {account_email}.")
    async with aiosqlite.connect(db_path) as db:
        # Проверяем, существует ли уже запись для этого аккаунта
        cursor = await db.execute("SELECT processed FROM stat WHERE account_email = ?", (account_email,))
        row = await cursor.fetchone()

        if row is None:
            # Если записи нет, создаём новую с processed = 1
            await db.execute('''
                INSERT INTO stat (account_email, processed)
                VALUES (?, 1)
            ''', (account_email,))
            logger.debug(f"Создана новая запись для аккаунта {account_email} с processed = 1.")
        else:
            # Если запись есть, увеличиваем счётчик
            current_count = row[0]
            new_count = current_count + 1
            await db.execute('''
                UPDATE stat SET processed = ? WHERE account_email = ?
            ''', (new_count, account_email))
            logger.debug(f"Обновлён счётчик processed для аккаунта {account_email}: {current_count} -> {new_count}.")

        await db.commit()
        return True


async def get_processed_count(account_email: str, db_path: str = DATABASE_PATH) -> int:
    """
    Возвращает количество обработанных объявлений для указанного аккаунта.
    Возвращает 0, если аккаунт не найден.
    """
    logger.debug(f"Получение счётчика processed для аккаунта {account_email}.")
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT processed FROM stat WHERE account_email = ?", (account_email,))
        row = await cursor.fetchone()
        count = row[0] if row else 0
        logger.debug(f"Счётчик processed для аккаунта {account_email}: {count}.")
        return count


# # --- Пример использования (опционально, для тестирования) ---
# async def example():
#     await init_db()
#     await is_ad_exists("12345")
#
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(example())