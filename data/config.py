from src.AccountUtilities.CPU import cores

GRADIENT_DATA = "data/GradientData.db" # DONT CHANGE

IMAP_DOMAIN = ""  # CHANGE ON YOUR IMAP DOMAIN FOR EXAMPLE: imap.gmx.net

# Mining mode
MINING_MODE = False # TRUE IF MINING MODE

# REGISTER PARAMETERS ONLY
REGISTER_ACCOUNT_ONLY = False # TRUE IF REGISTER MODE
REGISTER_TASKS = 5 # CHANGE FOR ACCOUNT REGISTER ONLY
MULTIPROCESS = cores # CHANGE FOR MINING AND FOR NODE REGISTER ONLY, FOR NOW WE AUTOMATICALLY CHECK THE CPU, BUT IF YOU WANT TO USE FEWER CORES, IT'S OK.
NODE_REGISTER = False # TRUE IF NODE REGISTER MODE
DB_INIT = False # TRUE FOR DATABASE INITIALIZATION


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