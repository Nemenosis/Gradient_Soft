import asyncio
from dbm import error
import aiohttp
from loguru import logger
from src.dataBase.dataBase import DatabaseManager
from src.messenger.mqtt_messenger import MqttMessenger
from src.AccountUtilities.IdTokenVerifier import IdTokenVerifier


# OopCompanion:suppressRename


class NodeMiner:
    def __init__(self, email, db_manager: DatabaseManager, user_agent):
        self.email = email
        self.db_manager = db_manager
        self.user_agent = user_agent
        self.proxy = None
        self.id_token = None
        self.idTokenVerifier = None
        self.mining_task = None

    async def try_check_ban(self, session, client_id):
        self.idTokenVerifier = IdTokenVerifier(self.email, self.db_manager, self.user_agent, self.proxy)
        self.id_token = await self.idTokenVerifier.id_token_verification(session)
        url = f"https://api.gradient.network/api/sentrynode/get/{client_id}"
        headers = {"Authorization": f"Bearer {self.id_token}", "User-Agent": self.user_agent}
        async with session.get(url, headers=headers, proxy=self.proxy) as response:
            try:
                if response.status == 403:
                    logger.error(f"Access forbidden. Status code: 403 - mail {self.email}")
                    return 403

                if response.status != 200:
                    logger.error("Failed to get node status. Status code: {}", response.status)
                    return None
                response_data = await response.json()
                data = response_data.get("data", {})
                return data.get("banned"), data.get("connect")
            except Exception as e:
                logger.error(f"Failed to get node banned. Error: {e}")

    async def is_node_banned(self, session, client_id, mqtt_messenger):
        await asyncio.sleep(30)
        while True:
            if await mqtt_messenger.get_monitoring_boolean_case():
                break
            banned_status, connect_status = await self.try_check_ban(session, client_id)

            if connect_status:
                logger.info("ℹ️ Node is connected - mail {}", self.email)

                if banned_status:
                    logger.error("❌ Node is banned. Replacing proxy - mail {}", self.email)
                    self.mining_task.cancel()
                    await self.db_manager.replace_banned_proxy(self.email)
                    self.proxy = await self.db_manager.get_user_data({"email": self.email}, True, "proxy")
                    self.proxy = self.proxy.get("proxy")
                    await asyncio.sleep(60)
                else:
                    logger.info("✅ Node is not banned - mail {}", self.email)
                break

            elif banned_status == 403 or banned_status is None:
                logger.error("Failed to get node status - mail {}", self.email)
                self.idTokenVerifier = IdTokenVerifier(self.email, self.db_manager, self.user_agent, self.proxy)
                self.id_token = await self.idTokenVerifier.id_token_verification(session)
            else:
                logger.warning("🕒 Waiting for node to connect - mail {}", self.email)
                await asyncio.sleep(5 * 60)

    async def process_mining(self):
        self.proxy = await self.db_manager.get_user_data({"email": self.email}, True, "proxy")
        self.proxy = self.proxy.get("proxy")

        try:
            async with aiohttp.ClientSession() as session:
                reconnect = False
                while True:
                    try:
                        if reconnect:
                            await asyncio.sleep(60)
                        info = await self.db_manager.get_user_data({"email": self.email}, False, "node", "clientid",
                                                                   "nodePassword")
                        messenger = MqttMessenger(self.db_manager, self.email, info, self.proxy, self.user_agent,
                                                  session)
                        messenger.monitoring_boolean_case = False
                        self.mining_task = asyncio.create_task(messenger.start_default_mining())
                        node_status_task = asyncio.create_task(
                            self.is_node_banned(session, info.get("node"), messenger))
                        await asyncio.gather(self.mining_task, node_status_task, return_exceptions=True)

                    except Exception as e:

                        logger.error(f"An error occurred during mining - mail {self.email}: {e}")

                    finally:
                        reconnect = True

        except Exception as e:
            logger.error("An error occurred while creating a session: {}", e)
