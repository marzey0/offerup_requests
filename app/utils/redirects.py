import logging

import aiohttp
import asyncio

from app.utils.fancy_replacer import replace_with_fancy
from app.utils.text_formatter import generate_random_string
from config import REDIRECTS_API_KEY, REDIRECTS_DOMAIN


logger = logging.getLogger(__name__)


def generate_fish_redirect_url():
    return f"{replace_with_fancy(REDIRECTS_DOMAIN)}/{generate_random_string(length=6)}"


async def set_redirect(target_url: str, redirect_alias: str, delay: int) -> bool:
    if delay > 0:
        await asyncio.sleep(delay)
    url = f"http://{REDIRECTS_DOMAIN}/add_redirect.php"
    headers = {
        'Authorization': f'Bearer {REDIRECTS_API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'to': target_url,
        'from': redirect_alias
    }
    # print(f"URL: {url}")
    # print(f"Data: {data}")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            logger.info(f"Ответ утановки редиректа: {response.status} / {await response.text()}")
            return response.status == 200


# if __name__ == '__main__':
#     import asyncio
#     asyncio.run(set_redirect('https://google.com', "test"))