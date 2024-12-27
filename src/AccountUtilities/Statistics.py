from loguru import logger
import aiohttp
from src.AccountUtilities.IdTokenVerifier import IdTokenVerifier
from src.dataBase.dataBase import DatabaseManager
import asyncio
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem


# OopCompanion:suppressRename


class Statistics:
    def __init__(self, email, db_manager, user_agent):
        self.id_token = None
        self.email = email
        self.db_manager = db_manager
        self.user_agent = user_agent
        self.proxy = None

    async def statistics(self):
        self.proxy = await self.db_manager.get_user_data({"email": self.email}, True, "proxy")
        self.proxy = self.proxy.get("proxy")
        client_id = await self.db_manager.get_user_data({"email": self.email}, False, "node")
        client_id = client_id.get("node")
        async with aiohttp.ClientSession() as session:
            self.idTokenVerifier = IdTokenVerifier(self.email, self.db_manager, self.user_agent, self.proxy)
            self.id_token = await self.idTokenVerifier.id_token_verification(session)
            url = f"https://api.gradient.network/api/sentrynode/get/{client_id}"
            headers = {"Authorization": f"Bearer {self.id_token}", "User-Agent": self.user_agent}
            async with session.get(url, headers=headers, proxy=self.proxy) as response:
                try:
                    if response.status == 403:
                        logger.error(f"Access forbidden. Status code: 403 - mail {self.email}")
                        return False

                    if response.status != 200:
                        logger.error("Failed to get node status. Status code: {}", response.status)
                        return False
                    response_data = await response.json()
                    data = response_data.get("data", {})
                    hours = data.get("todayDuration") // 3600000
                    minutes = (data.get("todayDuration") % 3600000) // 60000

                    updates = {
                        "TotalPoint": data.get("point")/100000,
                        "TodayPoint": data.get("today")/100000,
                        "Taps": data.get("latency"),
                        "TodayTaps": data.get('todayLatency'),
                        "MimingTime": f"{hours}:{minutes}",
                    }
                    await self.db_manager.update_statistics(self.email, updates)
                    return True
                except Exception as e:
                    logger.error(f"Failed to get node banned. Error: {e}")
                    return False

    async def statistics_get(self):
        max_retries = 5
        attempt = 0
        while attempt < max_retries:
            if await self.statistics():
                break
            else:
                self.db_manager.replace_banned_proxy(self.email)
                attempt += 1

    async def init_statistics(self):
        await self.db_manager.add_statistics_table()
        emails = await self.db_manager.get_all_emails_node()
        await self.db_manager.add_emails_to_statistics(emails)



async def process_email(email, db_manager, user_agent, semaphore):
    async with semaphore:
        point_fetcher = Statistics(email, db_manager, user_agent)
        await point_fetcher.statistics()


async def main():
    # # Database initialization
    db_manager = DatabaseManager('../../data/FirsMail.db')
    # ststs = Statistics(0,db_manager,0,)
    # await ststs.init_statistics()
    # Fetch all emails from the database
    # emails = await db_manager.get_all_data(True , False)
    #
    # # Configure User-Agent rotator
    # software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value]
    # operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value, OperatingSystem.MAC.value]
    # user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)
    #
    # # Limit the number of concurrent tasks
    # max_concurrent_tasks = 50
    # semaphore = asyncio.Semaphore(max_concurrent_tasks)
    #
    # # Process emails concurrently with randomized User-Agent
    # tasks = [
    #     process_email(email, db_manager, user_agent_rotator.get_random_user_agent(), semaphore)
    #     for email in emails
    # ]
    # await asyncio.gather(*tasks)

    point = await db_manager.get_total_points(False)
    logger.info(f"Total points: {point}")
if __name__ == "__main__":
    asyncio.run(main())
