import random
import aiohttp
import asyncio
from loguru import logger
from src.messenger.hex_converter import PacketPreparer
from src.messenger.packet_id_counter import PacketId
from aiohttp import BasicAuth


class MqttMessenger:
    def __init__(self, db_manager, email, info: dict, proxy: str, user_agent: str, session: aiohttp.ClientSession,
                 version=None):
        self.email = email
        self.packet_id = PacketId()
        self.packet_preparer = PacketPreparer(info, self.packet_id, version)
        self.uri = "wss://wss.gradient.network:443/mqtt"
        self.proxy = proxy
        self.user_agent = user_agent
        self.session = session
        self.websocket = None
        self.db_manager = db_manager
        self.headers = {
            'Pragma': 'no-cache',
            'Origin': 'chrome-extension://caacbgbklghmpodbdafajbgdnegacfmo',
            'Accept-Language': 'en-US,en;q=0.9,uk;q=0.8,ru-RU;q=0.7,ru;q=0.6,en-GB;q=0.5,pl;q=0.4',
            'Sec-WebSocket-Key': 'dp2p8h2Hn9f4MyaBYoJY0A==',
            'User-Agent': self.user_agent,
            'Upgrade': 'websocket',
            'Cache-Control': 'no-cache',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Version': '13',
            'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
            'Sec-WebSocket-Protocol': 'mqtt',
        }
        self.ping_task = None
        self.message_task = None
        self.renew_subscribe_task = None
        self.monitoring_boolean_case = False

    async def get_monitoring_boolean_case(self):
        return self.monitoring_boolean_case

    async def start_default_mining(self):
        try:
            await self.run_websocket("default")

        except Exception as e:
            await self.handle_exception(e, f"An error occurred during default mining - mail {self.email}")

        finally:
            await self.handle_cleanup()

    async def start_create_mining(self):
        try:
            await self.run_websocket("register")
            await self.run_websocket("type-key")
            await self.run_websocket("version")

        except Exception as e:
            await self.handle_exception(e, f"An error occurred during create mining - mail {self.email}")

        finally:
            await self.handle_cleanup()

    async def send_ping_frame(self):
        try:
            while True:
                if self.websocket.closed:
                    logger.info(f"WebSocket is closed - mail {self.email}")
                    break
                await asyncio.sleep(60)
                await self.websocket.send_bytes(self.packet_preparer.prepare_pingreq_packet())
                response = await self.websocket.receive()
                # Safeguard for logging
                if isinstance(response.data, bytes):
                    logger.info(f"Receive PINGRESP: {response.data.hex()} - mail {self.email}")
                elif isinstance(response.data, int):
                    logger.info(f"Receive PINGRESP: {hex(response.data)} - mail {self.email}")
                else:
                    logger.info(f"Receive PINGRESP: {response.data} - mail {self.email}")

        except Exception as e:
            await self.handle_exception(e, f"An error occurred in ping task - mail {self.email}")

    async def send_150b_frame(self):
        try:
            while True:
                if self.websocket.closed:
                    logger.info(f"WebSocket is closed - mail {self.email}")
                    break
                delay = random.randint(1, 10) * 60
                await asyncio.sleep(delay)
                await self.websocket.send_bytes(self.packet_preparer.prepare_150b_packet())
                logger.info(f"Sent 150B - mail {self.email}")

        except Exception as e:
            await self.handle_exception(e, f"An error occurred in message task - mail {self.email}")

    async def receiver(self, _type, number_of_responses=1):
        try:
            for i in range(number_of_responses):
                response = await self.websocket.receive()
                logger.info(f"Receive {_type}: {response.data.hex()} - mail {self.email}")
        except Exception as e:
            await self.handle_exception(e, f"An error occurred during receiving {_type}")

    async def run_websocket(self, _type):
        try:
            async with self.session.ws_connect(self.uri, headers=self.headers, proxy=self.proxy) as websocket:
                self.websocket = websocket
                await self.handle_mining_frame(_type)

        except Exception as e:
            await self.handle_exception(e, f"An error occurred during WebSocket connection - mail {self.email}")

    async def handle_mining_frame(self, _type):
        await self.websocket.send_bytes(self.packet_preparer.prepare_connect_packet())
        await self.receiver("CONNACK")

        try:
            if _type == "register":
                logger.info("Start register connection" + self.email)
                task_frame = self.packet_preparer.prepare_subscribe_packet() + self.packet_preparer.prepare_unsubscribe_packet() + self.packet_preparer.prepare_subscribe_packet()
                await self.websocket.send_bytes(task_frame)

            elif _type == "type-key":
                logger.info("Start type-key connection" + self.email)
                task_frame = self.packet_preparer.prepare_unsubscribe_packet() + self.packet_preparer.prepare_subscribe_packet() + self.packet_preparer.prepare_unsubscribe_packet() + self.packet_preparer.prepare_subscribe_packet()
                await self.websocket.send_bytes(task_frame)
                await self.receiver("6B", 4)
                await asyncio.sleep(56)
                await self.websocket.send_bytes(self.packet_preparer.prepare_type_key_packet())
                logger.info("Sent TYPE_KEY")
                await self.receiver("TYPE-KEY", 1)

            elif _type == "version":
                logger.info("Start version connection" + self.email)
                task_frame = (
                        self.packet_preparer.prepare_unsubscribe_packet() +
                        self.packet_preparer.prepare_subscribe_packet()
                )
                await self.websocket.send_bytes(task_frame)
                await self.receiver("6B", 2)
                await asyncio.sleep(60)
                await self.websocket.send_bytes(self.packet_preparer.prepare_version_packet())
                logger.info("Sent VERSION")
                await self.websocket.send_bytes(self.packet_preparer.prepare_pingreq_packet())
                await self.receiver("PINGRESP", 1)
                await self.close_websocket()

            elif _type == "default":
                logger.info("Start default connection")
                task_frame = self.packet_preparer.prepare_subscribe_packet() + self.packet_preparer.prepare_unsubscribe_packet() + self.packet_preparer.prepare_subscribe_packet()
                await self.websocket.send_bytes(task_frame)
                await self.receiver("6B", 3)
                self.ping_task = asyncio.create_task(self.send_ping_frame(), name="PingTask")
                self.message_task = asyncio.create_task(self.send_150b_frame(), name="MessageTask")
                self.renew_subscribe_task = asyncio.create_task(self.renew_subscribe_frame(), name="RenewSubscribeTask")
                try:
                    await asyncio.gather(self.ping_task, self.message_task, self.renew_subscribe_task,
                                         return_exceptions=True)
                except Exception as e:
                    await self.handle_exception(e, "An error occurred during default mining")

            else:
                logger.error(f"Unknown type: {_type}")

        except Exception as e:
            await self.handle_exception(e, f"An error occurred during {_type} mining")

    async def close_websocket(self):
        if self.websocket is not None and not self.websocket.closed:
            try:
                await self.websocket.send_bytes(self.packet_preparer.prepare_disconnect_packet())
                await self.websocket.close()
                logger.info("WebSocket closed successfully")
            except Exception as e:
                logger.error(f"Failed to properly close WebSocket: {e}" + self.email)

    async def handle_exception(self, e, custom_message="An error occurred"):
        logger.error(f"{custom_message}: {e} - mail {self.email}")
        self.monitoring_boolean_case = True
        await self.close_websocket()
        await self.handle_cleanup()
        await self.db_manager.replace_banned_proxy(self.email)
        self.proxy = await self.db_manager.get_user_data({"email": self.email}, True, "proxy")
        self.proxy = self.proxy.get("proxy")

    async def handle_cleanup(self):
        if self.ping_task and not self.ping_task.done():
            self.ping_task.cancel()
        if self.message_task and not self.message_task.done():
            self.message_task.cancel()
        if self.renew_subscribe_task and not self.renew_subscribe_task.done():
            self.renew_subscribe_task.cancel()

    async def renew_subscribe_frame(self):
        try:
            while True:
                if self.websocket.closed:
                    logger.info(f"WebSocket is closed - mail {self.email}")
                    break
                delay = random.randint(60, 120) * 60
                await asyncio.sleep(delay)
                await self.websocket.send_bytes(self.packet_preparer.prepare_subscribe_packet())
                logger.info(f"Sent Subscribe packet - mail {self.email}")

        except Exception as e:
            await self.handle_exception(e, f"An error occurred in subscribe renew task - mail {self.email}")
