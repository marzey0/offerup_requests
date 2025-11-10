# app/account_manager.py
import logging
import os
import asyncio
from typing import Dict, Optional, List, Tuple, Any
from asyncio import Queue

from faker.generator import random

from app.core.database import get_processed_count
from app.offerup_account import OfferUpAccount
from config import ACCOUNTS_DIR

logger = logging.getLogger(__name__)


class AccountManager:
    """
    Класс для управления аккаунтами: загрузка, сохранение, предоставление эккаунтов.
    Реализует очередь аккаунтов с охлаждением.
    """

    def __init__(self, accounts_dir: str = ACCOUNTS_DIR):
        self.accounts_dir = accounts_dir
        self.accounts: Dict[str, OfferUpAccount] = {}  # Словарь: {key: OfferUpAccount}
        self.available_accounts_queue: Queue = Queue()  # Очередь ключей аккаунтов, доступных для использования
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitoring = False
        self._lock = asyncio.Lock() # Лок для синхронизации доступа к очереди

    async def start_monitoring(self):
        """
        Запускает асинхронный мониторинг директории accounts на появление новых файлов.
        """
        if self._monitoring:
            logger.warning("Мониторинг уже запущен.")
            return

        logger.info(f"Запуск мониторинга директории {self.accounts_dir} на появление новых аккаунтов...")
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Мониторинг аккаунтов запущен.")

    async def stop_monitoring(self):
        """
        Останавливает мониторинг директории.
        """
        if not self._monitoring:
            return
        logger.info("Остановка мониторинга аккаунтов...")
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Мониторинг аккаунтов остановлен.")

    async def _monitor_loop(self):
        """
        Внутренний цикл мониторинга директории.
        """
        existing_files = {f for f in os.listdir(self.accounts_dir) if f.endswith('.json')}
        while self._monitoring:
            try:
                current_files = {f for f in os.listdir(self.accounts_dir) if f.endswith('.json')}

                new_files = current_files - existing_files

                if new_files:
                    logger.info(f"Найдены новые файлы аккаунтов: {new_files}")
                    for filename in new_files:
                        filepath = os.path.join(self.accounts_dir, filename)
                        await self._load_single_account(filepath)

                existing_files = current_files
            except OSError as e:
                logger.error(f"Ошибка доступа к директории {self.accounts_dir}: {e}")
            except Exception as e:
                logger.error(f"Неизвестная ошибка в цикле мониторинга: {e}")

            await asyncio.sleep(10) # Проверка каждые 10 секунд

    async def _load_single_account(self, filepath: str):
        """
        Загружает один аккаунт из файла и добавляет в менеджер.
        """
        try:
            if account := OfferUpAccount.load_from_file(filepath):
                if account.email in self.accounts:
                    logger.warning(f"Аккаунт с ключом {account.email} уже загружен. Файл {filepath} проигнорирован.")
                    return

                account.processed = await get_processed_count(account.email)
                self.accounts[account.email] = account
                # Добавляем в очередь доступных аккаунтов
                await self.available_accounts_queue.put(account.email)
                logger.info(f"Аккаунт {account.email} загружен и добавлен в очередь.")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при загрузке {filepath}: {e}")

    def get_all_account_keys(self) -> List[str]:
        """
        Возвращает список всех ключей (email или user_id) загруженных аккаунтов.
        """
        return list(self.accounts.keys())

    async def get_account(self) -> OfferUpAccount:
        """
        Берёт аккаунт из очереди. Если очередь пуста, ожидает.
        """
        async with self._lock:
            # Локаем, чтобы гарантировать, что один аккаунт не будет выдан дважды
            key = await self.available_accounts_queue.get() # Блокируется, если очередь пуста
            account = self.accounts.get(key)
            if not account:
                # На всякий случай, если аккаунт был удалён между проверкой и получением
                logger.warning(f"Аккаунт с ключом {key} не найден в словаре при выдаче.")
                # Повторяем попытку получения другого аккаунта
                return await self.get_account()
            logger.debug(f"Аккаунт {key} предоставлен для использования.")
            return account

    async def return_account_to_queue(self, key: str):
        """
        Возвращает аккаунт в очередь после использования.
        Ожидает время охлаждения перед возвратом.
        """
        account = self.accounts.get(key)
        if not account:
            logger.warning(f"Попытка вернуть несуществующий аккаунт {key} в очередь.")
            return

        if account.cooldown > 0:
            cooldown = random.uniform(account.cooldown*0.9, account.cooldown*1.1)
            logger.debug(f"Ожидание охлаждения аккаунта {key} ({cooldown:.2f} сек).")
            await asyncio.sleep(cooldown)

        # Возвращаем ключ в очередь
        await self.available_accounts_queue.put(key)
        logger.debug(f"Аккаунт {key} возвращён в очередь после охлаждения.")

    def remove_account(self, key: str):
        """
        Удаляет аккаунт из менеджера и удаляет файл.
        """
        if key in self.accounts:
            account = self.accounts[key]
            account.delete_file()
            del self.accounts[key]
            logger.info(f"Аккаунт {key} удалён из менеджера и файл удален.")
        else:
            logger.warning(f"Попытка удалить несуществующий аккаунт {key}.")

    async def initialize(self):
        """
        Инициализирует менеджер: загружает начальные аккаунты и запускает мониторинг.
        """
        # Загрузка начальных аккаунтов
        for filename in os.listdir(self.accounts_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.accounts_dir, filename)
                await self._load_single_account(filepath)

        await self.start_monitoring()

    async def finalize(self):
        """
        Завершает работу менеджера: останавливает мониторинг.
        """
        tasks = [account.api.close() for account in self.accounts.values()]
        tasks.append(self.stop_monitoring())
        await asyncio.gather(*tasks)