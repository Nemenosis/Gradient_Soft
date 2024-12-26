import asyncio
import captchatools

from data.config import (
    TWO_CAPTCHA_API_KEY,
    ANTICAPTCHA_API_KEY,
    CAPMONSTER_API_KEY,
    CAPSOLVER_API_KEY,
    CAPTCHAAI_API_KEY,
    CAPTCHA_PARAMS
)


# OopCompanion:suppressRename


class CaptchaService:
    def __init__(self):
        self.SERVICE_API_MAP = {
            "2captcha": TWO_CAPTCHA_API_KEY,
            "anticaptcha": ANTICAPTCHA_API_KEY,
            "capmonster": CAPMONSTER_API_KEY,
            "capsolver": CAPSOLVER_API_KEY,
            "captchaai": CAPTCHAAI_API_KEY,
        }

    def get_captcha_token(self):
        try:
            captcha_config = self.parse_captcha_type()
            if not CAPTCHA_PARAMS.get("sitekey") or not CAPTCHA_PARAMS.get("captcha_url"):
                raise ValueError("Missing required CAPTCHA_PARAMS: 'sitekey' or 'captcha_url'")

            solver = captchatools.new_harvester(**captcha_config, **CAPTCHA_PARAMS)
            return solver.get_token()

        except Exception as e:
            print(f"Ошибка при решении капчи: {e}")
            return None

    def parse_captcha_type(self, exit_on_fail: bool = True):
        for service, api_key in self.SERVICE_API_MAP.items():
            if api_key:
                return {"solving_site": service, "api_key": api_key}

        if exit_on_fail:
            print("No valid captcha solving service API key found.")
            exit(1)

    async def get_captcha_token_async(self):
        return await asyncio.to_thread(self.get_captcha_token)


# if __name__ == "__main__":
#     service = CaptchaService()
#     token = service.get_captcha_token()
#
#     if token:
#         print(f"Полученный токен капчи: {token}")
#     else:
#         print("Не удалось получить токен капчи.")
