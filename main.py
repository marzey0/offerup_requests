# main.py
import asyncio
import signal
import logging
import os
from typing import Optional

from app.core.database import init_db
from app.parser import OfferUpParser
from app.sender import MessageSender
from app.registrar import AccountRegistrar
from app.utils.logg import setup_logging
from config import DATABASE_PATH, PARSER_DELAY, SENDER_DELAY, REGISTRAR_DELAY

# --- Настройка логирования ---
logger_instance = setup_logging()
logger = logging.getLogger(__name__)

class MainApp:
    """
    Основной класс приложения, координирующий работу парсера, сендера и регистратора.
    """

    def __init__(self):
        # Флаг для корректного завершения работы
        self.running = True
        # Путь к базе данных
        self.db_path = DATABASE_PATH
        # Компоненты
        self.parser: Optional[OfferUpParser] = None
        self.sender: Optional[MessageSender] = None
        self.registrar: Optional[AccountRegistrar] = None

    async def setup(self):
        """
        Инициализация базы данных и создание экземпляров компонентов.
        """
        logger.info("Инициализация базы данных...")
        await init_db(self.db_path)
        logger.info("База данных инициализирована.")

        logger.info("Создание экземпляров компонентов...")
        self.parser = OfferUpParser()
        self.sender = MessageSender()
        self.registrar = AccountRegistrar(delay=REGISTRAR_DELAY)

        logger.info("Экземпляры компонентов созданы.")

    async def run_components(self):
        """
        Запускает все компоненты в отдельных асинхронных задачах.
        Возвращает список задач для последующего управления.
        """
        logger.info("Запуск компонентов...")
        task_parser = asyncio.create_task(self.parser.run(), name="Parser")
        task_sender = asyncio.create_task(self.sender.run(), name="Sender")
        task_registrar = asyncio.create_task(self.registrar.run(), name="Registrar")

        tasks = [task_parser, task_sender, task_registrar]
        logger.info("Все компоненты запущены.")
        return tasks

    async def shutdown(self, signal_name=None):
        """
        Обработка остановки. Устанавливает флаг и отменяет все задачи.
        """
        if signal_name:
            logger.info(f"Получен сигнал {signal_name}. Выполняется завершение...")
        else:
            logger.info("Выполняется завершение приложения...")

        self.running = False


async def main():
    """
    Основная асинхронная функция, точка входа в приложение.
    """
    logger.info("Запуск приложения...")

    main_app = MainApp()

    # Инициализация
    await main_app.setup()

    # Запуск компонентов
    tasks = await main_app.run_components()

    # Проверяем, является ли система Windows
    if os.name == 'nt':  # Windows
        logger.info("ОС Windows: ожидание KeyboardInterrupt (Ctrl+C)...")
        try:
            # Ждём завершения всех задач, но готовы к KeyboardInterrupt
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            logger.info("Получен KeyboardInterrupt (Ctrl+C).")
        finally:
            await main_app.shutdown()
            logger.info("Все задачи завершены. Приложение остановлено.")
    else:  # Unix-like (Linux, macOS)
        # Установка обработчиков сигналов для корректного завершения
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(main_app.shutdown(s.name)))

        logger.info("Ожидание завершения задач или сигнала...")

        # Ждём завершения всех задач
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except KeyboardInterrupt:
            # Это может не сработать напрямую, так как сигналы обрабатываются выше
            logger.info("Получен KeyboardInterrupt.")
        finally:
            # Завершение по флагу, если сигнал не вызвал shutdown
            if main_app.running:
                await main_app.shutdown()
            logger.info("Все задачи завершены. Приложение остановлено.")


if __name__ == "__main__":
    asyncio.run(main())