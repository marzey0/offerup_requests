# app/parser.py
import asyncio
import datetime
import logging
from typing import Dict, Any, Optional, List, Tuple

from app.core.offerup_api import OfferUpAPI
from app.core.database import ad_exists, add_ad
from config import PARSER_DELAY, PARSER_CATEGORIES_EXCLUDED, PARSER_SEMAPHORE, DATABASE_PATH, PARSER_PROXY, CITIES

logger = logging.getLogger(__name__)


class OfferUpParser:
    def __init__(self, db_path: str = DATABASE_PATH, delay: int = PARSER_DELAY, max_concurrent_details: int = PARSER_SEMAPHORE):
        self.db_path = db_path
        self.delay = delay
        self.running = True  # Флаг для остановки из main.py
        self.offerup_api = OfferUpAPI(proxy=PARSER_PROXY)
        self.max_concurrent_details = max_concurrent_details # Максимальное количество одновременных запросов на детали
        self.details_semaphore = asyncio.Semaphore(self.max_concurrent_details)

        self.categories_cashed: List[Dict[str, str]] = []

    async def run(self):
        """
        Основной цикл парсера.
        """
        logger.info("Запуск компонента парсера.")
        while self.running:
            try:
                logger.debug("Начало цикла парсинга...")
                for city, coordinates in CITIES.items():
                    await self._parse_new_listings(city, coordinates)
                logger.debug(f"Цикл парсинга завершён. Пауза {self.delay} секунд.")
                await asyncio.sleep(self.delay)
            except Exception as e:
                logger.error(f"Неожиданная ошибка в цикле парсера: {e}")
                await asyncio.sleep(self.delay) # Пауза даже при ошибке

    async def _get_categories(self) -> List[Dict[str, str]]:
        try:
            if not self.categories_cashed:
                categories_response = await self.offerup_api.get_category_taxonomy()
                for category in categories_response.get('data', {}).get('getTaxonomy', {}).get('children', []):
                    if category['id'] in self.categories_cashed:
                        continue
                    if category['label'] in PARSER_CATEGORIES_EXCLUDED:
                        continue
                    self.categories_cashed.append({
                        'id': category['id'],
                        'label': category['label'],
                    })

        except Exception as e:
            logger.error(f"Произошла ошибка {e.__class__.__name__} при запросе категорий: {e}")

        return self.categories_cashed or [
            {'id': '1', 'label': 'category 1'},
            {'id': '2', 'label': 'category 2'},
            {'id': '3', 'label': 'category 3'},
            {'id': '4', 'label': 'category 4'},
            {'id': '6', 'label': 'category 5'},
            {'id': '7', 'label': 'category 6'},
        ]

    async def _fetch_listings_for_category(self, category_id: str, coordinates: Tuple[float, float]) -> Optional[List[Dict[str, Any]]]:
        """
        Получает *плитки* с объявлениями для указанной категории.
        Возвращает список плиток типа LISTING.
        """
        try:
            response = await self.offerup_api.get_new_listings_in_category(category_id, coordinates)
            listings_tiles = []
            modular_feed = response.get('data', {}).get('modularFeed', {})
            loose_tiles = modular_feed.get('looseTiles', [])
            modules = modular_feed.get('modules', [])

            # Проходим по looseTiles
            for tile in loose_tiles:
                if tile.get('tileType') == 'LISTING':
                    listings_tiles.append(tile)

            # Проходим по modules и их tiles
            for module in modules:
                if module.get('__typename') == 'ModularFeedModuleGrid':
                    grid_tiles = module.get('grid', {}).get('tiles', [])
                    for tile in grid_tiles:
                        if tile.get('tileType') == 'LISTING':
                            listings_tiles.append(tile)

            logger.debug(f"Получено {len(listings_tiles)} плиток объявлений для категории {category_id}.")
            return listings_tiles

        except Exception as e:
            logger.error(f"Ошибка при получении объявлений для категории {category_id}: {e}")
            return None

    async def _fetch_ad_details(self, ad_id: str) -> Optional[Dict[str, Any]]:
        """
        Асинхронно получает детали объявления через семафор.
        Проверяет, существует ли объявление в БД перед запросом.
        Возвращает словарь с ad_id, title, seller_id, ratings_count или None.
        """
        async with self.details_semaphore:
            # Проверяем, есть ли объявление в БД перед запросом деталей
            if await ad_exists(ad_id):
                # logger.debug(f"Объявление {ad_id} уже существует в БД, пропуск получения деталей.")
                return None

            try:
                listing_details = await self.offerup_api.get_item_detail_data_by_listing_id(ad_id)
                if not listing_details:
                    logger.warning(f"Не удалось получить детали для объявления {ad_id}.")
                    return None

                # logger.debug(f"Получена информация об объявлении: {listing_details}")
                listing = listing_details.get('data', {}).get('listing', {})

                post_date_str = listing['postDate']
                try:
                    post_date = datetime.datetime.fromisoformat(post_date_str.replace('Z', '+00:00'))
                    current_time = datetime.datetime.now(datetime.UTC)
                    time_diff = current_time - post_date
                    location_name = listing["locationDetails"]["locationName"]
                    logger.debug(f"{ad_id} Опубликовано {time_diff.total_seconds() // 60} минут назад, {location_name}")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Ошибка при парсинге даты публикации {post_date_str}: {e}.")

                await add_ad(listing)

            except Exception as e:
                logger.error(f"Ошибка при получении деталей объявления {ad_id}: {e}")
                return None

    async def _parse_new_listings(self, city: str, coordinates: Tuple[float, float]):
        """
        Основная логика парсинга:
        1. Получить все категории.
        2. Отфильтровать по PARSER_CATEGORIES_EXCLUDED и уровню 1.
        3. Для каждой категории: получить новые объявления, проверить фильтры, сохранить в БД.
        """
        categories = await self._get_categories()
        logger.info(f"Парсим {city}")

        # --- 1. Параллельный запрос всех объявлений из всех категорий ---
        all_listings_tasks = [self._fetch_listings_for_category(cat["id"], coordinates) for cat in categories]
        all_listings_results = await asyncio.gather(*all_listings_tasks, return_exceptions=True)

        # Собираем все объявления из всех категорий
        all_listings = []
        for i, result in enumerate(all_listings_results):
            if isinstance(result, Exception):
                logger.error(f"Ошибка при получении объявлений из категории {categories[i]['id']}: {result}")
                continue
            if result: # Если результат не None
                all_listings.extend(result)

        if not all_listings:
            logger.debug("Нет новых объявлений из всех категорий.")
            return

        logger.debug(f"Получено {len(all_listings)} объявлений из всех категорий.")

        # --- 2. Извлечение уникальных ad_id ---
        unique_ad_ids = set()
        for tile in all_listings:
            listing_data = tile.get('listing')
            if listing_data:
                ad_id = listing_data.get('listingId')
                if ad_id:
                    unique_ad_ids.add(ad_id)

        logger.debug(f"Уникальных ID объявлений для проверки: {len(unique_ad_ids)}")

        # --- 3. Параллельный запрос деталей для новых объявлений через семафор ---
        detail_tasks = [self._fetch_ad_details(ad_id) for ad_id in unique_ad_ids]
        await asyncio.gather(*detail_tasks, return_exceptions=True)
