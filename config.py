# config.py
import os

from dotenv import load_dotenv


load_dotenv()


# Настройки создания фишей
TEAM = "resonanse"
TEAM_API_KEY = os.getenv("COMMANDER_TEAM_API_KEY")        # "KARAS_TEAM_API_KEY" или "COMMANDER_TEAM_API_KEY"
TEAM_USER_ID = int(os.getenv("COMMANDER_ID"))             # "KARAS_ID" или "COMMANDER_ID"
BALANCE_CHECKER = True                                    # True или False
FISH_VERSION = "2.0"                                      # "2.0" или "verif"
FISH_BUYER_NAME = "David Kim"
FISH_BUYER_ADDRESS = "540 S 200 W St, Beaver, UT 84713, US"
PERSONAL_DOMAIN = os.getenv("PERSONAL_DOMAIN")
DOMAIN_ID = int(os.getenv("COMMANDER_FISH_ID"))           # "COMMANDER_FISH_ID" или "KARAS_FISH_ID"

FANCY_ORIGINAL_TEXT = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
FANCY_SHRIFT_TEXT = '𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍1234567890'

# -- Настройки GreedySMS --
GREEDY_COUNTRY_ID = 187                                 # США
GREEDY_SERVICE_ID = "zm"                                # OfferUp
GREEDY_OPERATOR_NAME = "tmobile"
GREEDY_API_KEY = os.getenv("COMMANDER_GREEDY_API_KEY")  # "COMMANDER_GREEDY_API_KEY" или "KARAS_GREEDY_API_KEY"
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
    "HELLO",
    "{fish}"
]
VERIFY_EMAIL = True
VERIFY_PHONE = False
MAIN_PROXY = os.getenv("MAIN_PROXY")
OFFERUP_APP_VERSION = "2025.42.0"
OFFERUP_BUILD = "2025420004"
REGISTRAR_DELAY = 5


# -- Настройки сендера
MAX_AD_AGE = 12000  # минут
SENDER_DELAY_BETWEEN_MESSAGES = 3
SENDER_COOLDOWN_SECONDS_FOR_ACCOUNT = 60


# -- Настройки парсера --
PARSER_PROXY = os.getenv("PARSER_PROXY")
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
