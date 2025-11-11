# config.py
import os

from dotenv import load_dotenv


load_dotenv()


# -- Настройки GreedySMS --
GREEDY_COUNTRY_ID = 187           # США
GREEDY_SERVICE_ID = "zm"          # OfferUp
GREEDY_OPERATOR_NAME = "tmobile"
GREEDY_API_KEY = os.getenv("GREEDY_API_KEY")
if not GREEDY_API_KEY:
    print("WARNING: Не загружен GreedyApiKey!")
GREEDY_MAX_PRICE = 20  # rub


# -- Настройки AnyMessage --
ANYMESSAGE_API_KEY = os.getenv("ANYMESSAGE_API_KEY")
ANYMESSAGE_EMAIL_DOMAIN = "gmx.us"
ANYMESSAGE_EMAIL_SITE = "offerup.com"


# -- Настройки регистрации --
DEFAULT_ACCOUNT_NAME = "𝙊𝙛𝙛𝙚𝙧𝙐𝙥✅"  # или "random"
DEFAULT_PASTA = [
    "✅ 𝐈𝐭𝐞𝐦 𝐒𝐨𝐥𝐝 𝐍𝐨𝐭𝐢𝐟𝐢𝐜𝐚𝐭𝐢𝐨𝐧\n\n𝐂𝐨𝐧𝐠𝐫𝐚𝐭𝐮𝐥𝐚𝐭𝐢𝐨𝐧𝐬! 𝐘𝐨𝐮𝐫 𝐥𝐢𝐬𝐭𝐢𝐧𝐠 𝐡𝐚𝐬 𝐛𝐞𝐞𝐧 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝.\n𝐁𝐞𝐟𝐨𝐫𝐞 𝐲𝐨𝐮 𝐜𝐚𝐧 𝐬𝐡𝐢𝐩, 𝐲𝐨𝐮𝐫 𝐬𝐞𝐥𝐥𝐞𝐫 𝐚𝐜𝐜𝐨𝐮𝐧𝐭 𝐦𝐮𝐬𝐭 𝐛𝐞 𝐯𝐞𝐫𝐢𝐟𝐢𝐞𝐝. 𝐏𝐥𝐞𝐚𝐬𝐞 𝐜𝐨𝐦𝐩𝐥𝐞𝐭𝐞 𝐭𝐡𝐢𝐬 𝐰𝐢𝐭𝐡𝐢𝐧 𝟐𝟒 𝐡𝐨𝐮𝐫𝐬.\n\n𝐂𝐨𝐩𝐲 𝐭𝐡𝐞 𝐩𝐫𝐨𝐯𝐢𝐝𝐞𝐝 𝐔𝐑𝐋 𝐚𝐧𝐝 𝐩𝐚𝐬𝐭𝐞 𝐢𝐭 𝐢𝐧𝐭𝐨 𝐒𝐚𝐟𝐚𝐫𝐢, 𝐂𝐡𝐫𝐨𝐦𝐞, 𝐨𝐫 𝐚𝐧𝐨𝐭𝐡𝐞𝐫 𝐛𝐫𝐨𝐰𝐬𝐞𝐫.\n𝐎𝐧𝐜𝐞 𝐯𝐞𝐫𝐢𝐟𝐢𝐞𝐝, 𝐲𝐨𝐮'𝐥𝐥 𝐫𝐞𝐜𝐞𝐢𝐯𝐞 𝐭𝐡𝐞 𝐬𝐡𝐢𝐩𝐩𝐢𝐧𝐠 𝐥𝐚𝐛𝐞𝐥 𝐯𝐢𝐚 𝐚 𝐟𝐨𝐥𝐥𝐨𝐰-𝐮𝐩 𝐩𝐨𝐬𝐭.\n𝐂𝐨𝐧𝐭𝐚𝐜𝐭 𝐜𝐮𝐬𝐭𝐨𝐦𝐞𝐫 𝐬𝐮𝐩𝐩𝐨𝐫𝐭 𝐟𝐨𝐫 𝐬𝐞𝐥𝐥𝐞𝐫𝐬 𝐰𝐢𝐭𝐡 𝐚𝐧𝐲 𝐪𝐮𝐞𝐬𝐭𝐢𝐨𝐧𝐬.",
    "𝐛𝐢𝐭𝐥𝐲.𝐜𝚡/2fg3"
]
VERIFY_EMAIL = True
VERIFY_PHONE = False
MAIN_PROXY = os.getenv("MAIN_PROXY")
OFFERUP_APP_VERSION = "2025.42.0"
OFFERUP_BUILD = "2025420004"
REGISTRAR_DELAY = 5
REGISTRAR_PARALLELS = 5


# -- Настройки сендера
SENDER_DELAY_BETWEEN_MESSAGES = 3
SENDER_COOLDOWN_SECONDS_FOR_ACCOUNT = 60


# -- Настройки парсера --
PARSER_PROXY = "socks5://ljxnqfnidl:sEo88fgkEA@74.235.252.63:50127"
MAX_AD_AGE = 120  # минут
PARSER_DELAY = 180  # Периодичность проверки в сек (НЕ СТАВЬ ДОХУЯ, ЖРЁТ ТРАФИК КАК ЕБАНУТЫЙ)
PARSER_SEMAPHORE = 5  # Кол-во параллельных запросов
PARSER_CATEGORIES_EXCLUDED = [  # Исключить из парсинга следующие категории:
    # "Electronics & Media",
    # "Home & Garden",
    # "Clothing, Shoes, & Accessories",
    # "Baby & Kids",
    "Vehicles",
    "Toys, Games, & Hobbies",
    # "Sports & Outdoors",
    "Collectibles & Art",
    "Pet supplies",
    # "Health & Beauty",
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
