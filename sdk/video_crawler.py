from typing import Callable
from bs4 import BeautifulSoup
import requests
from sdk import common
from selenium import webdriver
from pyvirtualdisplay import Display
from pyvirtualdisplay.abstractdisplay import XStartError
from pathlib import Path
import orjson
import os

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
    cache = Path("tmpstor") / f"url-{url}-js".replace("/", "@").replace(".", "*")
    cache = cache.with_suffix(".min.json")
    if not cache.exists():
        print(f"Selenium scrape triggered on {url}")
        session.get(url)
        data = {"title": session.title, "link": url}
        with cache.open("w") as cache_fp:
            common.write_min_json(data, cache_fp)
        return data
    else:
        if os.environ.get("DEBUG"):
            print(f"Using cached resource {cache}")
        with cache.open() as cache_fp:
            return orjson.loads(cache_fp.read())

def get_video_bs4(url: str) -> dict:
    cache = Path("tmpstor") / f"url-{url}-bs4".replace("/", "@").replace(".", "*")
    cache = cache.with_suffix(".min.json")
    if not cache.exists():
        print(f"BS4 scrape triggered on {url}")
        html = requests.get(url).text
        soup = BeautifulSoup(html, 'html.parser')
        data = {"title": soup.title.string, "link": url}
        with cache.open("w") as cache_fp:
            common.write_min_json(data, cache_fp)
        return data
    else:
        if os.environ.get("DEBUG"):
            print(f"Using cached resource {cache}")
        with cache.open() as cache_fp:
            return orjson.loads(cache_fp.read())
