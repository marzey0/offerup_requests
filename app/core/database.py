# app/core/database.py
import json

import aiosqlite
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, UTC

from config import DATABASE_PATH, MAX_AD_AGE, MAX_RATINGS_COUNT

logger = logging.getLogger(__name__)


async def init_db():
    """
    Инициализирует базу данных, создавая таблицы ads и stat, если они не существуют.
    """
    logger.info(f"Инициализация базы данных: {DATABASE_PATH}")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Создаём таблицу ads, если она не существует
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ads (
                ad_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                ratings_count INTEGER NOT NULL,
                processed INTEGER DEFAULT 0, -- 0: не отписан, 1: отписан
                post_date TEXT,
                ad_details TEXT NOT NULL
            );
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


async def add_ad(ad: dict) -> bool:
    try:
        ad_id = ad["listingId"]
        title = ad["title"]
        seller_id = ad["owner"]["id"]
        ratings_count = ad["owner"]["profile"]["ratingSummary"]["count"]
        post_date = ad["postDate"]

        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('''
                INSERT OR IGNORE INTO ads (ad_id, title, seller_id, ratings_count, post_date, ad_details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ad_id, title, seller_id, ratings_count, post_date, json.dumps(ad)))
            await db.commit()

            # Проверяем, была ли вставка (изменено ли количество строк)
            if db.total_changes > 0:
                logger.debug(f"Добавлено объявление: {ad_id}")
                return True
            else:
                # logger.debug(f"Объявление уже существует: {ad_id}")
                return False

    except Exception as e:
        logger.error(f"Ошибка при добавлении объявления {ad_id}: {e}")
        return False


async def get_next_unprocessed_ad(max_age_minutes: int = MAX_AD_AGE) -> Optional[Dict[str, Any]]:
    """
    Получает следующее необработанное объявление, помечая его как обработанное.
    Каждый продавец может быть обработан только единожды.

    Args:
        max_age_minutes: Максимальный возраст объявления в минутах

    Returns:
        Optional[Dict]: Данные объявления или None если подходящих нет
    """
    try:
        # Вычисляем минимальную дату для фильтрации по возрасту
        min_date = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
        # Конвертируем в тот же формат, что и в базе
        min_date_str = min_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'

        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Начинаем транзакцию
            await db.execute("BEGIN TRANSACTION")

            # Ищем подходящее объявление (строковое сравнение работает для ISO формата)
            cursor = await db.execute('''
                SELECT ad_id, ad_details 
                FROM ads 
                WHERE processed = 0
                AND ratings_count = ?
                AND post_date >= ? 
                AND seller_id NOT IN (
                    SELECT DISTINCT seller_id 
                    FROM ads 
                    WHERE processed = 1
                )
                ORDER BY post_date DESC LIMIT 1
            ''', (min_date_str, MAX_RATINGS_COUNT))

            result = await cursor.fetchone()

            if result:
                # Помечаем найденное объявление как обработанное
                ad_id, ad_details = result
                await db.execute('''UPDATE ads SET processed = 1 WHERE ad_id = ?''', (ad_id,))
                await db.commit()
                return json.loads(ad_details)
            else:
                await db.commit()
                logger.debug("Необработанные объявления не найдены")
                return None

    except Exception as e:
        logger.error(f"Ошибка при поиске необработанного объявления: {e}")
        return None


async def update_ad_processed_status(ad_id: str, processed: int) -> bool:
    """
    Изменяет статус processed у объявления.

    Args:
        ad_id: ID объявления
        processed: Новый статус (0 - не обработан, 1 - обработан)

    Returns:
        bool: True если обновление успешно, False если ошибка
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute('''
                UPDATE ads 
                SET processed = ? 
                WHERE ad_id = ?
            ''', (processed, ad_id))
            await db.commit()

            if db.total_changes > 0:
                logger.info(f"Обновлен статус объявления {ad_id} на {processed}")
                return True
            else:
                logger.warning(f"Объявление {ad_id} не найдено для обновления")
                return False

    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса объявления {ad_id}: {e}")
        return False


async def ad_exists(ad_id: str) -> bool:
    """
    Проверяет, существует ли объявление в базе данных.

    Args:
        ad_id: ID объявления для проверки

    Returns:
        bool: True если объявление существует, False если нет
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute('''
                SELECT 1 FROM ads WHERE ad_id = ?
            ''', (ad_id,))

            result = await cursor.fetchone()
            return result is not None

    except Exception as e:
        logger.error(f"Ошибка при проверке существования объявления {ad_id}: {e}")
        return False


async def increment_processed_counter(account_email: str, db_path: str = DATABASE_PATH) -> int:
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
            new_count = 1
        else:
            # Если запись есть, увеличиваем счётчик
            current_count = row[0]
            new_count = current_count + 1
            await db.execute('''
                UPDATE stat SET processed = ? WHERE account_email = ?
            ''', (new_count, account_email))
            logger.debug(f"Обновлён счётчик processed для аккаунта {account_email}: {current_count} -> {new_count}.")

        await db.commit()
        return new_count


async def get_seller_processed_status(seller_id: str) -> bool:
    """
    Проверяет, был ли уже обработан продавец.

    Args:
        seller_id: ID продавца

    Returns:
        bool: True если продавец уже был обработан, False если нет
    """
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute('''
                SELECT 1 FROM ads WHERE seller_id = ? AND processed = 1 LIMIT 1
            ''', (seller_id,))

            result = await cursor.fetchone()
            return result is not None

    except Exception as e:
        logger.error(f"Ошибка при проверке статуса продавца {seller_id}: {e}")
        return False


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