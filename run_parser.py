# run_parser.py
import asyncio
import logging
import os

from app.core.database import init_db
from app.parser import OfferUpParser
from app.utils.logg import setup_logging


# --- Настройка логирования ---
logger_instance = setup_logging(level=logging.DEBUG)


async def main():
    """
    Точка входа для запуска только парсера.
    """

    await init_db()

    parser = OfferUpParser()

    print("Запуск задачи парсера...")
    task = asyncio.create_task(parser.run(), name="Parser")

    try:
        # Ждём завершения задачи, но готовы к KeyboardInterrupt
        await asyncio.gather(task, return_exceptions=True)
    except KeyboardInterrupt:
        print("Получен KeyboardInterrupt (Ctrl+C).")
    finally:
        await parser.offerup_api.close()
        print("Остановка парсера...")
        # Отменяем задачу, если она ещё работает
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass # Ожидаемое поведение при отмене
        print("Парсер остановлен.")


if __name__ == "__main__":
    if os.name == 'nt': # Проверяем, Windows ли это
        print("ОС Windows: запуск парсера с обработкой KeyboardInterrupt...")
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nПрограмма завершена пользователем.")
    else:
        # Для Unix-систем можно использовать add_signal_handler, если нужно
        # Но для простоты пока оставим как есть
        asyncio.run(main())