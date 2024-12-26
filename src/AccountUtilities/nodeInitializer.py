import asyncio

import aiohttp
import random
from loguru import logger
from src.dataBase.dataBase import DatabaseManager
from src.messenger.mqtt_messenger import MqttMessenger
from src.AccountUtilities.IdTokenVerifier import IdTokenVerifier


# OopCompanion:suppressRename


class NodeInitializer:
    def __init__(self, email, db_manager: DatabaseManager, user_agent, version):
        self.email = email
        self.db_manager = db_manager
        self.user_agent = user_agent
        self.proxy = None
        self.id_token = None
        self.version = version
        self.idTokenVerifier = None

    async def node_registration(self, session):
        self.idTokenVerifier = IdTokenVerifier(self.email, self.db_manager, self.user_agent, self.proxy)
        self.id_token = await self.idTokenVerifier.id_token_verification(session)
        url = "https://api.gradient.network/api/sentrynode/register"
        headers = {"Authorization": f"Bearer {self.id_token}", "User-Agent": self.user_agent}

        try:
            async with session.post(url, headers=headers, proxy=self.proxy) as response:

                if response.status != 200:
                    logger.error("Failed to register node. Status code: {}", response.status)
                    return None

                response_data = await response.json()

                if not response_data.get("clientid") or not response_data.get("username") or not response_data.get(
                        "password"):
                    logger.error("Incomplete registration data: {}", response_data)
                    return None

                await self.db_manager.update_user(
                    {"email": self.email},
                    False,
                    node=response_data.get("clientid"),
                    clientid=response_data.get("username"),
                    nodePassword=response_data.get("password")
                )
                return True

        except Exception as e:
            logger.error("An error occurred during node registration: {}", e)
            return None

    async def try_to_register(self, session):
        while True:
            global_monitoring_boolean_case = None
            node_registration_status = await self.node_registration(session)
            if node_registration_status:
                info = await self.db_manager.get_user_data(({"email": self.email}), False, "clientid", "node", "nodePassword")
                messenger = MqttMessenger(self.db_manager, self.email, info, self.proxy, self.user_agent, session,self.version)
                await messenger.start_create_mining()
                global_monitoring_boolean_case = messenger.monitoring_boolean_case
                if not messenger.monitoring_boolean_case:
                    messenger.monitoring_boolean_case = False
                    break

            if not global_monitoring_boolean_case:
                await self.db_manager.replace_banned_proxy(self.email)
            self.proxy = await self.db_manager.get_user_data({'email': self.email}, True, 'proxy')
            self.proxy = self.proxy.get('proxy')
            logger.info("Replaced banned proxy - mail {}", self.email)
            delay = random.randint(5, 10) * 60
            logger.warning(f"🕒 Waiting {delay} seconds to retry node registration - mail {self.email}")
            await asyncio.sleep(delay)

    async def process_registration(self):
        proxy_db = await self.db_manager.get_user_data({'email': self.email}, True, 'proxy')
        self.proxy = proxy_db.get('proxy')
        try:
            async with aiohttp.ClientSession() as session:
                logger.info("Creating a new session for node registration - mail {}", self.email)
                await self.try_to_register(session)

        except Exception as e:
            logger.error("An error occurred while creating a session: {}", e)
