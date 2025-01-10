from imap_tools import MailBox, AND
from bs4 import BeautifulSoup
from loguru import logger
from data.config import IMAP_DOMAIN
import random
import time
# OopCompanion:suppressRename


class MailVerif:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.imap_server = IMAP_DOMAIN or 'imap.rambler.ru'

    async def get_code(self):
        code = ""
        # delay = random.uniform(120, 180)
        # logger.info(f"Delaying connection to IMAP server for {self.email} by {delay:.2f} seconds.")
        # time.sleep(delay)
        try:
            with MailBox(self.imap_server).login(self.email, self.password) as mailbox:
                mailbox.folder.set('INBOX')
                messages = list(mailbox.fetch(AND(from_='noreply@gradient.network')))

                if messages:
                    last_msg = messages[-1]
                    html_content = last_msg.html

                    if html_content:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        div_elements = soup.find_all('div', class_='pDiv')
                        code = ''.join(div.get_text(strip=True) for div in div_elements)
                        logger.info(f"Verification code for {self.email}: {code}")
                    else:
                        logger.warning("No HTML content in the last email.")
                else:
                    logger.warning(f"No messages from noreply@gradient.network for {self.email}")
        except Exception as e:
            logger.error(f"Error connecting to the mail server for {self.email}: {e}")
        return code


# async def main():
#     email = "your_email@example.com"
#     password = "your_password"
#
#     mail_verif = MailVerif(email, password)
#     verification_code = await mail_verif.get_code(
#         from_email='noreply@gradient.network',
#         subject="Your Verification Code",
#         folder='INBOX'
#     )
#     if verification_code:
#         print(f"Received verification code: {verification_code}")
#     else:
#         print("Verification code not found.")
#
#
# if __name__ == "__main__":
#     asyncio.run(main())
