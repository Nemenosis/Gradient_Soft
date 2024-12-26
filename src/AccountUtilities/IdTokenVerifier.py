import time
import random
from loguru import logger


# OopCompanion:suppressRename


class IdTokenVerifier:
    def __init__(self, email, db_manager, user_agent, proxy):
        self.id_token = None
        self.email = email
        self.db_manager = db_manager
        self.user_agent = user_agent
        self.proxy = proxy

    async def get_id_token(self, session):
        url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=AIzaSyCWz-svq_InWzV9WaE3ez4XqxCE0C34ddI"
        password = await self.db_manager.get_user_data({"email": self.email}, False, "password")
        payload = {"clientType": "CLIENT_TYPE_WEB", "email": self.email,
                   "password": password.get('password'), "returnSecureToken": "true"}
        headers = {"User-Agent": self.user_agent}

        try:
            async with session.post(url, json=payload, headers=headers, proxy=self.proxy) as response:
                if response.status != 200:
                    logger.error("Failed to get ID token. Status code: {}", response.status)
                    return None

                response_data = await response.json()
                id_token = response_data.get("idToken")
                if not id_token:
                    logger.error("ID token missing in response: {}", response_data)
                    return None
                return id_token

        except Exception as e:
            logger.error("An error occurred while getting ID token: {}", e)
            return

    async def verify_id_token(self, session):
        url = "https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=AIzaSyCWz-svq_InWzV9WaE3ez4XqxCE0C34ddI"
        payload = {"idToken": self.id_token}
        headers = {"User-Agent": self.user_agent}

        try:
            async with session.post(url, json=payload, headers=headers, proxy=self.proxy) as response:
                if response.status != 200:
                    logger.error("Failed to verify ID token. Status code: {}", response.status)
                    return False

                response_data = await response.json()
                if not response_data.get("users"):
                    logger.error("Invalid ID token: {}", response_data)
                    return False

                return True

        except Exception as e:
            logger.error("An error occurred while verifying ID token: {}", e)
            return False

    async def id_token_verification(self, session):
        db_token = await self.db_manager.get_user_data({"email": self.email}, False, "idToken")
        self.id_token = db_token.get("idToken")
        try:
            is_valid = await self.verify_id_token(session)
            if not is_valid:
                self.id_token = await self.get_id_token(session)
                if self.id_token:
                    await self.db_manager.update_user({'email': self.email}, idToken=self.id_token)
            return self.id_token

        except Exception as e:
            logger.error("An error occurred while verifying or obtaining a token: {}", e)
            return None
