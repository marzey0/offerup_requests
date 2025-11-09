# app/utils/account_manager.py
import json
import logging
import os
from typing import Dict, Any, Optional, List
from app.core.offerup_api import OfferUpAPI
from config import ACCOUNTS_DIR

logger = logging.getLogger(__name__)


class AccountManager:
    """
    Класс для управления аккаунтами: загрузка, сохранение, предоставление экземпляров OfferUpAPI.
    """

    def __init__(self, accounts_dir: str = ACCOUNTS_DIR):
        self.accounts_dir = accounts_dir
        self.accounts_data: Dict[str, Any] = {}
        self.api_instances: Dict[str, OfferUpAPI] = {}
        self._load_accounts()

    def _load_accounts(self):
        """
        Загружает все JSON-файлы аккаунтов из папки accounts_dir.
        """
        logger.info(f"Загрузка аккаунтов из {self.accounts_dir}...")

        for filename in os.listdir(self.accounts_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.accounts_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Используем email или user_id как уникальный ключ
                    key = data.get('email') or data.get('user_id')
                    if key:
                        self.accounts_data[key] = data
                        logger.debug(f"Загружен аккаунт: {key}")
                    else:
                        logger.warning(f"Файл {filename} не содержит 'email' или 'user_id'. Пропущен.")

                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка чтения JSON из {filepath}: {e}")
                except Exception as e:
                    logger.error(f"Неизвестная ошибка при загрузке {filepath}: {e}")

        logger.info(f"Загружено {len(self.accounts_data)} аккаунтов.")

    def _save_account(self, key: str):
        """
        Сохраняет данные аккаунта обратно в JSON-файл.
        """
        data = self.accounts_data.get(key)
        if not data:
            logger.error(f"Нет данных для сохранения аккаунта с ключом {key}")
            return

        filename = f"{key}.json"
        filepath = os.path.join(self.accounts_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.debug(f"Аккаунт {key} сохранён в {filepath}.")
        except Exception as e:
            logger.error(f"Ошибка сохранения аккаунта {key} в {filepath}: {e}")

    def get_api_instance(self, key: str) -> Optional[OfferUpAPI]:
        """
        Возвращает экземпляр OfferUpAPI, инициализированный данными аккаунта.
        Если экземпляр уже создан, возвращает его из кэша.
        """
        if key in self.api_instances:
            logger.debug(f"Возвращаю кэшированный экземпляр API для {key}.")
            return self.api_instances[key]

        account_data = self.accounts_data.get(key)
        if not account_data:
            logger.error(f"Нет данных аккаунта для ключа {key}")
            return None

        # Извлекаем pasta из JSON
        pasta = account_data.get('pasta', [])
        if not pasta:
            logger.warning(f"У аккаунта {key} нет 'pasta' в JSON. Используется пустой список.")

        # Извлекаем proxy из JSON, fallback на None
        proxy = account_data.get('proxy')

        # Создаём новый экземпляр OfferUpAPI с прокси из JSON
        api_instance = OfferUpAPI(proxy=proxy)

        # Инициализируем его данными из JSON
        api_instance._session_id = account_data.get('session_id', api_instance._session_id)
        api_instance._device_id = account_data.get('device_id', api_instance._device_id)
        api_instance._user_agent, api_instance._browser_user_agent = account_data.get('user_agent', api_instance._user_agent), account_data.get('browser_user_agent', api_instance._browser_user_agent)
        api_instance._advertising_id = account_data.get('advertising_id', api_instance._advertising_id)
        # Устанавливаем pasta как атрибут экземпляра
        api_instance._pasta = pasta
        # Устанавливаем _anymessage_email_id, если есть
        api_instance._anymessage_email_id = account_data.get('anymessage_email_id', api_instance._anymessage_email_id)

        # Устанавливаем токены и ID, если они есть
        jwt_token = account_data.get('jwt_token')
        refresh_token = account_data.get('refresh_token')
        user_id = account_data.get('user_id')

        if jwt_token and refresh_token:
            api_instance.update_auth_tokens(jwt_token, refresh_token)
        if user_id:
            api_instance.update_session_data(user_id)

        # Кэшируем экземпляр
        self.api_instances[key] = api_instance
        logger.debug(f"Создан и кэширован экземпляр API для {key}.")
        return api_instance

    def update_account_tokens(self, key: str, jwt_token: str, refresh_token: str):
        """
        Обновляет токены в памяти и в JSON-файле аккаунта.
        """
        if key in self.accounts_data:
            old_jwt = self.accounts_data[key].get('jwt_token')
            if old_jwt != jwt_token:
                logger.info(f"Обновление токенов для аккаунта {key}.")
            self.accounts_data[key]['jwt_token'] = jwt_token
            self.accounts_data[key]['refresh_token'] = refresh_token
            self._save_account(key)

            # Если экземпляр API уже создан, обновляем его токены
            if key in self.api_instances:
                self.api_instances[key].update_auth_tokens(jwt_token, refresh_token)

    def get_all_account_keys(self) -> List[str]:
        """
        Возвращает список всех ключей (email или user_id) загруженных аккаунтов.
        """
        return list(self.accounts_data.keys())

    def get_next_account_key(self) -> Optional[str]:
        """
        Простая реализация: возвращает следующий аккаунт по кругу.
        Можно расширить логику (например, по статусу, количеству использований и т.п.).
        """
        keys = self.get_all_account_keys()
        if not keys:
            logger.warning("Нет доступных аккаунтов.")
            return None
        # Просто возвращаем первый, можно добавить логику переключения
        return keys[0] if len(keys) == 1 else keys[hash(str(keys)) % len(keys)] # Пример "кругового" выбора