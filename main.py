import asyncio
import json
from typing import Dict, Any

import aiohttp

from offerup_api import OfferUpAPI


import asyncio
import json
from typing import Dict, Any
import aiohttp # Убедитесь, что aiohttp импортирован


async def example_register_verify_email_and_phone(api_client: OfferUpAPI, email: str, name: str, password: str, phone_number: str):
    """
    Пример процесса регистрации нового пользователя, подтверждения email и номера телефона.

    Args:
        api_client (OfferUpAPI): Экземпляр клиента OfferUpAPI.
        email (str): Email для регистрации.
        name (str): Имя пользователя.
        password (str): Пароль.
        phone_number (str): Номер телефона для верификации (только цифры).
    """
    print("--- Начало процесса регистрации, верификации email и телефона ---")

    # 1. Получение UserContext (возможно, требуется для инициализации сессии или определения локации)
    # Используем примерные данные из предыдущих запросов
    viewport_size = {"width": 540, "height": 912}
    search_location = {"latitude": 40.7360524, "longitude": -73.9800987, "zipcode": "10010"}
    print("1. Получение UserContext...")
    try:
        context_response = await api_client.get_user_context(viewport_size, search_location)
        print(f"   Raw response: {context_response}") # Для отладки

        if context_response is None:
            print("   ОШИБКА: Сервер вернул 'None' на запрос UserContext. Это может указывать на проблемы с доступом (например, гео-ограничения). Проверьте ваше местоположение или настройки сети (VPN/Proxy).")
            return # Прерываем выполнение

        # Проверка на наличие ожидаемой структуры данных
        if 'data' not in context_response or 'userContext' not in context_response['data']:
             print(f"   ОШИБКА: Неожиданная структура ответа UserContext: {context_response}")
             return

        print(f"   UserContext получен. Пример ключа: {context_response['data']['userContext']['userContext'][0]['key']}")
        api_client.update_user_context(context_response['data']['userContext']['userContext'])
    except aiohttp.ClientResponseError as e:
        print(f"   HTTP Ошибка при получении UserContext: {e.status} - {e.message}")
        if e.status == 403 or e.status == 451: # Часто используются для гео-блоков
            print("   Возможно, OfferUp заблокирован в вашем регионе.")
        return
    except Exception as e:
        print(f"   Неожиданная ошибка при получении UserContext: {e}")
        return

    # 2. Регистрация
    print(f"2. Регистрация пользователя: {email}")
    try:
        signup_response = await api_client.signup(email, name, password)
        print(f"   Raw signup response: {signup_response}") # Для отладки

        if signup_response is None:
            print("   ОШИБКА: Сервер вернул 'None' на запрос Signup.")
            return

        if 'data' not in signup_response or 'signup' not in signup_response['data']:
             print(f"   ОШИБКА: Неожиданная структура ответа Signup: {signup_response}")
             return

        print(f"   Регистрация успешна. User ID: {signup_response['data']['signup']['id']}")
        print(f"   Email Verified (initial): {signup_response['data']['signup']['profile']['isEmailVerified']}")

        # Извлечение токенов и ID из ответа signup
        user_id = signup_response['data']['signup']['id']
        jwt_token = signup_response['data']['signup']['sessionToken']['value']
        refresh_token = signup_response['data']['signup']['refreshToken']['value']
        device_id = api_client._device_id

        # Обновление клиента токенами и ID
        api_client.update_auth_tokens(jwt_token, refresh_token)
        api_client.update_session_data(api_client._session_id, str(user_id), device_id)

        print("   Токены и ID обновлены в клиенте.")
    except aiohttp.ClientResponseError as e:
        print(f"   HTTP Ошибка при регистрации: {e.status} - {e.message}")
        if e.status == 403 or e.status == 451:
            print("   Возможно, OfferUp заблокирован в вашем регионе.")
        return
    except Exception as e:
        print(f"   Ошибка при регистрации: {e}")
        return # Прерываем выполнение

    # 3. Повторный вызов ChangeEmail (после получения токенов)
    print(f"3. Повторный вызов ChangeEmail: {email} (после регистрации)")
    try:
        change_email_response = await api_client.change_email(user_id, email)
        print(f"   Raw change email response: {change_email_response}") # Для отладки

        if change_email_response is None:
            print("   ОШИБКА: Сервер вернул 'None' на запрос ChangeEmail.")
            # В реальности это может быть не фатальной ошибкой, просто попытка обновить.
            # Продолжим выполнение.
        else:
            if change_email_response.get('data', {}).get('changeEmail'):
                print("   Email успешно обновлён через ChangeEmail.")
            else:
                print("   ChangeEmail не вернул успешный результат.")
    except aiohttp.ClientResponseError as e:
        print(f"   HTTP Ошибка при ChangeEmail: {e.status} - {e.message}")
        # Продолжим, так как email уже был указан при регистрации
    except Exception as e:
        print(f"   Ошибка при ChangeEmail: {e}")
        # Продолжим, так как email уже был указан при регистрации

    # 4. Изменение номера телефона (инициация)
    print(f"4. Инициация изменения номера телефона: {phone_number}")
    try:
        phone_change_response = await api_client.change_phone_number(phone_number)
        print(f"   Raw phone change response: {phone_change_response}") # Для отладки

        if phone_change_response is None:
            print("   ОШИБКА: Сервер вернул 'None' на запрос ChangePhoneNumber.")
            return

        if 'data' not in phone_change_response or 'changePhoneNumber' not in phone_change_response['data']:
             print(f"   ОШИБКА: Неожиданная структура ответа ChangePhoneNumber: {phone_change_response}")
             return

        reference_id = phone_change_response['data']['changePhoneNumber']['referenceId']
        print(f"   Запрос на изменение номера отправлен. Reference ID: {reference_id}")
    except aiohttp.ClientResponseError as e:
        print(f"   HTTP Ошибка при инициации изменения номера: {e.status} - {e.message}")
        if e.status == 406:
            error_body = e.message
            print(f"   Тело ошибки 406: {error_body}")
        return
    except Exception as e:
        print(f"   Ошибка при инициации изменения номера телефона: {e}")
        reference_id = None
        if not reference_id:
             print("   reference_id не получен, невозможно продолжить верификацию.")
             return

    # 5. Подтверждение номера телефона (псевдо-код)
    otp_code = "408218" # Замените на реальный OTP
    print(f"5. Подтверждение номера телефона с OTP: {otp_code}")
    try:
        confirm_response = await api_client.change_phone_number_confirm(
            otp=otp_code,
            reference_id=reference_id,
            phone_number=phone_number
        )
        print(f"   Raw confirm response: {confirm_response}") # Для отладки

        if confirm_response is None:
            print("   ОШИБКА: Сервер вернул 'None' на запрос ChangePhoneNumberConfirm.")
            return

        if 'data' not in confirm_response or 'changePhoneNumberConfirm' not in confirm_response['data']:
             print(f"   ОШИБКА: Неожиданная структура ответа ChangePhoneNumberConfirm: {confirm_response}")
             return

        if confirm_response.get('data', {}).get('changePhoneNumberConfirm'):
            print("   Номер телефона успешно подтвержден!")
        else:
            print("   Подтверждение номера не удалось.")
    except aiohttp.ClientResponseError as e:
        print(f"   HTTP Ошибка при подтверждении номера: {e.status} - {e.message}")
        return
    except Exception as e:
        print(f"   Ошибка при подтверждении номера телефона: {e}")
        return

    # 6. Получение обновленных данных профиля (опционально)
    print("6. Получение обновленных данных профиля...")
    try:
        profile_response = await api_client.get_auth_user()
        print(f"   Raw profile response: {profile_response}") # Для отладки

        if profile_response is None:
            print("   ОШИБКА: Сервер вернул 'None' на запрос GetAuthUser.")
            return

        if 'data' not in profile_response or 'me' not in profile_response['data']:
             print(f"   ОШИБКА: Неожиданная структура ответа GetAuthUser: {profile_response}")
             return

        profile = profile_response['data']['me']['profile']
        print(f"   Профиль: {profile['name']}, Email Verified: {profile['isEmailVerified']}, Phone Verified: {profile['isPhoneNumberVerified']}")
    except aiohttp.ClientResponseError as e:
        print(f"   HTTP Ошибка при получении профиля: {e.status} - {e.message}")
        return
    except Exception as e:
        print(f"   Ошибка при получении профиля: {e}")

    print("--- Процесс регистрации и верификации завершен ---")




# --- Пример использования ---
async def main():
    # Создаем сессию aiohttp и передаем её в API клиент
    # Важно: установите device_id и session_id, если они не по умолчанию и известны
    async with aiohttp.ClientSession() as session:
        api = OfferUpAPI(session=session)
        # Установим device_id и session_id, как в ваших примерах
        api.update_session_data("14b2640b-86d9-4b81-8efb-31b781c5e467", "166279441", "719062d0720c1502")
        api.update_user_context({}) # Инициализируем пустым, будет обновлено

        # Замените на реальные данные
        email = "mpod5uwx@gmail.com"
        name = "ibjnefodsdmfk"
        password = "securpassword123"
        phone_number = "4582659344"

        await example_register_verify_email_and_phone(api, email, name, password, phone_number)

# Запуск примера
asyncio.run(main())