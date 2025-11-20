# config.py
import os
from dotenv import load_dotenv
load_dotenv()


# https://api.anymessage.shop/email/getmessage?token=JGuX5P1XIsIb8k0deVon9G7caR5d7R1t&preview=1&id=
# https://api.anymessage.shop/email/reorder?token=JGuX5P1XIsIb8k0deVon9G7caR5d7R1t&id=


# Настройки создания фишей
TEAM = "resonanse"
TEAM_API_KEY = os.getenv("KARAS_TEAM_API_KEY")        # "KARAS_TEAM_API_KEY" или "COMMANDER_TEAM_API_KEY"
TEAM_USER_ID = int(os.getenv("KARAS_ID"))             # "KARAS_ID" или "COMMANDER_ID"
BALANCE_CHECKER = True                                    # True или False
FISH_VERSION = "2.0"                                      # "2.0" или "verif"
FISH_BUYER_NAME = "David Kim"
FISH_BUYER_ADDRESS = "540 S 200 W St, Beaver, UT 84713, USA"
PERSONAL_DOMAIN = os.getenv("PERSONAL_DOMAIN")
DOMAIN_ID = int(os.getenv("KARAS_FISH_ID"))           # "COMMANDER_FISH_ID" или "KARAS_FISH_ID"
REDIRECTS_API_KEY = os.getenv("REDIRECTS_API_KEY")
REDIRECTS_DOMAIN = os.getenv("REDIRECTS_DOMAIN")

FANCY_ORIGINAL_TEXT = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
FANCY_SHRIFT_TEXT = '𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡𝟘'

# -- Настройки GreedySMS --
GREEDY_COUNTRY_ID = 187                                 # США
GREEDY_SERVICE_ID = "zm"                                # OfferUp
GREEDY_OPERATOR_NAME = "tmobile"
GREEDY_API_KEY = os.getenv("COMMANDER_GREEDY_API_KEY")  # "COMMANDER_GREEDY_API_KEY" или "KARAS_GREEDY_API_KEY"
GREEDY_MAX_PRICE = 20  # rub


# -- Настройки AnyMessage --
ANYMESSAGE_API_KEY = os.getenv("COMMANDER_ANYMESSAGE_API_KEY")  # KARAS_ANYMESSAGE_API_KEY или KOMMANDER_ANYMESSAGE_API_KEY
ANYMESSAGE_EMAIL_DOMAIN = "outlook.com"
ANYMESSAGE_EMAIL_SITE = "offerup.com"


# -- Настройки регистрации --
AVATAR = ""
# AVATAR = "data/avatar.jpg"
DEFAULT_ACCOUNT_NAME = "random"  # или "random"
DEFAULT_PASTA = [
    "We would like to inform you that the item has been claimed by a buyer.",
    "To change the item's status, please follow the ⅼ𝗶𝗻𝗸. Thank you for staying with us!",
    "{fish}"
]
VERIFY_EMAIL = True
VERIFY_PHONE = False
REGISTRAR_PROXY = os.getenv("REGISTRAR_PROXY")
OFFERUP_APP_VERSION = "2025.42.0"
OFFERUP_BUILD = "2025420004"
REGISTRAR_DELAY = 5


# -- Настройки сендера
MAX_AD_AGE = 60*48  # минут
MAX_RATINGS_COUNT = 0
SENDER_DELAY_BETWEEN_MESSAGES = 10
SENDER_COOLDOWN_SECONDS_FOR_ACCOUNT = 30
LIMIT_PROCESSED = 6



# -- Настройки парсера --
CITIES = {
    "Austin": (30.30162942254873, -97.71792895784678),
    "Akron": (41.10873322090972, -81.52667034586825),
    "Albuquerque": (35.07989825103732, -106.65789567854694),
    "Atlanta": (33.75676000783004, -84.39959536746775),
    "Augusta": (33.4593892448076, -82.02105549763552),
    "Baltimor": (39.296462398419436, -76.61578195695581),
    "Bakersfield": (35.39646395772715, -119.01625630030999),
    "Boston": (42.3644946221799, -71.17191203463652),
    "Birmingham": (33.518945420667265, -86.81658738300167),
    "Charlotte": (35.25514013425387, -80.82217620525678),
    "Chicago": (41.84449380067751, -87.98050011632826),
    "Chattanooga": (35.05292181272193, -85.32244692684108),
    "Cincinnati": (39.10916665397127, -84.53692403794233),
    "Columbus": (39.98500929384035, -82.99907004385533),
    "Dallas": (32.80883876400479, -97.05625587459683),
    "Denver": (39.75726598939007, -104.98591602939469),
    "Detroit": (42.47654327163873, -83.19659207547873),
    "El Paso": (31.748906279025082, -106.42513700442414),
    "Fort Smith": (35.38272753711714, -94.3922675536869),
    "Fresno": (36.771042821265226, -119.77744826733395),
    "Greensboro": (36.07173487476938, -79.7963238131338),
    "Grand Rapids": (42.98494961240547, -85.66851602241667),
    "Houston": (29.778488437762647, -95.36787166484116),
    "Indianapolis": (39.79180384505216, -86.14787054340083),
    "Jacksonville": (30.348131925829147, -81.66257270785776),
    "Kansas City": (39.109166607901194, -94.57842798796553),
    "Las Vegas": (36.16314704563283, -115.18325486520764),
    "Los Angeles": (34.07806962853416, -118.24150672341925),
    "Litle Rock": (34.74675360985964, -92.2963019141928),
    "Memphis": (35.156283251152765, -90.01910186611723),
    "Miami": (26.06219840885343, -80.18084544602497),
    "MIlwauke": (43.057238790997324, -88.06353556460999),
    "Mobile": (30.695071762312065, -88.04156282394054),
    "Montgomery": (32.37113488242126, -86.30022995995418),
    "Nashville": (36.193946774920335, -86.76323467003706),
    "New York": (40.69843740331633, -73.93993324094151),
    "Norfolg": (36.858075796072015, -76.29717844758413),
    "Oklahoma City": (35.45550301736424, -97.53006824103277),
    "Orlando": (28.551221103309278, -81.37286197684688),
    "Peoria": (40.685209485577296, -89.59063513881009),
    "Philadelphia": (39.965026253282666, -75.16884060799298),
    "Phoenix": (33.480270473126595, -112.08228351819874),
    "Portland": (45.54067232532414, -122.66332494067237),
    "Pittsburg": (40.4348121979348, -80.02154343338998),
    "Providence": (41.82494747797532, -71.4082626414451),
    "Raleigh": (35.7959725903102, -78.63726627841184),
    "Richmond": (37.55371193264264, -77.46722233427184),
    "Sacramento": (38.677351166648315, -121.41528080601874),
    "San Antonio": (29.407542546870122, -98.49342553609233),
    "San Diego": (32.723850350865085, -116.81545532973306),
    "San Francisco": (37.76147128734422, -122.43932031490331),
    "San Jose": (37.39266404107808, -121.9744009286356),
    "San Bernardino": (34.102151249632755, -117.24450160233538),
    "Saint Louis": (38.647326238191056, -90.1948832489999),
    "Seattle": (47.62109460951212, -122.32058436212402),
    "Spokane": (47.68054320033548, -117.4354836582816),
    "Springfield": (37.208882903327485, -93.29302785763451),
    "Tampa": (27.960915782760992, -82.44402889047713),
    "Tallahassee": (30.449135061018566, -84.27325248029815),
    "Tucson": (32.25971792839872, -111.01122831317807),
    "Washington": (38.913943911962185, -77.03930977365651)
}
PARSER_PROXY = os.getenv("PARSER_PROXY")
PARSER_DELAY = 60  # Периодичность проверки в сек
PARSER_SEMAPHORE = 10  # Кол-во параллельных запросов
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
# os.makedirs(DATA_DIR, exist_ok=True)
# os.makedirs(ARCHIVE_ACCOUNTS_DIR, exist_ok=True)
# os.makedirs(LIMIT_OUT_ACCOUNTS_DIR, exist_ok=True)

