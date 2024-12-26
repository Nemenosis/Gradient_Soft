from operator import truediv


MIN_PROXY_SCORE = 50  # for mining mode

#########################################
APPROVE_EMAIL = True  # approve email (NEEDED IMAP AND ACCESS TO EMAIL)
#
GRADIENT_DATA = "data/GradientData.db"
IMAP_DOMAIN = "imap.firstmail.ltd"  # CHANGE ON YOUR IMAP DOMAIN

#########################################

CLAIM_REWARDS_ONLY = False

STOP_ACCOUNTS_WHEN_SITE_IS_DOWN = True  # stop account for 20 minutes, to reduce proxy traffic usage
CHECK_POINTS = False  # show point for each account every nearly 10 minutes

# Mining mode
MINING_MODE = False # TRUE IF MINING MODE

# REGISTER PARAMETERS ONLY
REGISTER_ACCOUNT_ONLY = False # TRUE IF REGISTER MODE
REGISTER_TASKS = 2 # CHANGE FOR ACCOUNT REGISTER ONLY
MULTIPROCESS = 5 # CHANGE FOR MINING AND FOR NODE REGISTER ONLY
NODE_REGISTER = False # TRUE IF NODE REGISTER MODE
DB_INIT = False # TRUE FOR DATABASE INITIALIZATION


# 8e2a3ad7b1359e109963fb284aa2d019
TWO_CAPTCHA_API_KEY = ""
ANTICAPTCHA_API_KEY = ""
CAPMONSTER_API_KEY = ""
CAPSOLVER_API_KEY = ""
CAPTCHAAI_API_KEY = ""

# Captcha params, left empty
CAPTCHA_PARAMS = {
    # "captcha_type": "v3",
    # "invisible_captcha": False,
    "sitekey": "6Lfe5TAqAAAAAI3mJZFYU17Rzjh9DB5KDRReuqYV",
    "captcha_url": "https://app.gradient.network/signup"
}


########################################

ACCOUNTS_FILE_PATH = "mail.txt"
PROXIES_FILE_PATH = "proxy.txt"
# WALLETS_FILE_PATH = "data/wallets.txt"