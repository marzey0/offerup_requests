import os

from dotenv import load_dotenv


load_dotenv()

# -- Настройки GreedySMS --
GREEDY_COUNTRY_ID = 187           # США
GREEDY_SERVICE_ID = "zm"          # OfferUp
GREEDY_OPERATOR_NAME = "tmobile"
GREEDY_API_KEY = os.getenv("GREEDY_API_KEY")

# -- Настройки AnyMessage --
ANYMESSAGE_API_KEY = os.getenv("ANYMESSAGE_API_KEY")

# -- Настройки регистрации --
MAIN_PROXY = os.getenv("MAIN_PROXY")


