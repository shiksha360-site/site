from sdk.fetcher.yt import Youtube
from .classes import ScrapeData, ScrapeCache
from sdk import common
from .scrapers import ln_scrape

scrapers = {
    "lnscrape": ln_scrape.ln_scrape
}

scrape_cache = ScrapeCache()

def get_channel_list():
    return common.load_yaml("data/core/yt_channels.yaml")

def scrape(yt: Youtube, chapter_info: dict, subtopic: str):
    channel_list = get_channel_list()
    scraped_data = {}
    for name, channel_info in channel_list.items():
        scrape_cache.set_current(channel_info["scraper"])
        data = ScrapeData(yt=yt, channel_info=channel_info, chapter_info=chapter_info, subtopic=subtopic, scrape_cache=scrape_cache)
        scraped_data[name] = scrapers[channel_info["scraper"]](data)
    return scraped_data

def scrape_cache_clear():
    scrape_cache.clear()