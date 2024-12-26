import requests
from bs4 import BeautifulSoup


def get_version():
    extension_id = "caacbgbklghmpodbdafajbgdnegacfmo"
    url = f"https://chrome.google.com/webstore/detail/{extension_id}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    version_tag = soup.find('div', class_='N3EXSc')
    version = version_tag.text.strip()
    return version
