import aiohttp
import asyncio
from art import text2art
from termcolor import colored, cprint
import webbrowser
import ctypes
import os
import re
import sys
from bs4 import BeautifulSoup
import requests
import argparse
import multiprocessing
from data.config import REGISTER_ACCOUNT_ONLY,GRADIENT_DATA,MULTIPROCESS,DB_INIT, MINING_MODE,REGISTER_TASKS,NODE_REGISTER
from src.autoReger.autoReger import AutoReger
import asyncio
from src.dataBase.dataBase import DatabaseManager
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem
from src.AccountUtilities.NodeMiner import NodeMiner
from src.AccountUtilities.nodeInitializer import NodeInitializer
from loguru import logger

def bot_info(name: str = ""):
    cprint(text2art(name), 'blue')

    if sys.platform == 'win32':
        ctypes.windll.kernel32.SetConsoleTitleW(f"{name}")

    link = "https://t.me/Dva_Xsa"
    git_hub = "https://github.com/Nemenosis?tab=repositories"
    clickable_link = f"\033]8;;{link}\033\\{link}\033]8;;\033\\"
    additional_text = ""
    if REGISTER_ACCOUNT_ONLY:
        additional_text += colored("REGISTER MODE", color='magenta')
    if NODE_REGISTER:
        additional_text += colored("NODE REGISTER MODE", color='magenta')
    if MINING_MODE:
        additional_text += colored("MINING MODE", color='magenta')
    if DB_INIT:
        additional_text += colored("DATABASE INIT MODE", color='magenta')

    print(
        f"{colored('Nemenosis <crypto/> moves:', color='light_red')} "
        f"{colored(clickable_link, color='light_red')}\n"
        f"{colored(f'Git-hub {git_hub}', color='light_red')}\n"
        f"{colored('Version 1.0', color='light_red')}\n"
        f"{additional_text}\n"
    )
    choice = input("Open links for Git-hub and Telegram? (y/n): ").lower()
    if choice == 'y':
        webbrowser.open(link)
        webbrowser.open(git_hub)



async def run_registration_process(db_manager: DatabaseManager, ref_code: str, REGISTER_TASKS):
    emails = await db_manager.get_all_data(True, True)
    passwords = await db_manager.get_all_data(False, True)
    if not emails or len(emails) == 0:
        logger.error("No emails found in the database.")
        return

    if len(emails) != len(passwords):
        logger.error("The number of emails and passwords do not match!")
        return

    proxies = await db_manager.get_all_proxies_from_db()

    if len(proxies) < len(emails):
        logger.warning("⚠️ The number of available proxies is less than the number of emails!")
        return

    software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value, OperatingSystem.MAC.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)

    user_agents = [user_agent_rotator.get_random_user_agent() for _ in range(len(emails))]

    tasks = []
    semaphore = asyncio.Semaphore(REGISTER_TASKS)

    async def register_account(email, password, user_agent):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                auto_reger = AutoReger(email, password, user_agent, ref_code, db_manager)
                await auto_reger.process_registration(session, 'data/aborted_mail.txt')

    for email, password, proxy, user_agent in zip(emails, passwords, proxies, user_agents):
        tasks.append(register_account(email, password, user_agent))

    await asyncio.gather(*tasks)

def start_node_registration_process(emails_chunk,process_index):
    db_path = GRADIENT_DATA
    database_manager = DatabaseManager(db_path)

    software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value, OperatingSystem.MAC.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)
    user_agents = [user_agent_rotator.get_random_user_agent() for _ in range(len(emails_chunk))]

    def get_version():
        extension_id = "caacbgbklghmpodbdafajbgdnegacfmo"
        url = f"https://chrome.google.com/webstore/detail/{extension_id}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        version_tag = soup.find('div', class_='N3EXSc')
        version = version_tag.text.strip()
        return version

    version = get_version()

    async def node_registration_task():
        tasks = []
        semaphore = asyncio.Semaphore(REGISTER_TASKS)

        async def register_node(email, user_agent):
            async with semaphore:
                logger.info(f"[Process {process_index}] Starting registration for email: {email}")
                node_initializer = NodeInitializer(email, database_manager, user_agent, version=version)
                await node_initializer.process_registration()
                logger.info(f"[Process {process_index}] Starting registration for email: {email}")

        for email, user_agent in zip(emails_chunk, user_agents):
            tasks.append(asyncio.create_task(register_node(email, user_agent)))

        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"[Process {process_index}] All node registration tasks completed.")
        # logger.info("All node registration tasks in this process completed.")

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(node_registration_task())


async def run_node_registration_multiprocess():
    db_path = GRADIENT_DATA
    database_manager = DatabaseManager(db_path)
    emails = await database_manager.get_all_data(True, False)

    if not emails or len(emails) == 0:
        logger.error("No emails found in the database.")
        return

    chunk_size = len(emails) // MULTIPROCESS
    chunks = [emails[i * chunk_size:(i + 1) * chunk_size] for i in range(MULTIPROCESS)]

    if len(emails) % MULTIPROCESS != 0:
        chunks[-1].extend(emails[MULTIPROCESS * chunk_size:])

    processes = []
    for i, emails_chunk in enumerate(chunks):
        process = multiprocessing.Process(target=start_node_registration_process, args=(emails_chunk, i))
        logger.info(f"Starting process {i} for email chunk: {emails_chunk}")
        processes.append(process)
        process.start()

    for process in processes:
        process.join()
        logger.info(f"Process {process.pid} has completed.")


def start_mining_process(emails_chunk):
    db_path = GRADIENT_DATA
    database_manager = DatabaseManager(db_path)

    software_names = [SoftwareName.CHROME.value, SoftwareName.FIREFOX.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value, OperatingSystem.MAC.value]
    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)
    user_agents = [user_agent_rotator.get_random_user_agent() for _ in range(len(emails_chunk))]

    async def mining_task():
        tasks = []
        for email, user_agent in zip(emails_chunk, user_agents):
            node_miner = NodeMiner(email, database_manager, user_agent)
            tasks.append(asyncio.create_task(node_miner.process_mining()))

        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All mining tasks in this process completed.")

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(mining_task())



async def run_mining_multiprocess():

    db_path = GRADIENT_DATA
    database_manager = DatabaseManager(db_path)
    emails = await database_manager.get_all_emails_node()
    if not emails or len(emails) == 0:
        logger.error("No emails found in the database.")
        return

    chunk_size = len(emails) // MULTIPROCESS
    chunks = [emails[i * chunk_size:(i + 1) * chunk_size] for i in range(MULTIPROCESS)]

    if len(emails) % MULTIPROCESS != 0:
        chunks[-1].extend(emails[MULTIPROCESS * chunk_size:])

    processes = []
    for i, emails_chunk in enumerate(chunks):
        process = multiprocessing.Process(target=start_mining_process, args=(emails_chunk,))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()


async def initDatabase():
    if DB_INIT:
        db_manager = DatabaseManager(GRADIENT_DATA)
        await db_manager.create_table()
        await db_manager.create_users_from_file('data/mail.txt')
        await db_manager.load_proxies_from_file('data/proxy.txt')
        emails = await db_manager.get_all_data()
        await db_manager.assign_emails_to_null_proxies(emails)



async def run_auto_reger():
        # database.db
        # GradientData.db
        db_path = GRADIENT_DATA
        ref_code = "TZ0RLT"
        database_manager = DatabaseManager(db_path)
        if DB_INIT:
            await initDatabase()
        if REGISTER_ACCOUNT_ONLY:
            await run_registration_process(database_manager, ref_code, REGISTER_TASKS)

        if NODE_REGISTER:
            await run_node_registration_multiprocess()

        if MINING_MODE:
            await run_mining_multiprocess()



if __name__ == "__main__":
    bot_info("Gradient_Soft")

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run_auto_reger())
