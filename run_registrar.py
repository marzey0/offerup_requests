# run_registrar.py
import asyncio
import logging
import os
from app.registrar import AccountRegistrar
from app.utils.logg import setup_logging
from config import REGISTRAR_DELAY

# --- Настройка логирования ---
logger_instance = setup_logging(logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    """
    Точка входа для запуска только регистратора.
    """
    logger.info("Запуск только компонента регистратора...")

    registrar = AccountRegistrar(delay=REGISTRAR_DELAY)
    registrar.running = True

    logger.info("Запуск задачи регистратора...")
    task = asyncio.create_task(registrar.run(), name="Registrar")

    try:
        # Ждём завершения задачи, но готовы к KeyboardInterrupt
        await asyncio.gather(task, return_exceptions=True)
    except KeyboardInterrupt:
        logger.info("Получен KeyboardInterrupt (Ctrl+C).")
    finally:
        logger.info("Остановка регистратора...")
        registrar.running = False
        # Отменяем задачу, если она ещё работает
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass # Ожидаемое поведение при отмене
        logger.info("Регистратор остановлен.")


if __name__ == "__main__":
    # Проверяем, Windows ли это
    if os.name == 'nt':
        logger.info("ОС Windows: запуск регистратора с обработкой KeyboardInterrupt...")
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nПрограмма завершена пользователем.")
    else:
        # Для Unix-систем можно использовать add_signal_handler, если нужно
        # Но для простоты пока оставим как есть
        asyncio.run(main())