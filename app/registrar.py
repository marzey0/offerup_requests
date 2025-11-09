# app/core/registrar.py
import asyncio
import logging
import json
import traceback
import uuid
from typing import Dict, Any, Optional

from aiohttp_socks import ProxyConnector
from fake_useragent import UserAgent
from faker import Faker
from app.core.offerup_api import OfferUpAPI
from app.core.anymessage import AnyMessageClient
from app.core.greedy_sms import GreedySMSClient
from config import (
    REGISTRAR_DELAY,
    MESSAGES,
    MAIN_PROXY,
    GREEDY_COUNTRY_ID,
    GREEDY_SERVICE_ID,
    GREEDY_OPERATOR_NAME,
    GREEDY_MAX_PRICE,
    ANYMESSAGE_EMAIL_SITE,
    ANYMESSAGE_EMAIL_DOMAIN
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

        self.offerup_api = OfferUpAPI()
        self.anymessage_client = AnyMessageClient()
        self.greedy_sms = GreedySMSClient()

        self.email: Optional[str] = None
        self.password: str = self._generate_random_password()
        self.username: Optional[str] = None

        self.anymessage_email_id: Optional[str] = None

    async def run(self):
        """
        Основной цикл регистратора. Бесконечно пытается зарегистрировать аккаунты.
        """
        logger.info("Запуск компонента регистратора.")
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

    async def _register_single_account(self) -> bool:
        """
        Выполняет полный цикл регистрации одного аккаунта: создание, верификация email, верификация телефона.
        Возвращает True, если аккаунт успешно создан и верифицирован.
        """
        # --- 1. Получение email через AnyMessage ---
        logger.debug("Заказ email через AnyMessage...")
        ordered_email, email_id = await self._order_email_with_anymessage()
        if not ordered_email:
            logger.error("Не удалось заказать email. Прерывание регистрации.")
            return False

        # --- 2. Подготовка данных аккаунта ---
        password = self._generate_random_password()
        name = self.faker.name()  # Используем Faker для имени
        proxy = MAIN_PROXY

        logger.info(f"Регистрация аккаунта: {ordered_email}, proxy: {proxy}")

        # --- 3. Регистрация ---
        try:
            logger.debug("Отправка запроса на регистрацию...")
            async with self.offerup_api as offerup:  # Открываем сессию
                signup_response = await offerup.signup(email=ordered_email, name=name, password=password)
                if not self._is_successful_response(signup_response):
                    logger.error(f"Ошибка регистрации для {ordered_email}: {signup_response}")
                    return False

                jwt_token = offerup._jwt_token
                refresh_token = offerup._refresh_token
                user_id = offerup._user_id  # Получили user_id после регистрации

                if not jwt_token or not refresh_token or not user_id:
                    logger.error(f"Не все токены/ID получены при регистрации {ordered_email}.")
                    return False

                logger.info(f"Регистрация {ordered_email} успешна. Получены токены и user_id.")

        except Exception as e:
            logger.error(f"Ошибка при регистрации или инициации верификации email для {ordered_email}: {e}")
            return False

        # --- 6. Верификация Email (ожидание письма и подтверждение) ---
        # Теперь вызываем ожидание письма
        self.anymessage_client._anymessage_email_id = email_id  # Предполагаем, что API клиент хранит это
        email_verified = await self._wait_for_verification_email_and_confirm(email_id)
        if not email_verified:
            logger.error(f"Не удалось верифицировать email для {ordered_email}.")
            return False

        # --- 7. Верификация Телефона ---
        # phone_verified = await self._verify_phone_with_greedy_sms()
        # if not phone_verified:
        #     logger.error(f"Не удалось верифицировать телефон для {ordered_email}.")
        #     return False

        # --- 8. Сохранение аккаунта ---
        await self._save_account_to_file(
            email=ordered_email,
            password=password,
            jwt_token=jwt_token,
            refresh_token=refresh_token,
            user_id=user_id,
            pasta=MESSAGES,
            user_agent=self.offerup_api._user_agent,
            browser_user_agent=self.offerup_api._browser_user_agent,
            proxy=proxy,
            session_id=self.offerup_api._session_id,
            device_id=self.offerup_api._device_id,
            advertising_id=self.offerup_api._advertising_id,
            anymessage_email_id=email_id,
            email_verified=True,  # Устанавливаем как True, если _wait_for_verification_email_and_confirm вернул True
            phone_verified=False
        )

        logger.info(f"Аккаунт {ordered_email} успешно сохранён в файл.")
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
        logger.info("Заказ email через AnyMessage для регистрации.")
        async with self.anymessage_client as anymessage:
            try:
                order_response = await anymessage.order_email(site=ANYMESSAGE_EMAIL_SITE, domain=ANYMESSAGE_EMAIL_DOMAIN)
                if order_response.get('status') != 'success':
                    logger.error(f"Не удалось заказать email через AnyMessage: {order_response}")
                    return None, None

                self.email = order_response['email']
                self.anymessage_email_id = order_response['id']
                logger.info(f"Заказан email: {self.email}, ID: {self.anymessage_email_id}")
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
        logger.info(f"Ожидание письма с подтверждением email (ID: {email_id}) через AnyMessage.")
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
                            logger.info(f"Найден URL в письме: {link_url}")

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

                            logger.info(f"Извлечены user_id и token для подтверждения email.")

                            # --- НОВОЕ: Вызов API подтверждения email ---
                            logger.info("Отправка запроса подтверждения email через API...")
                            try:
                                async with self.offerup_api as ac: # Открываем сессию для API запроса
                                    confirm_response = await ac.confirm_email_from_token(user_id=user_id, token=token)
                                    # Логируем ответ для отладки (можно убрать позже)
                                    logger.debug(f"Ответ confirm_email_from_token: {confirm_response}")
                                    # Если ответ успешный (без ошибок), считаем, что email подтверждён
                                    if confirm_response and 'errors' not in confirm_response:
                                        logger.info("Email успешно подтверждён через API (confirm_email_from_token).")
                                    else:
                                        logger.error(f"Ошибка подтверждения email через API: {confirm_response.get('errors')}")
                                        return False
                            except Exception as e_api:
                                logger.error(f"Ошибка при вызове confirm_email_from_token: {e_api}", traceback.format_exc())
                                return False
                            # --- КОНЕЦ НОВОГО ---

                            # --- Проверка статуса email через API ---
                            logger.info("Проверка статуса верификации email через API...")
                            # Ждём немного, чтобы OfferUp успел обновить статус после confirm_email
                            await asyncio.sleep(10)
                            try:
                                async with self.offerup_api as ac: # Открываем сессию для API запроса
                                    auth_user_response = await ac.get_auth_user()
                                    # Логируем ответ для отладки (можно убрать позже)
                                    logger.debug(f"Ответ get_auth_user после подтверждения: {auth_user_response}")
                                    # Извлекаем статус верификации из ответа
                                    is_email_verified = auth_user_response.get('data', {}).get('me', {}).get('profile', {}).get('isEmailVerified', False)
                                    if is_email_verified:
                                        logger.info("Статус email подтверждён подтверждён через API (get_auth_user).")
                                        return True # Успех!
                                    else:
                                        logger.warning("API сообщил, что email НЕ подтверждён, хотя запрос confirm_email был успешен.")
                                        # Можно попробовать ещё раз или вернуть False
                                        # Пока вернём False
                                        return False
                            except Exception as e_api:
                                logger.error(f"Ошибка при проверке статуса email через API: {e_api}")
                                return False
                            # --- КОНЕЦ ПРОВЕРКИ ---

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
        logger.info("Начало верификации телефона через GreedySMS.")
        async with self.greedy_sms as sms_client:
            try:
                # 1. Получить номер
                logger.debug("Получение номера через GreedySMS...")
                number_response = await sms_client.get_number(
                    country=GREEDY_COUNTRY_ID,
                    service=GREEDY_SERVICE_ID,
                    operator=GREEDY_OPERATOR_NAME,
                    max_price=GREEDY_MAX_PRICE
                )
                if number_response.get('status') != 'new': # или другое поле успеха
                    logger.error(f"Не удалось получить номер через GreedySMS: {number_response}")
                    return False

                activation_id = number_response['id']
                phone_number = number_response['number']
                logger.info(f"Получен номер: {phone_number}, ID активации: {activation_id}")

                # 2. Отправить номер на OfferUp
                logger.debug(f"Отправка номера {phone_number} на OfferUp...")
                change_phone_response = await self.offerup_api.change_phone_number(phone_number=phone_number)
                if 'errors' in change_phone_response:
                    logger.error(f"Ошибка при отправке номера на OfferUp: {change_phone_response}")
                    return False

                reference_id = change_phone_response.get('data', {}).get('changePhoneNumber', {}).get('referenceId')
                if not reference_id:
                     logger.error("Не удалось получить referenceId после отправки номера.")
                     return False

                # 3. Ждём SMS
                max_attempts = 10
                for attempt in range(max_attempts):
                    logger.debug(f"Попытка {attempt + 1}/{max_attempts} получить SMS...")
                    status_response = await sms_client.get_status(activation_id=activation_id)
                    status = status_response.get('status')
                    if status == 'success' and 'code' in status_response:
                        otp_code = status_response['code']
                        logger.info(f"Получен OTP-код: {otp_code}")
                        # 4. Подтвердить номер с OTP
                        logger.debug(f"Подтверждение номера {phone_number} с OTP {otp_code}...")
                        confirm_response = await self.offerup_api.change_phone_number_confirm(
                            otp=otp_code,
                            reference_id=reference_id,
                            phone_number=phone_number
                        )
                        if 'errors' in confirm_response:
                            logger.error(f"Ошибка при подтверждении номера: {confirm_response}")
                            return False
                        logger.info("Номер успешно подтверждён.")
                        return True
                    elif status in ['timeout', 'banned', 'canceled']:
                        logger.error(f"Статус активации {status}, номер: {phone_number}.")
                        return False
                    else:
                        # Статус 'waiting' или 'used' или 'delay'
                        logger.debug(f"Статус активации: {status}. Ожидание...")
                        await asyncio.sleep(15) # Ждём 15 секунд перед следующей проверкой

                logger.error(f"Не дождались SMS-кода для номера {phone_number} за {max_attempts * 15} секунд.")
                return False

            except Exception as e:
                logger.error(f"Ошибка при верификации телефона через GreedySMS: {e}")
                return False

    @staticmethod
    async def _save_account_to_file(
            email: str,
        password: str,
        jwt_token: str,
        refresh_token: str,
        user_id: str,
        pasta: list,
        user_agent: str,
        browser_user_agent: str,
        proxy: Optional[str],
        session_id: str,
        device_id: str,
        advertising_id: str,
        anymessage_email_id: Optional[int],
        email_verified: bool,
        phone_verified: bool
    ):
        """
        Сохраняет данные аккаунта в JSON-файл.
        """
        import os
        from config import ACCOUNTS_DIR
        # Используем email как имя файла, экранируя недопустимые символы
        filename = f"{email.replace('@', '_at_').replace('.', '_dot_')}.json"
        filepath = os.path.join(ACCOUNTS_DIR, filename)

        account_data = {
            "email": email,
            "password": password,
            "jwt_token": jwt_token,
            "refresh_token": refresh_token,
            "user_id": user_id,
            "pasta": pasta,
            "user_agent": user_agent,
            "browser_user_agent": browser_user_agent,
            "proxy": proxy,
            "session_id": session_id,
            "device_id": device_id,
            "advertising_id": advertising_id,
            "anymessage_email_id": anymessage_email_id,
            "email_verified": email_verified,
            "phone_verified": phone_verified
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(account_data, f, ensure_ascii=False, indent=4)
            logger.info(f"Файл аккаунта сохранён: {filepath}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла аккаунта {filepath}: {e}")