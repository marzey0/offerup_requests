# app/core/anymessage.py
import aiohttp
from typing import Optional, Dict, Any, Union

from config import ANYMESSAGE_API_KEY, ANYMESSAGE_EMAIL_SITE, ANYMESSAGE_EMAIL_DOMAIN


class AnyMessageAPIError(Exception):
    """Базовое исключение для ошибок, специфичных для API AnyMessage."""
    pass


class AnyMessageClient:
    """
    Асинхронный клиент для взаимодействия с API AnyMessage.
    Предоставляет методы для работы с балансом, заказом и получением email-активаций.
    Использует aiohttp.ClientSession и реализует асинхронный контекстный менеджер.
    """

    def __init__(self, token: str = ANYMESSAGE_API_KEY):
        """
        Инициализирует клиент AnyMessageClient.

        Args:
            token (str): Токен аутентификации пользователя.
        """
        self.base_url = "https://api.anymessage.shop"
        self.token = token
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """
        Асинхронный вход в контекстный менеджер. Создает aiohttp.ClientSession.
        """
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Асинхронный выход из контекстного менеджера. Закрывает aiohttp.ClientSession.
        """
        if self._session and not self._session.closed:
            await self._session.close()

    def _build_url(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Вспомогательный метод для построения полного URL с токеном и параметрами.
        """
        full_params = {"token": self.token}
        if params:
            full_params.update(params)
        # aiohttp сам правильно кодирует параметры
        param_str = "&".join(f"{k}={v}" for k, v in full_params.items() if v is not None)
        return f"{self.base_url}{endpoint}?{param_str}"

    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], str]:
        """
        Внутренний метод для выполнения HTTP-запросов к API.

        Args:
            method (str): HTTP-метод (GET).
            endpoint (str): Конечная точка API (например, '/user/balance').
            params (Optional[Dict[str, Any]]): Параметры для добавления к URL.

        Returns:
            Union[Dict[str, Any], str]: JSON-ответ от API или строка (например, HTML для preview).

        Raises:
            AnyMessageAPIError: Если статус ответа != 200 или если API возвращает {"status": "error"}.
            aiohttp.ClientError: При других ошибках клиента.
        """
        if not self._session:
            raise RuntimeError("Client session is not open. Use 'async with' statement.")

        url = self._build_url(endpoint, params)

        try:
            async with self._session.request(method, url) as response:
                if response.status != 200:
                    text = await response.text()
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Request failed with status {response.status}: {text}"
                    )

                # Для метода get_message с preview=1 ожидается HTML
                if params and params.get('preview') == '1':
                    return await response.text()

                # Для остальных - JSON
                json_response = await response.json()
                if json_response.get("status") == "error" and json_response.get("value") != "wait message":
                    raise AnyMessageAPIError(f"API Error: {json_response.get('value', 'Unknown error')}")
                return json_response

        except aiohttp.ClientResponseError:
            raise  # Переподнимаем исключение, чтобы вызывающий код мог его обработать
        except aiohttp.ClientError as e:
            raise e  # Переподнимаем исключения клиента
        except ValueError:  # json.decoder.JSONDecodeError наследует от ValueError
            # Если ожидается JSON, но получена не-JSON строка (например, при ошибке)
            text = await response.text()
            raise AnyMessageAPIError(f"Invalid JSON response: {text}")

    async def get_balance(self) -> Dict[str, Any]:
        """
        Получает баланс пользователя.

        Args:
            (Метод не принимает дополнительных аргументов, токен передается автоматически)

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о балансе.
            Пример успешного ответа:
            {
              "status": "success",
              "balance": "1.0"
            }
            Пример ошибочного ответа:
            {
              "status": "error",
              "value": "token"
            }
        """
        return await self._make_request("GET", "/user/balance")

    async def emails_for_site(self, site: str) -> Dict[str, Any]:
        """
        Возвращает количество доступных email-адресов для указанного сайта.

        Args:
            site (str): Название сайта (например, 'instagram.com').

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о количестве.
            Пример успешного ответа:
            {
              "status": "success",
              "data": {
                ...
              }
            }
            Пример ошибочного ответа:
            {
              "status": "error",
              "value": "token"  // или "site"
            }
        """
        params = {"site": site}
        return await self._make_request("GET", "/email/quantity", params)

    async def order_email(self, site: str, domain: str, ex: Optional[str] = None, subject: Optional[str] = None) -> Dict[str, Any]:
        """
        Заказывает новый email-адрес для указанного сайта.

        Args:
            site (str): Название сайта (например, 'instagram.com').
            domain (str): Домен для email (например, 'gmx').
            ex (Optional[str]): Дополнительный параметр (опционально).
            subject (Optional[str]): Тема письма (опционально).

        Returns:
            Dict[str, Any]: JSON-ответ с ID и email.
            Пример успешного ответа:
            {
              "status": "success",
              "id": "1001",
              "email": "user123@gmx.com"
            }
            Пример ошибочного ответа:
            {
              "status": "error",
              "value": "token"  // или "site"
            }
        """
        params = {"site": site, "domain": domain}
        if ex is not None:
            params["ex"] = ex
        if subject is not None:
            params["subject"] = subject
        return await self._make_request("GET", "/email/order", params)

    async def get_message(self, email_id: str, preview: bool = False) -> Union[Dict[str, Any], str]:
        """
        Получает содержимое письма по ID заказа email.

        Args:
            email_id (str): ID заказа email.
            preview (bool): Если True, возвращает чистый HTML содержимого письма. По умолчанию False.

        Returns:
            Union[Dict[str, Any], str]: JSON-ответ с сообщением или HTML-строка, если preview=True.
            Пример успешного JSON-ответа (preview=False):
            {
              "status": "success",
              "message": "..."
            }
            Пример успешного HTML-ответа (preview=True):
            "..."
            Пример ошибочного ответа:
            {
              "status": "error",
              "value": "token"  // или "id"
            }
        """
        params = {"id": email_id}
        if preview:
            params["preview"] = "1"
        return await self._make_request("GET", "/email/getmessage", params)

    async def reorder_email(self, email_id: Optional[str] = None, email: Optional[str] = None, site: Optional[str] = None) -> Dict[str, Any]:
        """
        Запрашивает новый email для существующего заказа или для указанного email и сайта.

        Args:
            email_id (Optional[str]): ID заказа email (взаимоисключающий с email и site).
            email (Optional[str]): Существующий email (взаимоисключающий с id).
            site (Optional[str]): Название сайта (взаимоисключающий с id).

        Returns:
            Dict[str, Any]: JSON-ответ с новым ID и email.
            Пример успешного ответа:
            {
              "status": "success",
              "id": "1002",
              "email": "user456@gmx.com"
            }
            Пример ошибочного ответа:
            {
              "status": "error",
              "value": "token"  // или "id", "email", "site"
            }
        """
        # Проверяем, что предоставлены либо id, либо email и site
        if (email_id is not None) and (email is None and site is None):
            params = {"id": email_id}
        elif (email_id is None) and (email is not None and site is not None):
            params = {"email": email, "site": site}
        else:
            raise ValueError("Either provide 'id' OR both 'email' and 'site'.")

        return await self._make_request("GET", "/email/reorder", params)

    async def cancel_email(self, email_id: str) -> Dict[str, Any]:
        """
        Отменяет активацию email по ID заказа.

        Args:
            email_id (str): ID заказа email.

        Returns:
            Dict[str, Any]: JSON-ответ с подтверждением отмены.
            Пример успешного ответа:
            {
              "status": "success",
              "value": "activation canceled"
            }
            Пример ошибочного ответа:
            {
              "status": "error",
              "value": "token"  // или "id"
            }
        """
        params = {"id": email_id}
        return await self._make_request("GET", "/email/cancel", params)


# --- Пример использования ---
# async def main():
#     """
#     Пример тестирования методов клиента через асинхронный контекстный менеджер.
#     """
#     # Замените на реальный токен
#     async with AnyMessageClient(token=ANYMESSAGE_API_KEY) as client:
#         try:
#             order_response = await client.order_email(site=ANYMESSAGE_EMAIL_SITE, domain=ANYMESSAGE_EMAIL_DOMAIN)
#             email = order_response['email']
#             anymessage_email_id = order_response['id']
#             print(f"Заказан email: {email}, ID: {anymessage_email_id}")
#             print("Ожидаю письмо... Ссылка подтверждения будет выдана автоматически!")
#
#             while True:
#                 message_response = await client.get_message(email_id=anymessage_email_id)
#                 message_status = message_response.get('status')
#                 if message_status == 'error' and message_response.get('value') == 'wait message':
#                     await asyncio.sleep(3)
#                     continue
#                 elif message_status == 'success':
#                     message_content = message_response.get('message', '')
#                     match = re.search(
#                         r'href=[\'"]([^\'"]*offerup\.com[^\s\'"]*confirm-email[^\s\'"]*)[\'"]',
#                         message_content
#                     )
#                     if match:
#                         link_url = match.group(1).replace('&amp;', '&')  # Заменяем &amp; на &
#                         print(f"Найден URL в письме: {link_url}")
#                         break
#
#                 print(f"Что-то пошло не так... {message_response=}")
#                 break
#
#         except AnyMessageAPIError as e:
#             print(f"\nAPI ошибка: {e}")
#         except Exception as e:
#             print(f"\nПроизошла ошибка: {e}")
#
#
# if __name__ == "__main__":
#     import asyncio
#     import re
#     asyncio.run(main())