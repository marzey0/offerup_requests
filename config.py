# config.py
import os

from dotenv import load_dotenv


load_dotenv()


# -- Настройки GreedySMS --
GREEDY_COUNTRY_ID = 187           # США
GREEDY_SERVICE_ID = "zm"          # OfferUp
GREEDY_OPERATOR_NAME = "tmobile"
GREEDY_API_KEY = os.getenv("GREEDY_API_KEY")
GREEDY_MAX_PRICE = 20  # rub


# -- Настройки AnyMessage --
ANYMESSAGE_API_KEY = os.getenv("ANYMESSAGE_API_KEY")
ANYMESSAGE_EMAIL_DOMAIN = "gmx.us"
ANYMESSAGE_EMAIL_SITE = "offerup.com"


# -- Настройки регистрации --
DEFAULT_ACCOUNT_NAME = "тётя мотя"  # или "random"
DEFAULT_PASTA = ["hi, bro"]
VERIFY_EMAIL = True
VERIFY_PHONE = False
MAIN_PROXY = os.getenv("MAIN_PROXY")
OFFERUP_APP_VERSION = "2025.42.0"
OFFERUP_BUILD = "2025420004"
REGISTRAR_DELAY = 5


# -- Настройки сендера
SENDER_DELAY_BETWEEN_MESSAGES = 1
SENDER_COOLDOWN_SECONDS_FOR_ACCOUNT = 5


# -- Настройки парсера --
PARSER_DELAY = 180  # Периодичность проверки в сек (НЕ СТАВЬ ДОХУЯ, ЖРЁТ ТРАФИК КАК ЕБАНУТЫЙ)
PARSER_SEMAPHORE = 5  # Кол-во параллельных запросов
PARSER_CATEGORIES_EXCLUDED = [  # Исключить из парсинга следующие категории:
    # "Electronics & Media",
    # "Home & Garden",
    # "Clothing, Shoes, & Accessories",
    "Baby & Kids",
    "Vehicles",
    "Toys, Games, & Hobbies",
    "Sports & Outdoors",
    "Collectibles & Art",
    "Pet supplies",
    "Health & Beauty",
    # "Wedding",
    "Business equipment",
    "Tickets",
    "General"
]


# -- Другое --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ACCOUNTS_DIR = os.path.join(BASE_DIR, "accounts")
DATABASE_PATH = os.path.join(DATA_DIR, "main.db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ACCOUNTS_DIR, exist_ok=True)
