import asyncio
import os
from typing import List, Tuple

import config
from app.core.database import get_processed_count
from app.offerup_account import OfferUpAccount


async def check_inbox():
    print("Инициализация аккаунтов")
    accounts: List[Tuple[str, OfferUpAccount]] = []

    for dir_ in (config.ACCOUNTS_DIR, config.ARCHIVE_ACCOUNTS_DIR, config.LIMIT_OUT_ACCOUNTS_DIR):
        dir_name = dir_.split("/")[-1]
        for filename in os.listdir(dir_):
            if filename.endswith(".json"):
                print(f"Загрузка аккаунта: {filename}")
                filepath = os.path.join(config.ACCOUNTS_DIR, filename)
                if account := OfferUpAccount.load_from_file(filepath):
                    account.processed = await get_processed_count(account.email)
                    accounts.append((dir_name, account))


    print(f"Загружено аккаунтов: {len(accounts)}")
    print("\n-----------------------------------------\n")

    for dir_name, account in accounts:
        try:
            inbox_response = await account.api.get_unread_alert_count()
        except Exception as e:
            print(f"Ошибка {e.__class__.__name__} при запросе входящих на аккаунте {account.email}: {e}")
            continue
        try:
            inbox_messages = inbox_response.get("data", {}).get("unreadNotificationCount", {}).get("inbox", inbox_response)
            print(f"[{dir_name}] {account.email} - Отписано: {account.processed}, Входящие: {inbox_messages}")
        except AttributeError:
            pass
        finally:
            await account.api.close()


if __name__ == "__main__":
    asyncio.run(check_inbox())