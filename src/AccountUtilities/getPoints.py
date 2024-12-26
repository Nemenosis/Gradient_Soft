from loguru import logger
import aiohttp
from src.AccountUtilities.IdTokenVerifier import IdTokenVerifier
from src.dataBase.dataBase import DatabaseManager
import asyncio
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem


# OopCompanion:suppressRename


class GetPoint:
    def __init__(self, email, db_manager, user_agent):
        self.id_token = None
        self.email = email
        self.db_manager = db_manager
        self.user_agent = user_agent
        self.proxy = None

    async def profile_points(self):
        if not self.proxy:
            self.proxy = await self.db_manager.get_user_data({"email": self.email}, True, "proxy")
        self.proxy = self.proxy.get("proxy")

        async with aiohttp.ClientSession() as session:
            # Fetch the user's token from the database
            verifier = IdTokenVerifier(self.email, self.db_manager, self.user_agent, self.proxy)
            id_token = await verifier.id_token_verification(session)
            if not id_token:
                logger.error(f"❌ No idToken found for {self.email}")
                return None

            try:
                url = "https://api.gradient.network/api/user/profile"
                headers = {
                    "Authorization": f"Bearer {id_token}",
                    'User-Agent': self.user_agent
                }

                # Make the request
                async with session.post(url, headers=headers, proxy=self.proxy) as response:
                    result = await response.json()

                    # Check for success response
                    if result.get('code') == 200:
                        logger.info(f"✅ Profile request successful for {self.email}!")
                        data = result.get("data", {})

                        # Safely access the 'point' attribute
                        if 'point' in data:
                            data = data.get("point", {})
                            # Extract total and today points
                            total_points = data.get('total')
                            today_points = data.get('today')

                            # Log only total and today points
                            logger.info(f"Points for {self.email}: Total = {total_points/100000}, Today = {today_points/100000}")
                        else:
                            logger.error(f"❌ 'point' attribute not found in the response for {self.email}")
                    elif result.get('code') == 400:
                        logger.warning(f"⚠️ Invalid request (400) for {self.email}")
                    else:
                        logger.error(f"❌ Profile request error for {self.email}, status: {response.status}")
            except Exception as err:
                logger.error(f"❌ Error when requesting profile for {self.email}: {err}")
                return None


async def process_email(email, db_manager, user_agent, semaphore):
    async with semaphore:
        point_fetcher = GetPoint(email, db_manager, user_agent)
        await point_fetcher.profile_points()


async def main():
    # Database initialization
    db_manager = DatabaseManager('../AccountExtractor/data/FirsMail.db')

    # Fetch all emails from the database
    emails = await db_manager.get_all_data(True , False)

    # Configure User-Agent rotator
    software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value, OperatingSystem.MAC.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)

    # Limit the number of concurrent tasks
    max_concurrent_tasks = 5
    semaphore = asyncio.Semaphore(max_concurrent_tasks)

    # Process emails concurrently with randomized User-Agent
    tasks = [
        process_email(email, db_manager, user_agent_rotator.get_random_user_agent(), semaphore)
        for email in emails
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
