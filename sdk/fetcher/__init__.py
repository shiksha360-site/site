import os
from sdk.fetcher.yt import Youtube
from sdk import common
from .scrapers import ln_scrape

scrapers = {
    "lnscrape": ln_scrape.ln_scrape
}

class ScrapeCache():
    def __init__(self):
        self.cache = {}
        self.current = None
    
    def keys(self):
        return self.cache.keys()
    
    def set_current(self, current: str):
        if current not in self.keys():
            self.cache[current] = []
        self.current = current
    
    def get_cached(self) -> list:
        return self.cache[self.current]
    
    def add(self, title: str):
        self.cache[self.current].append(title)

scrape_cache = ScrapeCache()

def get_channel_list():
    return common.load_yaml("data/core/yt_channels.yaml")

def scrape(yt: Youtube, chapter_info: dict, subtopic: str):
    channel_list = get_channel_list()
    scraped_data = {}
    for name, channel_info in channel_list.items():
        scrape_cache.set_current(channel_info["scraper"])
        scraped_data[name] = scrapers[channel_info["scraper"]](yt, channel_info, chapter_info, subtopic, scrape_cache)
    return scraped_data