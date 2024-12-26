from multiprocessing.util import is_exiting
from loguru import logger
import random
import aiohttp
import asyncio
# from src.autoReger.mailVerif import MailVerif
from src.dataBase.dataBase import DatabaseManager
from src.autoReger.captcha_manager import CaptchaService
from src.autoReger.mail_verify_manager import MailVerif


# OopCompanion:suppressRename


class AutoReger:
    def __init__(self, email: str, password: str, user_agent, ref_code, db_manager: DatabaseManager):
        self.api_key = "AIzaSyCWz-svq_InWzV9WaE3ez4XqxCE0C34ddI"
        self.SITE_KEY = "6Lfe5TAqAAAAAI3mJZFYU17Rzjh9DB5KDRReuqYV"
        self.proxy = None
        self.email = email
        self.password = password
        self.user_agent = user_agent
        self.db_manager = db_manager
        self.mail_cod = MailVerif(self.email, self.password)
        self.ref_code = ref_code

    async def is_exists(self, session):
        self.proxy = await self.db_manager.get_user_data({"email": self.email}, True, "proxy")
        self.proxy = self.proxy.get("proxy")
        url= f'https://api.gradient.network/api/user/pub/check/genesis?email={self.email}'
        headers = {
            'User-Agent': self.user_agent
        }
        try:
            async with session.post(url, proxy=self.proxy, headers=headers) as response:
                result = await response.json()
                if result.get('code') == 200:
                    data = result.get('data', {})
                    is_firebase = data.get('isFirebase', False)
                    if is_firebase:
                        return True
                    else:
                        return False
        except Exception as e:
            logger.error(f"ERROR: {e}")
            await self.db_manager.replace_banned_proxy(self.email)
            self.proxy = await self.db_manager.get_user_data({"email": self.email}, True, "proxy")
            self.proxy = self.proxy.get("proxy")
            return 'error'

    async def register_user(self, session):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        headers = {
            'User-Agent': self.user_agent
        }
        payload = {
            "clientType": "CLIENT_TYPE_WEB",
            "email": self.email,
            "password": self.password,
            "returnSecureToken": True
        }

        try:
            async with session.post(url, json=payload, proxy=self.proxy, headers=headers) as response:
                if response.status == 200:
                    response_data = await response.json()
                    logger.info(f"Registration start: {response_data.get('email')}")
                    return response_data.get("idToken"), response_data.get("refreshToken")
                else:
                    response_data = await response.json()
                    if "error" in response_data and response_data["error"].get("message") == "EMAIL_EXISTS":
                        logger.error(f"Error: Email already exists ({self.email}).")
                        return None, None
                    else:
                        logger.error(
                            f"Registration failed with status code {response.status}. Response: {response_data}")
                        return None, None
        except Exception as e:
            logger.error(f"An exception occurred during registration: {e}")
            return None, None

    async def verif_token(self, session, id_token):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={self.api_key}"
        payload = {"idToken": id_token}
        headers = {
            'User-Agent': self.user_agent
        }
        try:
            async with session.post(url, json=payload, proxy=self.proxy, headers=headers) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data
                else:
                    response_data = await response.json()

                    if "error" in response_data and response_data["error"].get("message") == "MISSING_ID_TOKEN":
                        logger.error(f"Error: MISSING_ID_TOKEN. The ID token is missing or invalid.")
                        return None
                    else:
                        logger.error(
                            f"Token verification failed with status code {response.status}. Response: {response_data}")
                        return None
        except Exception as e:
            logger.error(f"An exception occurred during token verification: {e}")
            return None

    async def send_captcha_token(self, session, captcha_token, id_token):
        url = "https://api.gradient.network/api/user/send/verify/email"
        payload = {"code": captcha_token}
        headers = {
            "Authorization": f"Bearer {id_token}",
            'User-Agent': self.user_agent
        }
        try:
            async with session.post(url, json=payload, headers=headers, proxy=self.proxy) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data
                else:
                    response_data = await response.json()

                    if "msg" in response_data and response_data["msg"] == "Bot detected":
                        logger.error(f"Error: Bot detected. Please verify you are not a bot. Response: {response_data}")
                        return None

                    logger.error(
                        f"Error: Failed to send captcha token. Status code: {response.status}. Response: {response_data}")
                    return None
        except Exception as e:
            logger.error(f"An exception occurred while sending the captcha token: {e}")
            return None

    async def aborted_mail(self, filename):
        await self.db_manager.delete_user({"email": self.email})
        await self.db_manager.update_user({"proxy": self.proxy}, True,  email= None, status=None)
        try:
            with open(filename, "a") as file:
                file.write(f"{self.email}:{self.password}\n")
            logger.info(f"Successful:'{filename}'.")
        except Exception as e:
            logger.error(f"Error: {e}")

    async def verify_email_with_code(self, session, id_token):
        delay = random.randint(10, 15)
        await asyncio.sleep(delay)

        try:
            code = await self.mail_cod.get_code()

            if code:
                url = "https://api.gradient.network/api/user/verify/email"
                payload = {"code": code}
                headers = {
                    "Authorization": f"Bearer {id_token}",
                    'User-Agent': self.user_agent
                }

                async with session.post(url, json=payload, headers=headers, proxy=self.proxy) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return response_data
                    else:
                        response_data = await response.json()

                        if "msg" in response_data and response_data["msg"] == "Invalid verification code":
                            logger.error("Error: Invalid verification code. The code provided is incorrect or expired.")
                            return None

                        logger.error(
                            f"Error: Failed to verify email. Status code: {response.status}. Response: {response_data}")
                        return None
            else:
                logger.error("Could not receive confirmation code from email.")
                return None
        except Exception as e:
            logger.error(f"An exception occurred while verifying email: {e}")
            return None

    async def register_profile(self, session, id_token):
        url = "https://api.gradient.network/api/user/register"
        payload = {"code": self.ref_code}
        headers = {
            "Authorization": f"Bearer {id_token}",
            'User-Agent': self.user_agent
        }

        try:
            async with session.post(url, json=payload, headers=headers, proxy=self.proxy) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data
                else:
                    response_data = await response.json()
                    logger.error(f"Profile registration error. Status: {response.status}, Respond: {response_data}")
                    return None
        except Exception as e:
            logger.error(f"An error occurred while registering your profile: {e}")
            return None

    async def refresh_id_token(self, session, refresh_token):
        url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        try:
            async with session.post(url, data=payload, proxy=self.proxy) as response:
                if response.status == 200:
                    response_data = await response.json()
                    new_id_token = response_data.get("id_token")
                    await self.db_manager.update_user({"email": self.email},False, idToken=new_id_token)
                    return new_id_token
                else:
                    response_data = await response.json()

                    error_message = response_data.get("error", {}).get("message", "Unknown error")
                    if error_message == "TOKEN_EXPIRED":
                        logger.error("Error: Refresh token has expired.")
                    elif error_message == "INVALID_REFRESH_TOKEN":
                        logger.error("Error: Refresh token is invalid.")
                    elif error_message == "USER_DISABLED":
                        logger.error("Error: User account is disabled.")
                    else:
                        logger.error(f"Unknown error: {error_message}")

                    logger.error(f"Failed to refresh id_token: {response.status}. Response: {response_data}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Client error while refreshing id_token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while refreshing id_token: {e}")
            return None

    async def get_user_profile(self, session, id_token):
        try:
            url = "https://api.gradient.network/api/user/profile"
            headers = {
                "Authorization": f"Bearer {id_token}",
                'User-Agent': self.user_agent
            }
            async with session.post(url, headers=headers, proxy=self.proxy) as response:
                result = await response.json()
                if result.get('code') == 200:
                    logger.info(f"✅ Profile request successful for {self.email}!")
                    return True
                elif result.get('code') == 400:
                    logger.warning(f"⚠️ Invalid request (400) for {self.email}")
                    await self.db_manager.delete_user({"email": self.email})
                    return None
                else:
                    logger.error(f"❌ Profile request error for {self.email}, status: {response.status}")
                    return None
        except Exception as err:
            logger.error(f"❌ Error when requesting profile for {self.email}: {err}")
            return None

    async def process_registration(self,session, filename):
        try:

            # 1. Check if the email already exists
            max_retries = 3
            attempts = 0

            while attempts < max_retries:
                is_exists = await self.is_exists(session)

                if is_exists == 'error':  # Якщо отримано 'error', повторити спробу з новим проксі
                    logger.warning(f"Attempt {attempts + 1}: Proxy error, retrying...")
                    attempts += 1
                    continue  # Переходить до наступної ітерації без інкрементації спроби

                if is_exists:  # Email існує
                    logger.error(f"Email {self.email} already exists. Cannot proceed with registration.")
                    return
                break

            if attempts == max_retries:
                logger.error("Exceeded maximum retries for checking email.")
                return

            # 3. Register the user
            id_token, refresh_token = await self.register_user(session)
            if not id_token or not refresh_token:
                await self.aborted_mail(filename)
                logger.error("User registration failed. Process aborted.")
                return

            # 4. Verify the token
            verified = await self.verif_token(session, id_token)
            if not verified:
                await self.aborted_mail(filename)
                logger.error("Token verification failed. Process aborted.")
                return

            # 2. Solve captcha (assuming `solve_captcha` is already defined)
            captcha_service = CaptchaService()

            captcha_token = await captcha_service.get_captcha_token_async()
            if not captcha_token:
                await self.aborted_mail(filename)
                logger.error("Failed to solve captcha. Registration process aborted.")
                return

            # 5. Send the captcha token
            captcha_verification = await self.send_captcha_token(session, captcha_token, id_token)
            if not captcha_verification:
                await self.aborted_mail(filename)
                logger.error("Captcha token verification failed. Process aborted.")
                return

            # 6. Verify email with the code received via email
            email_verified = await self.verify_email_with_code(session, id_token)
            if not email_verified:
                await self.aborted_mail(filename)
                logger.error("Email verification failed. Process aborted.")
                return

            # 7. Refresh the ID token
            new_id_token = await self.refresh_id_token(session, refresh_token)
            if not new_id_token:
                await self.aborted_mail(filename)
                logger.error("Failed to refresh ID token. Process aborted.")
                return

            verified_refresh = await self.verif_token(session, new_id_token)
            if not verified_refresh:
                await self.aborted_mail(filename)
                logger.error("Token verification failed. Process aborted.")
                return

            # 8. Register the profile with the referral code
            profile_registered = await self.register_profile(session, new_id_token)
            if not profile_registered:
                await self.aborted_mail(filename)
                logger.error("Profile registration failed. Process aborted.")
                return

            delay = random.randint(1, 3)
            await asyncio.sleep(delay)
            get_profile = await self.get_user_profile(session, new_id_token)
            if not get_profile:
                logger.warning("Profile request failed. Process aborted.")
                return

            # 9. Registration process complete
            logger.info(f"Registration process completed successfully for email: {self.email}")

        except Exception as e:
            await self.aborted_mail(filename)
            logger.error(f"An unexpected error occurred during the registration process: {e}")

