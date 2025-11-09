# run_parser.py
import asyncio
import logging
import os

from app.core.database import init_db
from app.parser import OfferUpParser
from app.utils.logg import setup_logging
from config import DATABASE_PATH, PARSER_DELAY


# --- Настройка логирования ---
logger_instance = setup_logging(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    """
    Точка входа для запуска только парсера.
    """
    logger.info("Запуск только компонента парсера...")

    await init_db()

    parser = OfferUpParser(db_path=DATABASE_PATH, delay=PARSER_DELAY)
    parser.running = True

    logger.info("Запуск задачи парсера...")
    task = asyncio.create_task(parser.run(), name="Parser")

    try:
        # Ждём завершения задачи, но готовы к KeyboardInterrupt
        await asyncio.gather(task, return_exceptions=True)
    except KeyboardInterrupt:
        logger.info("Получен KeyboardInterrupt (Ctrl+C).")
    finally:
        logger.info("Остановка парсера...")
        parser.running = False
        # Отменяем задачу, если она ещё работает
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass # Ожидаемое поведение при отмене
        logger.info("Парсер остановлен.")


if __name__ == "__main__":
    if os.name == 'nt': # Проверяем, Windows ли это
        logger.info("ОС Windows: запуск парсера с обработкой KeyboardInterrupt...")
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nПрограмма завершена пользователем.")
    else:
        # Для Unix-систем можно использовать add_signal_handler, если нужно
        # Но для простоты пока оставим как есть
        asyncio.run(main())