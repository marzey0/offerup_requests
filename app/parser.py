# app/core/parser.py
import asyncio
import logging
from typing import Dict, Any, Optional, List
from app.core.offerup_api import OfferUpAPI
from app.core.database import add_ad_if_new
from app.account_manager import AccountManager
from config import PARSER_DELAY, PARSER_CATEGORIES_EXCLUDED

logger = logging.getLogger(__name__)


class OfferUpParser:
    """
    Компонент для парсинга новых объявлений на OfferUp.
    Использует рандомный аккаунт из папки accounts/ для выполнения запросов.
    Получает список всех категорий, исключает PARSER_CATEGORIES_EXCLUDED.
    Для каждой оставшейся категории 1-го уровня парсит новые объявления.
    Проверяет фильтры (0 продаж/0 покупок) сразу из полученных данных.
    Сохраняет объявления в базу данных с соответствующим статусом processed.
    """

    def __init__(self, db_path: str, delay: int = PARSER_DELAY):
        self.db_path = db_path
        self.delay = delay
        self.running = True  # Флаг для остановки из main.py
        self.account_manager = AccountManager() # Создаём менеджер аккаунтов
        # self.proxy = MAIN_PROXY # Не используем, если OfferUpAPI из AccountManager инициализирована с proxy из JSON

        self.offerup_api = OfferUpAPI()

    async def run(self):
        """
        Основной цикл парсера.
        """
        logger.info("Запуск компонента парсера.")
        while self.running:
            try:
                logger.debug("Начало цикла парсинга...")
                await self._parse_new_listings()
                logger.debug(f"Цикл парсинга завершён. Пауза {self.delay} секунд.")
                await asyncio.sleep(self.delay)
            except Exception as e:
                logger.error(f"Неожиданная ошибка в цикле парсера: {e}")
                await asyncio.sleep(self.delay) # Пауза даже при ошибке

    async def _parse_new_listings(self):
        """
        Основная логика парсинга:
        1. Получить аккаунт.
        2. Получить все категории.
        3. Отфильтровать по PARSER_CATEGORIES_EXCLUDED и уровню 1.
        4. Для каждой категории: получить новые объявления, проверить фильтры, сохранить в БД.
        """
        # --- 1. Выбираем аккаунт ---
        account_keys = self.account_manager.get_all_account_keys()
        if not account_keys:
            logger.warning("Нет доступных аккаунтов для парсинга. Ожидание...")
            return

        import random
        chosen_account_key = random.choice(account_keys)
        logger.info(f"Используем аккаунт {chosen_account_key} для парсинга.")

        self.offerup_api = self.account_manager.get_api_instance(chosen_account_key)
        if not self.offerup_api:
            logger.error(f"Не удалось получить API клиент для аккаунта {chosen_account_key}. Пропуск итерации.")
            return

        # --- 2. Получаем все категории ---
        logger.debug("Получение иерархии категорий...")
        try:
            async with self.offerup_api as ac:
                taxonomy_response = await ac.get_category_taxonomy()
                categories = taxonomy_response.get('data', {}).get('getTaxonomy', {}).get('children', [])
        except Exception as e:
            logger.error(f"Ошибка при получении категорий: {e}")
            return

        if not categories:
            logger.warning("Не удалось получить список категорий. Пропуск итерации.")
            return

        # --- 3. Фильтруем категории ---
        filtered_categories = []
        for cat in categories:
            label = cat.get('label')
            level = cat.get('level')
            cat_id = cat.get('id')
            if level == 1 and label not in PARSER_CATEGORIES_EXCLUDED:
                logger.debug(f"Добавляем в парсинг категорию 1-го уровня: {label} (ID: {cat_id})")
                filtered_categories.append(cat)
            else:
                logger.debug(f"Пропускаем категорию: {label} (уровень: {level}, в исключениях: {label in PARSER_CATEGORIES_EXCLUDED})")

        if not filtered_categories:
            logger.warning("Нет подходящих категорий 1-го уровня для парсинга.")
            return

        # --- 4. Обрабатываем каждую отфильтрованную категорию ---
        for category in filtered_categories:
            cat_id = category.get('id')
            cat_label = category.get('label')
            if not cat_id or not cat_label:
                logger.warning(f"Категория без ID или названия, пропущена: {category}")
                continue

            logger.info(f"Парсинг категории: {cat_label} (ID: {cat_id})")

            try:
                # Получаем объявления для категории
                listings_tiles = await self._fetch_listings_for_category(cat_id)
                if not listings_tiles:
                    logger.debug(f"Нет объявлений в категории {cat_label} (ID: {cat_id}).")
                    continue

                logger.debug(f"Получены объявления: {listings_tiles}")

                # Обрабатываем каждое объявление в плитках
                for tile in listings_tiles:
                    # Извлекаем информацию о продавце из плитки
                    listing_data = tile.get('listing')
                    if not listing_data:
                        logger.warning(f"Плитка без данных объявления, пропущена: {tile}")
                        continue

                    ad_id = listing_data.get('listingId')
                    if not ad_id:
                        logger.warning(f"Объявление без listingId в категории {cat_label}, пропущено: {listing_data}")
                        continue

                    async with self.offerup_api as ac:
                        listing_details = await ac.get_item_detail_data_by_listing_id(ad_id)
                        if not listing_details:
                            continue
                    logger.debug(f"Получена информация об объявлении: {listing_details}")

                    # Извлекаем информацию о продавце
                    owner_data = listing_details.get('data', {}).get('listing', {}).get('owner', {})
                    owner_profile = owner_data.get('profile', {})
                    if not owner_profile:
                        logger.warning(f"Не удалось получить профиль продавца для объявления {ad_id}. Пропуск.")
                        continue

                    # Проверяем фильтры: 0 продаж и 0 покупок
                    ratings_count = owner_profile.get('ratingSummary', {}).get("count")
                    title = listing_data.get('title', 'Без названия')
                    seller_id = owner_data.get('id') # Используем id из owner, а не userId из profile, если он есть

                    # Сохраняем в БД. Функция сама решит, установить processed = 1 или 0
                    added = await add_ad_if_new(
                        db_path=self.db_path,
                        ad_id=ad_id,
                        title=title,
                        seller_id=seller_id,
                        ratings_count=ratings_count
                    )
                    if added:
                        if ratings_count == 0:
                            logger.info(f"Новое объявление {ad_id} от продавца {seller_id} (ratings_count == 0) добавлено в БД с processed=1.")
                        else:
                            logger.info(f"Новое объявление {ad_id} от продавца {seller_id} (ratings_count != 0) добавлено в БД с processed=0.")
                    else:
                        logger.debug(f"Объявление {ad_id} уже существует в БД, обновлено.")

            except Exception as e:
                logger.error(f"Ошибка при парсинге категории {cat_label} (ID: {cat_id}): {e}")
                continue

    async def _fetch_listings_for_category(self, category_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Получает *плитки* с объявлениями для указанной категории.
        Возвращает список плиток типа LISTING.
        """
        try:
            async with self.offerup_api as ac:
                response = await ac.get_new_listings_in_category(category_id=category_id)
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
