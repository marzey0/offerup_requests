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
OFFERUP_APP_VERSION = "2025.42.0"
OFFERUP_BUILD = "2025420004"
REGISTRAR_DELAY = 5
MAIN_PROXY = os.getenv("MAIN_PROXY")
MESSAGES = ["hi, bro"]

DATABASE_PATH = "data/main.db"
os.makedirs("data", exist_ok=True)
ACCOUNTS_DIR = "accounts"
os.makedirs(ACCOUNTS_DIR, exist_ok=True)
PARSER_DELAY = 15

# -- Настройки сендера
SENDER_DELAY = 1
SENDER_COOLDOWN_SECONDS = 5


# -- Настройки парсера --
PARSER_CATEGORIES_EXCLUDED = [  # Исключить из парсинга следующие категории:
    "Vehicles", "Tickets", "Business equipment"
]

