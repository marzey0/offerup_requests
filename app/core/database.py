# app/core/database.py
import aiosqlite
import logging
from typing import Dict, Any, List
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


async def init_db(db_path: str = DATABASE_PATH):
    """
    Инициализирует базу данных, создавая таблицу ads, если она не существует.
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
        await db.commit()
        logger.info("База данных инициализирована.")


async def add_ad_if_new(db_path: str, ad_id: str, title: str, seller_id: str, ratings_count: int) -> bool:
    """
    Добавляет объявление в базу данных, если его ещё нет.
    Возвращает True, если объявление было добавлено как новое.
    """
    logger.debug(f"Проверка объявления {ad_id} на наличие в БД.")
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT 1 FROM ads WHERE ad_id = ?", (ad_id,))
        exists = await cursor.fetchone()
        if exists:
            logger.debug(f"Объявление {ad_id} уже существует в БД.")
            return False

        # Проверяем, подходит ли объявление под критерии (0 отзывов)
        if ratings_count == 0:
            processed_status = 1  # Требует обработки
            logger.info(f"Новое объявление {ad_id} от продавца {seller_id} подходит под фильтр (0 отзывов).")
        else:
            processed_status = 0  # Не требует обработки

        await db.execute('''
            INSERT INTO ads (ad_id, title, seller_id, ratings_count, processed)
            VALUES (?, ?, ?, ?, ?)
        ''', (ad_id, title, seller_id, ratings_count, processed_status))
        await db.commit()
        logger.debug(f"Объявление {ad_id} добавлено в БД с processed = {processed_status}.")
        return True


async def get_unprocessed_ads(db_path: str, limit: int = 10) -> List[Dict[str, Any]]:
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


async def mark_ad_as_processed(db_path: str, ad_id: str) -> bool:
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
        logger.info(f"Объявление {ad_id} помечено как обработанное.")
        return True


# --- Пример использования (опционально, для тестирования) ---
# async def example():
#     await init_db()
#     await add_ad_if_new("12345", "Тестовое объявление", "seller_123", 0, 0)
#     unprocessed = await get_unprocessed_ads(limit=5)
#     print(unprocessed)
#     await mark_ad_as_processed("12345")

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(example())