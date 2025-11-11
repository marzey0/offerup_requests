# run_sender.py
import asyncio
import logging
import os

from app.core.database import init_db
from app.sender import MessageSender
from app.utils.logg import setup_logging
from config import DATABASE_PATH

# --- Настройка логирования ---
logger_instance = setup_logging(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def main():
    """
    Точка входа для запуска только сендера.
    """
    await init_db()

    logger.info("Запуск только компонента сендера...")

    sender = MessageSender()
    sender.running = True

    logger.info("Запуск задачи сендера...")
    task = asyncio.create_task(sender.run(), name="Sender")

    try:
        # Ждём завершения задачи, но готовы к KeyboardInterrupt
        await asyncio.gather(task, return_exceptions=True)
    except KeyboardInterrupt:
        logger.info("Получен KeyboardInterrupt (Ctrl+C).")
    finally:
        logger.info("Остановка сендера...")
        sender.running = False
        # Отменяем задачу, если она ещё работает
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await sender.account_manager.finalize()
        logger.info("Сендер остановлен.")


if __name__ == "__main__":
    if os.name == 'nt': # Проверяем, Windows ли это
        logger.info("ОС Windows: запуск сендера с обработкой KeyboardInterrupt...")
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nПрограмма завершена пользователем.")
    else:
        # Для Unix-систем можно использовать add_signal_handler, если нужно
        # Но для простоты пока оставим как есть
        asyncio.run(main())