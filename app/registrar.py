# app/registrar.py
import asyncio
import logging
import json
import traceback
import uuid
from typing import Dict, Any, Optional

from faker import Faker
from app.core.anymessage import AnyMessageClient
from app.core.greedy_sms import GreedySMSClient
from app.offerup_account import OfferUpAccount
from config import (
    REGISTRAR_DELAY,
    DEFAULT_PASTA,
    MAIN_PROXY,
    GREEDY_COUNTRY_ID,
    GREEDY_SERVICE_ID,
    GREEDY_OPERATOR_NAME,
    GREEDY_MAX_PRICE,
    ANYMESSAGE_EMAIL_SITE,
    ANYMESSAGE_EMAIL_DOMAIN, VERIFY_EMAIL, VERIFY_PHONE, DEFAULT_ACCOUNT_NAME
)

logger = logging.getLogger(__name__)


class AccountRegistrar:
    """
    Компонент для регистрации, верификации email и телефона новых аккаунтов.
    """

    def __init__(self, delay: int = REGISTRAR_DELAY):
        self.delay = delay
        self.running = True  # Флаг для остановки цикла из main.py
        self.faker = Faker()

        self.account: Optional[OfferUpAccount] = None
        self.anymessage_client = AnyMessageClient()
        self.greedy_sms = GreedySMSClient()

    async def run(self):
        """
        Основной цикл регистратора. Бесконечно пытается зарегистрировать аккаунты.
        """
        logger.info("Запуск компонента регистратора.")
        try:
            while self.running:
                try:
                    logger.debug("Попытка регистрации нового аккаунта...")
                    success = await self._register_single_account()
                    if success:
                        logger.info("Аккаунт успешно зарегистрирован, верифицирован и сохранён.")
                    else:
                        logger.warning("Не удалось зарегистрировать аккаунт, повтор через задержку.")
                    await asyncio.sleep(self.delay)
                except Exception as e:
                    logger.error(f"Неожиданная ошибка в цикле регистратора: {e}")
                    await asyncio.sleep(self.delay) # Пауза даже при ошибке
        finally:
            if self.account:
                await self.account.api.close()
            await self.anymessage_client.close()
            await self.greedy_sms.close()

    async def _register_single_account(self) -> bool:
        """
        Выполняет полный цикл регистрации одного аккаунта: создание, верификация email, верификация телефона.
        Возвращает True, если аккаунт успешно создан и верифицирован.
        """
        logger.debug("Заказ email через AnyMessage...")
        ordered_email, email_id = await self._order_email_with_anymessage()
        if not ordered_email:
            logger.error("Не удалось заказать email. Прерывание регистрации.")
            return False

        self.account = OfferUpAccount(
            email=ordered_email,
            password=self._generate_random_password(),
            name=self.faker.user_name() if "random" in DEFAULT_ACCOUNT_NAME.lower() else DEFAULT_ACCOUNT_NAME,
            proxy=MAIN_PROXY,
            pasta=DEFAULT_PASTA,
            anymessage_email_id=email_id
        )

        register_result = await self.account.register()
        if not register_result:
            return False

        await self.account.api.change_email(self.account.user_id, self.account.email)

        # --- Верификация Email (ожидание письма и подтверждение) ---
        if VERIFY_EMAIL:
            email_verified = await self._wait_for_verification_email_and_confirm(email_id)
            if not email_verified:
                logger.error(f"Не удалось верифицировать email для {ordered_email}.")
                return False

        # --- Верификация Телефона ---
        if VERIFY_PHONE:
            phone_verified = await self._verify_phone_with_greedy_sms()
            if not phone_verified:
                logger.warning(f"Не удалось верифицировать телефон для {ordered_email}.")

        self.account.save_to_file()
        logger.info(f"Зарегистрирован новый аккаунт: {ordered_email}")
        await self.account.api.close()
        self.account = None
        return True

    @staticmethod
    def _generate_random_password() -> str:
        """
        Генерирует случайный пароль.
        """
        # Простая генерация, можно улучшить
        unique_part = str(uuid.uuid4())[:8]
        return f"Pass{unique_part}123!"

    @staticmethod
    def _is_successful_response(response: Dict[str, Any]) -> bool:
        """
        Проверяет, является ли ответ от API успешным (пока простая проверка).
        """
        return response is not None and 'errors' not in response

    async def _order_email_with_anymessage(self) -> tuple[Optional[str], Optional[str]]:
        """
        Заказывает email через AnyMessage API и возвращает (email, email_id) или (None, None) при ошибке.
        """
        logger.debug("Заказ email через AnyMessage для регистрации.")
        async with self.anymessage_client as anymessage:
            try:
                order_response = await anymessage.order_email(site=ANYMESSAGE_EMAIL_SITE, domain=ANYMESSAGE_EMAIL_DOMAIN)
                if order_response.get('status') != 'success':
                    logger.error(f"Не удалось заказать email через AnyMessage: {order_response}")
                    return None, None

                self.email = order_response['email']
                self.anymessage_email_id = order_response['id']
                logger.debug(f"Заказан email: {self.email}, ID: {self.anymessage_email_id}")
                return self.email, self.anymessage_email_id

            except Exception as e:
                logger.error(f"Ошибка при заказе email через AnyMessage: {e}")
                return None, None

    async def _wait_for_verification_email_and_confirm(self, email_id: str) -> bool:
        """
        Ждёт письмо с подтверждением от AnyMessage, извлекает userId и token,
        затем вызывает API для подтверждения email.
        Возвращает True при успехе.
        """
        logger.debug(f"Ожидание письма с подтверждением email (ID: {email_id}) через AnyMessage.")
        await asyncio.sleep(30)
        async with self.anymessage_client as anymessage:
            try:
                max_attempts = 10
                for attempt in range(max_attempts):
                    logger.debug(f"Попытка {attempt + 1}/{max_attempts} получить письмо...")
                    message_response = await anymessage.get_message(email_id=email_id)
                    logger.debug(f"Ответ AnyMessage (попытка {attempt + 1}): {message_response}")

                    if message_response.get('status') == 'error' and message_response.get('value') == 'wait message':
                        logger.debug(f"Письмо ещё не пришло (AnyMessage: wait message), попытка {attempt + 1}.")
                        await asyncio.sleep(10)
                        continue

                    if message_response.get('status') == 'success':
                        message_content = message_response.get('message', '')
                        import re
                        match = re.search(r'href=[\'"]([^\'"]*offerup\.com[^\s\'"]*confirm-email[^\s\'"]*)[\'"]', message_content)
                        if match:
                            link_url = match.group(1).replace('&amp;', '&') # Заменяем &amp; на &
                            logger.debug(f"Найден URL в письме: {link_url}")

                            # Извлекаем параметры из URL
                            from urllib.parse import urlparse, parse_qs
                            parsed_url = urlparse(link_url)
                            params = parse_qs(parsed_url.query)
                            user_id = params.get('user_id', [None])[0]
                            token = params.get('token', [None])[0]
                            # challenge_id = params.get('challenge_id', [None])[0] # может быть пустым

                            if not user_id or not token:
                                logger.error(f"Не удалось извлечь user_id или token из URL: {link_url}")
                                return False

                            logger.debug("Отправка запроса подтверждения email через API...")
                            try:
                                confirm_response = await self.account.api.confirm_email_from_token(user_id=user_id, token=token)
                                # Логируем ответ для отладки (можно убрать позже)
                                logger.debug(f"Ответ confirm_email_from_token: {confirm_response}")
                                # Если ответ успешный (без ошибок), считаем, что email подтверждён
                                if confirm_response and 'errors' not in confirm_response:
                                    logger.debug("Email успешно подтверждён через API (confirm_email_from_token).")
                                    return True
                                else:
                                    logger.error(f"Ошибка подтверждения email через API: {confirm_response.get('errors')}")
                                    return False
                            except Exception as e_api:
                                logger.error(f"Ошибка при вызове confirm_email_from_token: {e_api}", traceback.format_exc())
                                return False
                        else:
                            logger.warning("Ссылка подтверждения не найдена в письме (message).")
                    else:
                        logger.error(f"AnyMessage вернул неожиданный статус или ошибку: {message_response}")
                        return False

                logger.error(f"Не дождались письма с подтверждением за {max_attempts * 10} секунд.")
                return False

            except Exception as e:
                logger.error(f"Ошибка при ожидании письма с подтверждением: {e}")
                return False

    async def _verify_phone_with_greedy_sms(self) -> bool:
        """
        Верифицирует телефон, используя GreedySMS API.
        """
        logger.debug("Начало верификации телефона через GreedySMS.")
        async with self.greedy_sms as sms_client:
            for i in range(5):
                if i != 1:
                    await asyncio.sleep(3)

                try:
                    # 1. Получить номер
                    logger.debug("Получение номера через GreedySMS...")
                    number_response = await sms_client.get_number(
                        country=GREEDY_COUNTRY_ID,
                        service=GREEDY_SERVICE_ID,
                        operator=GREEDY_OPERATOR_NAME,
                        max_price=GREEDY_MAX_PRICE
                    )
                    if number_response.get('error'):
                        logger.error(f"Не удалось получить номер через GreedySMS: {number_response}")
                        continue

                    activation_id = number_response['activationId']
                    phone_number = number_response['phone'][1:]
                    logger.debug(f"Получен номер: {phone_number}, ID активации: {activation_id}")

                    # 2. Отправить номер на OfferUp
                    logger.debug(f"Отправка номера {phone_number} на OfferUp...")
                    change_phone_response = await self.account.api.change_phone_number(phone_number=phone_number)
                    if 'errors' in change_phone_response:
                        logger.error(f"Ошибка при отправке номера на OfferUp: {change_phone_response}")
                        continue

                    reference_id = change_phone_response.get('data', {}).get('changePhoneNumber', {}).get('referenceId')
                    if not reference_id:
                         logger.error("Не удалось получить referenceId после отправки номера.")
                         continue

                    # 3. Ждём SMS
                    max_attempts = 10
                    for attempt in range(max_attempts):
                        logger.debug(f"Попытка {attempt + 1}/{max_attempts} получить SMS...")
                        status_response = await sms_client.get_status(activation_id=activation_id)
                        status = status_response.get('status')
                        if "STATUS_OK" in status:
                            otp_code = status.lstrip("STATUS_OK:")
                            logger.debug(f"Получен OTP-код: {otp_code}")
                            # 4. Подтвердить номер с OTP
                            logger.debug(f"Подтверждение номера {phone_number} с OTP {otp_code}...")
                            confirm_response = await self.account.api.change_phone_number_confirm(
                                otp=otp_code,
                                reference_id=reference_id,
                                phone_number=phone_number
                            )
                            if 'errors' in confirm_response:
                                logger.error(f"Ошибка при подтверждении номера: {confirm_response}")
                                continue
                            logger.debug("Номер успешно подтверждён.")
                            return True
                        elif status in ['timeout', 'banned', 'canceled']:
                            logger.error(f"Статус активации {status}, номер: {phone_number}.")
                            continue
                        else:
                            # Статус 'waiting' или 'used' или 'delay'
                            logger.debug(f"Статус активации: {status}. Ожидание...")
                            await asyncio.sleep(15) # Ждём 15 секунд перед следующей проверкой

                    logger.error(f"Не дождались SMS-кода для номера {phone_number} за {max_attempts * 15} секунд.")
                    continue

                except Exception as e:
                    logger.error(f"Ошибка при верификации телефона через GreedySMS: {e}")
                    continue

        return False