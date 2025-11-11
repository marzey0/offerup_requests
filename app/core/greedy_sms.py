# app/core/greedy_sms.py
import aiohttp
from typing import Optional, Dict, Any

from config import GREEDY_API_KEY


class GreedySMSClient:
    """
    Асинхронный клиент для взаимодействия с API GreedySMS.
    Предоставляет методы для получения баланса, работы с активациями и т.д.
    Использует aiohttp.ClientSession и реализует асинхронный контекстный менеджер.
    """

    def __init__(self, auth_token: str = GREEDY_API_KEY):
        """
        Инициализирует клиент GreedySMSClient.

        Args:
            auth_token (str): Токен аутентификации.
        """
        self.base_url = "https://api.greedy-sms.com"
        self.auth_token = auth_token
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

    def _get_headers(self) -> Dict[str, str]:
        """
        Возвращает стандартные заголовки для запросов к API.
        """
        headers = {
            "Content-Type": "application/json"
        }
        if self.auth_token:
            headers["x-api-key"] = self.auth_token
        return headers

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Внутренний метод для выполнения HTTP-запросов к API.

        Args:
            method (str): HTTP-метод (GET, POST).
            endpoint (str): Конечная точка API (например, '/users/getMe').
            data (Optional[Dict[str, Any]]): Данные для отправки в теле запроса (для POST).

        Returns:
            Dict[str, Any]: JSON-ответ от API.

        Raises:
            aiohttp.ClientResponseError: Если статус ответа != 200.
            aiohttp.ClientError: При других ошибках клиента.
        """
        if not self._session:
            raise RuntimeError("Client session is not open. Use 'async with' statement.")

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            async with self._session.request(method, url, headers=headers, json=data) as response:
                if response.status != 200:
                    text = await response.text()
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Request failed with status {response.status}: {text}"
                    )
                return await response.json()
        except aiohttp.ClientResponseError:
            raise  # Переподнимаем исключение, чтобы вызывающий код мог его обработать
        except aiohttp.ClientError as e:
            raise e  # Переподнимаем исключения клиента

    async def get_balance(self) -> Dict[str, Any]:
        """
        Получает информацию о пользователе, включая баланс.

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о пользователе.
            Пример:
            {
              "id": "string",
              "balance": 1,
              ...
            }
        """
        return await self._make_request("GET", "/users/getMe")

    async def get_operators(self, country: int) -> Dict[str, Any]:
        """
        Получает список операторов для указанной страны.

        Args:
            country (int): Идентификатор страны.

        Returns:
            Dict[str, Any]: JSON-ответ с информацией об операторах.
            Пример:
            {
              "operators": [...]
            }
        """
        data = {"country": country}
        return await self._make_request("POST", "/activations/getOperators", data)

    async def get_countries(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Получает список стран.

        Args:
            page (int): Номер страницы (по умолчанию 1).
            page_size (int): Количество элементов на странице (по умолчанию 10).

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о странах.
            Пример:
            {
              "countries": [...],
              "total": 100
            }
        """
        data = {"page": page, "pageSize": page_size}
        return await self._make_request("POST", "/activations/getCountries", data)

    async def get_services(self, country: int, page: int = 1, language: str = "rus", page_size: int = 10) -> Dict[str, Any]:
        """
        Получает список сервисов для указанной страны.

        Args:
            country (int): Идентификатор страны.
            page (int): Номер страницы (по умолчанию 1).
            language (str): Язык ("rus" или "eng", по умолчанию "rus").
            page_size (int): Количество элементов на странице (по умолчанию 10).

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о сервисах.
            Пример:
            {
              "services": [...],
              "total": 50
            }
        """
        data = {"country": country, "page": page, "language": language, "pageSize": page_size}
        return await self._make_request("POST", "/activations/getServices", data)

    async def get_prices(self, country: int, service: str, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Получает цены на активации для указанной страны и сервиса.

        Args:
            country (int): Идентификатор страны.
            service (str): Код сервиса (например, "telegram").
            page (int): Номер страницы (по умолчанию 1).
            page_size (int): Количество элементов на странице (по умолчанию 10).

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о ценах.
            Пример:
            {
              "prices": [...],
              "total": 30
            }
        """
        data = {"country": country, "service": service, "page": page, "pageSize": page_size}
        return await self._make_request("POST", "/activations/getPrices", data)

    async def get_numbers_status(self, country: int, operator: str = "", page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Получает количество доступных номеров для указанной страны и оператора.

        Args:
            country (int): Идентификатор страны.
            operator (str): Код оператора (необязательно).
            page (int): Номер страницы (по умолчанию 1).
            page_size (int): Количество элементов на странице (по умолчанию 10).

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о статусе номеров.
            Пример:
            {
              "status": [...],
              "total": 1000
            }
        """
        data = {"country": country, "operator": operator, "page": page, "pageSize": page_size}
        return await self._make_request("POST", "/activations/getNumbersStatus", data)

    async def get_top_countries_by_service(self, service: str, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Получает топ стран по популярности для указанного сервиса.

        Args:
            service (str): Код сервиса (например, "telegram").
            page (int): Номер страницы (по умолчанию 1).
            page_size (int): Количество элементов на странице (по умолчанию 10).

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о топ-странах.
            Пример:
            {
              "topCountries": [...],
              "total": 10
            }
        """
        data = {"service": service, "page": page, "pageSize": page_size}
        return await self._make_request("POST", "/activations/getTopCountriesByService", data)

    async def get_status(self, activation_id: int) -> Dict[str, Any]:
        """
        Получает статус активации по её идентификатору.

        Args:
            activation_id (int): Идентификатор активации.

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о статусе активации.
            Пример:
            {
              "status": "string",
              "number": "string",
              "code": "string" // если доступен
            }
        """
        data = {"activationId": activation_id}
        return await self._make_request("POST", "/activations/getStatus", data)

    async def get_history(self, active: bool = True, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Получает историю активаций пользователя.

        Args:
            active (bool): Фильтр по активным/неактивным (по умолчанию True).
            page (int): Номер страницы (по умолчанию 1).
            page_size (int): Количество элементов на странице (по умолчанию 10).

        Returns:
            Dict[str, Any]: JSON-ответ с информацией об активациях.
            Пример:
            {
              "history": [...],
              "total": 20
            }
        """
        data = {"active": active, "page": page, "pageSize": page_size}
        return await self._make_request("POST", "/activations/getHistory", data)

    async def get_number(self, country: int, service: str, operator: str = "", activation_type: int = 0, language: str = "rus", max: bool = False, max_price: int = 0) -> Dict[str, Any]:
        """
        Покупает (получает) номер для активации.

        Args:
            country (int): Идентификатор страны.
            service (str): Код сервиса (например, "telegram").
            operator (str): Код оператора (необязательно).
            activation_type (int): Тип активации (0=SMS, 1=номер, 2=голос, по умолчанию 0).
            language (str): Язык (по умолчанию "rus").
            max (bool): Использовать максимальную цену (по умолчанию False).
            max_price (int): Максимальная цена (по умолчанию 0).

        Returns:
            Dict[str, Any]: JSON-ответ с информацией о номере и активации.
            Пример:
            {
              "id": 123,
              "number": "79123456789",
              "status": "new"
            }
        """
        data = {
            "country": country,
            "service": service,
            "operator": operator,
            "activationType": activation_type,
            # "language": language,
            "max": max,
            "maxPrice": max_price
        }
        return await self._make_request("POST", "/activations/getNumber", data)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

# --- Пример использования ---
# async def main():
#     async with GreedySMSClient(auth_token="019a5dfd-8070-7000-ad06-126537eebf4f") as client:
#         try:
#
#             operators = await client.get_operators(187)
#             with open("greedy_docs/greedy_us_operators.json", "w", encoding="utf-8") as file:
#                 file.write(json.dumps(operators, ensure_ascii=False, indent=4))
#
#         except aiohttp.ClientResponseError as e:
#             print(f"\nHTTP ошибка: {e}")
#         except Exception as e:
#             print(f"\nПроизошла ошибка: {e}")
#
#
# if __name__ == "__main__":
#     import asyncio
#     import json
#     asyncio.run(main())