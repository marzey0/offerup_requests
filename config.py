# config.py
import os

from dotenv import load_dotenv


load_dotenv()

# https://api.anymessage.shop/email/getmessage?token=JGuX5P1XIsIb8k0deVon9G7caR5d7R1t&preview=1&id=
# https://api.anymessage.shop/email/reorder?token=JGuX5P1XIsIb8k0deVon9G7caR5d7R1t&id=


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
FANCY_SHRIFT_TEXT = '𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁1234567890'

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
ANYMESSAGE_EMAIL_DOMAIN = "gmail.com"
ANYMESSAGE_EMAIL_SITE = "offerup.com"


# -- Настройки регистрации --
DEFAULT_ACCOUNT_NAME = "Service"  # или "random"
DEFAULT_PASTA = [
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
MAX_RATINGS_COUNT = 10
SENDER_DELAY_BETWEEN_MESSAGES = 3
SENDER_COOLDOWN_SECONDS_FOR_ACCOUNT = 60
LIMIT_PROCESSED = 5


# -- Настройки парсера --
CITIES = {
    "New York": (40.69843740331633, -73.93993324094151),
    "Los Angeles": (34.07806962853416, -118.24150672341925),
    "Chicago": (41.84449380067751, -87.98050011632826),
    "Houston": (29.778488437762647, -95.36787166484116),
    "Phoenix": (33.480270473126595, -112.08228351819874),
    "Philadelphia": (39.965026253282666, -75.16884060799298),
    "San Antonio": (29.407542546870122, -98.49342553609233),
    "San Diego": (32.723850350865085, -116.81545532973306),
    "Dallas": (32.80883876400479, -97.05625587459683),
    "San Jose": (37.39266404107808, -121.9744009286356),
    "Austin": (30.30162942254873, -97.71792895784678),
    "Jacksonville": (30.348131925829147, -81.66257270785776),
    "Columbus": (39.98500929384035, -82.99907004385533),
    "Indianapolis": (39.79180384505216, -86.14787054340083),
    "Charlotte": (35.25514013425387, -80.82217620525678),
    "San Francisco": (37.76147128734422, -122.43932031490331),
    "Seattle": (47.62109460951212, -122.32058436212402),
    "Denver": (39.75726598939007, -104.98591602939469),
    "Oklahoma City": (35.45550301736424, -97.53006824103277),
    "Nashville": (36.193946774920335, -86.76323467003706),
    "El Paso": (31.748906279025082, -106.42513700442414),
    "Washington": (38.913943911962185, -77.03930977365651),
    "Boston": (42.3644946221799, -71.17191203463652),
    "Las Vegas": (36.16314704563283, -115.18325486520764),
    "Portland": (45.54067232532414, -122.66332494067237)
}
PARSER_PROXY = os.getenv("PARSER_PROXY")
PARSER_DELAY = 180  # Периодичность проверки в сек (НЕ СТАВЬ ДОХУЯ, ЖРЁТ ТРАФИК КАК ЕБАНУТЫЙ)
PARSER_SEMAPHORE = 5  # Кол-во параллельных запросов
PARSER_CATEGORIES_EXCLUDED = [  # Исключить из парсинга следующие категории:
    # "Electronics & Media",
    # "Home & Garden",
    # "Clothing, Shoes, & Accessories",
    # "Baby & Kids",
    "Vehicles",
    # "Toys, Games, & Hobbies",
    # "Sports & Outdoors",
    # "Collectibles & Art",
    # "Pet supplies",
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
ARCHIVE_ACCOUNTS_DIR = os.path.join(ACCOUNTS_DIR, "archive")
LIMIT_OUT_ACCOUNTS_DIR = os.path.join(ACCOUNTS_DIR, "limit_out")
DATABASE_PATH = os.path.join(DATA_DIR, "main.db")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARCHIVE_ACCOUNTS_DIR, exist_ok=True)
os.makedirs(LIMIT_OUT_ACCOUNTS_DIR, exist_ok=True)

