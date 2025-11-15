# app/sender.py
import asyncio
import logging
from app.core.database import get_next_unprocessed_ad, increment_processed_counter, update_ad_processed_status
from app.account_manager import AccountManager
from config import ARCHIVE_ACCOUNTS_DIR, LIMIT_PROCESSED, LIMIT_OUT_ACCOUNTS_DIR

logger = logging.getLogger(__name__)


class MessageSender:
    """
    Компонент для отправки сообщений продавцам по объявлениям из базы данных.
    Использует очередь аккаунтов (round-robin) с учётом времени охлаждения.
    Берёт одно объявление за раз и обрабатывает его с помощью доступного аккаунта.
    Самое свежее объявление из базы данных передаётся на обработку.
    """

    def __init__(self):
        self.running = True  # Флаг для остановки из main.py
        self.account_manager = AccountManager()

    async def run(self):
        """
        Основной цикл сендера.
        """
        logger.info("Запуск компонента сендера.")
        await self.account_manager.initialize()
        while self.running:
            try:
                ad = await get_next_unprocessed_ad()
                if ad is None:
                    await asyncio.sleep(1)
                    continue

                # Берём первое (и единственное) объявление из выборки
                ad_id = ad['listingId']
                seller_id = ad['owner']['id']
                logger.debug(f"Найдено объявление для обработки: {ad_id} (продавец: {seller_id})")

                account = await self.account_manager.get_account()

                logger.debug(f"Используем аккаунт {account.email} для отправки сообщения по объявлению {ad_id}.")

                # Отправляем сообщение
                success = await account.process_ad(ad)
                if success:
                    account.processed = await increment_processed_counter(account.email)
                    logger.info(f"({account.processed}) {account.email} - Объявление {ad_id} отписано.")
                else:
                    await update_ad_processed_status(ad_id, 0)

                if account.banned:
                    logger.warning(f"({account.processed}) {account.email} забанен!")
                    # self.account_manager.move_account(account.email, ARCHIVE_ACCOUNTS_DIR)
                    self.account_manager.remove_account(account.email)
                    await account.api.close()
                    continue
                elif account.unauthorized:
                    logger.warning(f"({account.processed}) {account.email} разлогинило!")
                    # self.account_manager.move_account(account.email, ARCHIVE_ACCOUNTS_DIR)
                    self.account_manager.remove_account(account.email)
                    await account.api.close()
                    continue
                elif account.unverified:
                    logger.warning(f"({account.processed}) {account.email} кинуло на вериф!")
                    # self.account_manager.move_account(account.email, ARCHIVE_ACCOUNTS_DIR)
                    self.account_manager.remove_account(account.email)
                    await account.api.close()
                    continue
                elif account.processed >= LIMIT_PROCESSED:
                    logger.warning(f"{account.email} Истратил лимит!")
                    self.account_manager.remove_account(account.email)
                    await account.api.close()
                    continue

                asyncio.create_task(self.account_manager.return_account_to_queue(account))

            except Exception as e:
                logger.error(f"Неожиданная ошибка в цикле сендера: {e}")
                await asyncio.sleep(5) # Пауза при ошибке


