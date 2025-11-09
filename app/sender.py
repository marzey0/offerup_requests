# app/core/sender.py
import asyncio
import logging
import time
import random
from typing import Dict, Any, Optional
from app.core.offerup_api import OfferUpAPI
from app.core.database import get_unprocessed_ads, mark_ad_as_processed
from app.account_manager import AccountManager
from config import SENDER_DELAY, SENDER_COOLDOWN_SECONDS

logger = logging.getLogger(__name__)


class MessageSender:
    """
    Компонент для отправки сообщений продавцам по объявлениям из базы данных.
    Использует очередь аккаунтов (round-robin) с учётом времени охлаждения.
    Берёт одно объявление за раз и обрабатывает его с помощью доступного аккаунта.
    Самое свежее объявление из базы данных передаётся на обработку.
    """

    def __init__(self, db_path: str, delay: int = SENDER_DELAY):
        self.db_path = db_path
        self.delay = delay
        self.running = True  # Флаг для остановки из main.py
        self.account_manager = AccountManager()
        # Словарь для отслеживания времени последнего использования аккаунта
        self.account_last_used: Dict[str, float] = {}
        # Индекс для round-robin выбора аккаунта
        self.account_index = 0

    async def run(self):
        """
        Основной цикл сендера.
        """
        logger.info("Запуск компонента сендера.")
        while self.running:
            try:
                logger.debug("Проверка на наличие необработанных объявлений...")
                # Берём *одно* объявление из БД
                ads = await get_unprocessed_ads(self.db_path, limit=1)
                if not ads:
                    logger.debug(f"Нет необработанных объявлений (processed=1). Пауза {self.delay} секунд.")
                    await asyncio.sleep(self.delay)
                    continue

                # Берём первое (и единственное) объявление из выборки
                ad = ads[0]
                ad_id = ad['ad_id']
                seller_id = ad['seller_id']
                logger.info(f"Найдено объявление для обработки: {ad_id} (продавец: {seller_id})")

                # Выбираем аккаунт с учётом времени охлаждения
                account_key = await self._get_available_account()
                if not account_key:
                    logger.warning("Нет доступных аккаунтов с учётом времени охлаждения. Пауза.")
                    await asyncio.sleep(self.delay)
                    continue

                logger.info(f"Используем аккаунт {account_key} для отправки сообщения по объявлению {ad_id}.")

                # Получаем API клиент для выбранного аккаунта
                api_client = self.account_manager.get_api_instance(account_key)
                if not api_client:
                    logger.error(f"Не удалось получить API клиент для аккаунта {account_key}.")
                    continue

                # Отправляем сообщение
                success = await self._send_message_to_seller(api_client, ad)
                if success:
                    # Помечаем объявление как обработанное
                    marked = await mark_ad_as_processed(self.db_path, ad_id)
                    if marked:
                        logger.info(f"Объявление {ad_id} помечено как обработанное (processed=2).")
                    else:
                        logger.error(f"Не удалось пометить объявление {ad_id} как обработанное.")
                else:
                    logger.warning(f"Не удалось отправить сообщение по объявлению {ad_id} через аккаунт {account_key}.")

                # Обновляем время последнего использования аккаунта
                self.account_last_used[account_key] = time.time()

                # Пауза между обработками объявлений
                await asyncio.sleep(self.delay)

            except Exception as e:
                logger.error(f"Неожиданная ошибка в цикле сендера: {e}")
                await asyncio.sleep(self.delay) # Пауза даже при ошибке

    async def _get_available_account(self) -> Optional[str]:
        """
        Возвращает ключ аккаунта, который доступен для использования (прошло время охлаждения).
        Использует round-robin для перебора аккаунтов.
        """
        account_keys = self.account_manager.get_all_account_keys()
        if not account_keys:
            logger.warning("Нет загруженных аккаунтов.")
            return None

        current_time = time.time()
        num_accounts = len(account_keys)

        # Проверяем аккаунты, начиная с последнего использованного + 1 (round-robin)
        for i in range(num_accounts):
            idx = (self.account_index + i) % num_accounts
            key = account_keys[idx]

            last_used = self.account_last_used.get(key, 0)
            if current_time - last_used >= SENDER_COOLDOWN_SECONDS:
                # Нашли подходящий аккаунт
                self.account_index = (idx + 1) % num_accounts # Обновляем индекс для следующего раза
                return key

        # Ни один аккаунт не прошёл проверку на охлаждение
        logger.debug("Нет доступных аккаунтов, все на cooldown.")
        return None

    async def _send_message_to_seller(self, api_client: OfferUpAPI, ad: Dict[str, Any]) -> bool:
        """
        Отправляет сообщение продавцу по указанному объявлению, используя post_first_message.
        """
        ad_id = ad['ad_id']
        # seller_id = ad['seller_id'] # seller_id не нужен для post_first_message

        # Выбираем случайное сообщение из pasta аккаунта, установленной AccountManager
        pasta = api_client._pasta
        if not pasta:
            logger.warning("У аккаунта нет 'pasta'. Используется стандартное сообщение.")
            message_text = "Привет, интересует ваш товар."
        else:
            message_text = random.choice(pasta)

        logger.info(f"Отправка сообщения '{message_text}' по объявлению {ad_id}.")

        try:
            async with api_client as ac: # Открываем сессию
                # 1. Отправить первое сообщение в чат по объявлению
                logger.debug(f"Отправляем первое сообщение '{message_text}' по объявлению {ad_id}...")
                post_first_message_response = await ac.post_first_message(listing_id=ad_id, text=message_text)
                if not post_first_message_response or 'errors' in post_first_message_response:
                    logger.error(f"Ошибка при отправке первого сообщения: {post_first_message_response}")
                    return False

                # 2. Проверим, успешно ли создалось обсуждение (опционально, в зависимости от структуры ответа)
                # В ответе на post_first_message может быть discussionId
                discussion_id = post_first_message_response.get('data', {}).get('postFirstMessage', {}).get('discussionId')
                if discussion_id:
                    logger.info(f"Сообщение успешно отправлено, создан чат с ID: {discussion_id}.")
                else:
                    # Если discussionId нет, но ошибки тоже нет, возможно, сообщение отправлено успешно
                    logger.info(f"Сообщение успешно отправлено по объявлению {ad_id} (discussionId не возвращён, но ошибок нет).")

                return True

        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения по объявлению {ad_id}: {e}")
            return False
