import asyncio
import logging
import os
from app.registrar import AccountRegistrar
from app.utils.logg import setup_logging
from config import REGISTRAR_DELAY

# --- Настройка логирования ---
logger_instance = setup_logging(logging.DEBUG)
logger = logging.getLogger(__name__)

async def run_single_registrar(semaphore: asyncio.Semaphore, delay: int):
    """
    Запускает один экземпляр регистратора в рамках семафора.
    """
    async with semaphore:
        registrar = AccountRegistrar(delay=delay)
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


async def main():
    """
    Точка входа для запуска компонента регистратора.
    Спрашивает количество аккаунтов и запускает регистрацию пачками.
    """
    logger.info("Запуск компонента регистратора...")

    try:
        total_accounts = int(input("Сколько аккаунтов зарегать? "))
        if total_accounts <= 0:
            print("Количество аккаунтов должно быть положительным числом.")
            return
    except ValueError:
        print("Пожалуйста, введите корректное число.")
        return

    concurrent_limit = int(input("Семафор: "))  # Например, 10 параллельных процессов
    semaphore = asyncio.Semaphore(concurrent_limit)

    tasks = []
    for i in range(total_accounts):
        logger.info(f"Подготовка задачи регистрации для аккаунта {i + 1}/{total_accounts}...")
        task = asyncio.create_task(run_single_registrar(semaphore, REGISTRAR_DELAY))
        tasks.append(task)

    logger.info(f"Запуск {total_accounts} задач регистрации с ограничением {concurrent_limit} параллельных...")

    try:
        # Ждём завершения всех задач, но готовы к KeyboardInterrupt
        await asyncio.gather(*tasks, return_exceptions=True)
    except KeyboardInterrupt:
        logger.info("Получен глобальный KeyboardInterrupt (Ctrl+C).")
        # Отменяем все оставшиеся задачи
        for task in tasks:
            if not task.done():
                task.cancel()
        # Ждём их завершения
        await asyncio.gather(*tasks, return_exceptions=True)


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