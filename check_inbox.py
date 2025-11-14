import asyncio
import os

import config
from app.core.database import get_processed_count
from app.offerup_account import OfferUpAccount


async def check_inbox():
    print("Инициализация аккаунтов")
    accounts = []

    accounts_dir = config.ACCOUNTS_DIR
    for filename in os.listdir(accounts_dir):
        print(f"Загрузка аккаунта: {filename}")
        if filename.endswith(".json"):
            filepath = os.path.join(accounts_dir, filename)
            if account := OfferUpAccount.load_from_file(filepath):
                account.processed = await get_processed_count(account.email)
                accounts.append(account)

    print(f"Загружено аккаунтов: {len(accounts)}")
    print("\n-----------------------------------------\n")

    for account in accounts:
        try:
            inbox_response = await account.api.get_unread_alert_count()
        except Exception as e:
            print(f"Ошибка {e.__class__.__name__} при запросе входящих на аккаунте {account.email}: {e}")
            continue

        inbox_messages = inbox_response["data"]["unreadNotificationCount"]["inbox"]
        print(f"{account.email} - Отписано: {account.processed}, Входящие: {inbox_messages}")
        await account.api.close()


if __name__ == "__main__":
    asyncio.run(check_inbox())