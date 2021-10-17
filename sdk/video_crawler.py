from typing import Callable
from bs4 import BeautifulSoup
import requests
from sdk import common
from selenium import webdriver
from pyvirtualdisplay import Display
from pyvirtualdisplay.abstractdisplay import XStartError
import signal

started_display = False
display = None

def prepare():
    display = Display(visible=0, size=(800, 600))
    try:
        display.start()
        started_display = True
    except XStartError:
        pass
    
    return webdriver.Chrome()

def page_kill(session):
    session.close()
    if started_display:
        display.stop()


def get_video_with_js(session, url: str) -> dict:
    print(f"Selenium scrape triggered on {url}")
    session.get(url)
    return {"title": session.title, "link": url}

def get_video_bs4(url: str) -> dict:
    print(f"BS4 scrape triggered on {url}")
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    return {"title": soup.title.string, "link": url}